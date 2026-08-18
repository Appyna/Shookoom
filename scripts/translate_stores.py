import os, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_cities_cache():
    result = supabase.table("cities").select("name_he, name_fr").execute()
    return {r["name_he"]: r["name_fr"] for r in result.data}

def get_chains_cache():
    result = supabase.table("chains").select("id, name_fr").execute()
    return {r["id"]: r["name_fr"] for r in result.data}

def translate_batch(stores, cities_cache, chains_cache):
    if not openai_client or not stores:
        return []
    
    chains_ref = "\n".join([f"- {name_fr}" for name_fr in chains_cache.values()])
    
    lines = []
    for s in stores:
        chain_name = chains_cache.get(s.get("chain_id"), "")
        city_he_existing = s.get("city_he") or ""
        lines.append(
            f"ID:{s['id']}|"
            f"CHAINE:{chain_name}|"
            f"NOM:{s.get('store_name_he') or ''}|"
            f"ADRESSE:{s.get('address') or ''}|"
            f"VILLE_HE_EXISTANTE:{city_he_existing}"
        )
    
    prompt = (
        "Tu es un expert en géographie israélienne et en supermarchés israéliens.\n"
        "Pour chaque magasin, extrais et traduis les informations.\n\n"
        "Format STRICT de réponse: ID|nom_fr|ville_he|ville_fr|adresse_fr\n\n"
        "Règles IMPORTANTES:\n"
        "1. nom_fr: traduis le nom du magasin en français. "
        "Utilise EXACTEMENT ces noms de chaînes officiels:\n"
        f"{chains_ref}\n"
        "2. ville_he: SI VILLE_HE_EXISTANTE est remplie → utilise-la directement. "
        "Sinon extrais la ville depuis l'adresse, puis depuis le nom du magasin.\n"
        "3. ville_fr: translittération française officielle de la ville "
        "(Tel Aviv, Jérusalem, Haïfa, Netanya, Beer Sheva, Bnei Brak, etc)\n"
        "4. adresse_fr: traduis l'adresse en français. "
        "Garde les numéros. Traduis rue/boulevard/avenue. "
        "Si pas d'adresse: laisse vide\n"
        "5. Si ville introuvable: ville_he=INCONNU, ville_fr=Israël\n"
        "6. 1 ligne par magasin, même ordre exact\n"
        "7. Pas de | dans les champs\n\n"
        "Magasins:\n" + "\n".join(lines)
    )
    
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        return r.choices[0].message.content.strip().split("\n")
    except Exception as e:
        print(f"⚠️ Erreur GPT: {e}")
        return []

def main():
    print("🏪 Traduction magasins démarrée")
    
    cities_cache = get_cities_cache()
    chains_cache = get_chains_cache()
    print(f"📦 {len(cities_cache)} villes en cache, {len(chains_cache)} chaînes")
    
    result = supabase.table("stores")\
        .select("id, chain_id, store_name_he, store_name_fr, city_he, city_fr, address, address_fr")\
        .execute()
    
    stores = [s for s in result.data if not s.get("store_name_fr")]
    print(f"📦 {len(stores)} magasins à traiter")
    
    updated = 0
    new_cities = {}
    BATCH = 20
    
    for i in range(0, len(stores), BATCH):
        batch = stores[i:i+BATCH]
        translations = translate_batch(batch, cities_cache, chains_cache)
        
        for store, line in zip(batch, translations):
            try:
                parts = line.split("|")
                if len(parts) < 5:
                    continue
                
                nom_fr = parts[1].strip()
                ville_he = parts[2].strip()
                ville_fr_gpt = parts[3].strip()
                adresse_fr = parts[4].strip()
                
                # Normaliser la ville
                if ville_he and ville_he != "INCONNU":
                    if ville_he in cities_cache:
                        ville_fr = cities_cache[ville_he]
                    else:
                        ville_fr = ville_fr_gpt
                        new_cities[ville_he] = ville_fr
                        cities_cache[ville_he] = ville_fr
                else:
                    ville_fr = "Israël"
                    ville_he = None

                # Si nom_fr = juste le nom de la chaîne → composer avec la ville
                chain_name = chains_cache.get(store.get("chain_id"), "")
                if nom_fr == chain_name and ville_fr and ville_fr != "Israël":
                    nom_fr = f"{chain_name} - {ville_fr}"
                
                update_data = {}
                if nom_fr:
                    update_data["store_name_fr"] = nom_fr
                if ville_he and not store.get("city_he"):
                    update_data["city_he"] = ville_he
                if ville_fr:
                    update_data["city_fr"] = ville_fr
                if adresse_fr:
                    update_data["address_fr"] = adresse_fr
                
                if update_data:
                    supabase.table("stores")\
                        .update(update_data)\
                        .eq("id", store["id"])\
                        .execute()
                    updated += 1
                    
            except Exception as e:
                print(f"⚠️ Erreur store {store.get('id')}: {e}")
        
        if (i // BATCH) % 5 == 0:
            print(f"✅ [{i+BATCH}/{len(stores)}] {updated} magasins mis à jour")
        
        time.sleep(0.5)
    
    if new_cities:
        print(f"🏙️ {len(new_cities)} nouvelles villes à ajouter...")
        for he, fr in new_cities.items():
            try:
                supabase.table("cities")\
                    .upsert({"name_he": he, "name_fr": fr, "verified": False})\
                    .execute()
            except Exception as e:
                print(f"⚠️ Erreur ville {he}: {e}")
        print(f"✅ Nouvelles villes ajoutées dans cities avec verified=FALSE")
    
    print(f"🎉 Terminé: {updated} magasins mis à jour, {len(new_cities)} nouvelles villes")

if __name__ == "__main__":
    main()
