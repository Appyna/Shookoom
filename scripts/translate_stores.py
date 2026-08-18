import os, time, re
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

INVALID_CITY_VALUES = {"לא קיים", "אין עיר", "INCONNU", "", "null", "None", "לא קיים"}

CHAIN_NAMES_FR = {
    "shufersal": "Shufersal",
    "rami_levy": "Rami Levy",
    "yayno_bitan": "Yeinot Bitan & Carrefour",
    "keshet": "Keshet",
    "good_pharm": "Good Pharm",
    "super_sapir": "Super Sapir",
    "zol_vebegadol": "Zol VeBegadol",
    "dor_alon": "Dor Alon",
    "stop_market": "Stop Market",
    "super_yuda": "Super Yuda",
    "salach_dabach": "Salach Dabach",
    "bareket": "Bareket",
    "city_market": "City Market",
    "maayan2000": "Maayan 2000",
    "king_store": "King Store",
    "polizer": "Polizer",
    "shefa_barcart": "Shefa Barcart",
    "shuk_ahir": "Shuk Ahir",
    "osher_ad": "Osher Ad",
    "tiv_taam": "Tiv Taam",
    "yohananof": "Yohananof",
    "yellow": "Yellow",
    "fresh_market": "Fresh Market",
}

def get_cities_cache():
    result = supabase.table("cities").select("name_he, name_fr").execute()
    return {r["name_he"]: r["name_fr"] for r in result.data}

def is_online_store(store):
    address = store.get("address") or ""
    name = store.get("store_name_he") or ""
    return "http" in address or "אינטרנט" in name or "אונליין" in name or "online" in name.lower()

def find_city_in_text(text, cities_cache):
    """Méthode 2 — cherche une ville connue dans le texte"""
    if not text:
        return None, None
    for city_he, city_fr in cities_cache.items():
        if len(city_he) >= 3 and city_he in text:
            return city_he, city_fr
    return None, None

def translate_name_and_address(stores, cities_cache):
    """GPT uniquement pour traduire nom + adresse — PAS pour trouver la ville"""
    if not openai_client or not stores:
        return []
    
    chain_names_list = "\n".join([f"- {v}" for v in CHAIN_NAMES_FR.values()])
    
    lines = []
    for s in stores:
        chain_name = CHAIN_NAMES_FR.get(s.get("chain_id"), "")
        city_fr = s.get("_city_fr", "Israël")
        lines.append(
            f"ID:{s['id']}|"
            f"CHAINE:{chain_name}|"
            f"NOM_HE:{s.get('store_name_he') or ''}|"
            f"ADRESSE:{s.get('address') or ''}|"
            f"VILLE_FR:{city_fr}"
        )
    
    prompt = (
        "Tu es un expert en supermarchés israéliens.\n"
        "Pour chaque magasin, retourne: ID|nom_fr|adresse_fr\n\n"
        "RÈGLES CRITIQUES:\n"
        f"1. Noms de chaînes INTOUCHABLES:\n{chain_names_list}\n"
        "'Yellow' = TOUJOURS 'Yellow' (JAMAIS 'Jaune')\n\n"
        "2. nom_fr: '[NOM_CHAINE] [description courte] - [VILLE_FR]'\n"
        "Exemples:\n"
        "- 'Shufersal Express - Tel Aviv'\n"
        "- 'Rami Levy - Jérusalem'\n"
        "- 'Yellow - Haïfa'\n"
        "JAMAIS de texte hébreu dans nom_fr\n"
        "JAMAIS d'apostrophe dans les noms\n\n"
        "3. adresse_fr: traduis l'adresse en français. Si vide: laisse vide\n\n"
        "4. JAMAIS de | dans les champs\n"
        "5. 1 ligne par magasin, même ordre exact\n\n"
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

def extract_city_gpt(store, cities_cache):
    """Méthode 3 — GPT pour extraire la ville uniquement"""
    if not openai_client:
        return None, None
    
    prompt = (
        "Extrais UNIQUEMENT le nom de la ville israélienne depuis ces infos.\n"
        "Réponds UNIQUEMENT avec: ville_he|ville_fr\n"
        "Exemples: תל אביב|Tel Aviv, ירושלים|Jérusalem, חיפה|Haïfa\n"
        "SANS apostrophe: רעננה|Raanana, מודיעין|Modiin\n"
        "Si pas de ville claire: |Israël\n\n"
        f"Nom du magasin: {store.get('store_name_he') or ''}\n"
        f"Adresse: {store.get('address') or ''}"
    )
    
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        parts = r.choices[0].message.content.strip().split("|")
        if len(parts) == 2:
            ville_he = parts[0].strip()
            ville_fr = parts[1].strip().replace("'", "").replace("`", "")
            if ville_he in INVALID_CITY_VALUES or not ville_he:
                return None, "Israël"
            # Vérifier si dans cache
            if ville_he in cities_cache:
                return ville_he, cities_cache[ville_he]
            return ville_he, ville_fr
        return None, "Israël"
    except:
        return None, "Israël"

def main():
    print("🏪 Traduction magasins démarrée")
    
    cities_cache = get_cities_cache()
    print(f"📦 {len(cities_cache)} villes en cache")
    
    new_cities = {}
    total_updated = 0
    
    while True:
        result = supabase.table("stores")\
            .select("id, chain_id, store_name_he, store_name_fr, city_he, city_fr, address, address_fr")\
            .is_("store_name_fr", "null")\
            .limit(200)\
            .execute()
        
        stores = result.data
        if not stores:
            print("✅ Tous les magasins sont traduits!")
            break
        
        print(f"📦 {len(stores)} magasins restants...")
        
        # Étape 1+2 : Trouver la ville pour chaque magasin AVANT GPT
        for store in stores:
            if is_online_store(store):
                store["_city_he"] = None
                store["_city_fr"] = "En ligne"
                continue
            
            city_he = None
            city_fr = None
            
            # Méthode 1 — city_he déjà dans la base
            existing_city_he = store.get("city_he")
            if existing_city_he and existing_city_he not in INVALID_CITY_VALUES:
                if existing_city_he in cities_cache:
                    city_he = existing_city_he
                    city_fr = cities_cache[existing_city_he]
            
            # Méthode 2 — chercher ville connue dans adresse ou nom
            if not city_he:
                city_he, city_fr = find_city_in_text(store.get("address"), cities_cache)
            if not city_he:
                city_he, city_fr = find_city_in_text(store.get("store_name_he"), cities_cache)
            
            # Méthode 3 — GPT en dernier recours
            if not city_he:
                city_he, city_fr = extract_city_gpt(store, cities_cache)
                if city_he and city_he not in cities_cache:
                    city_fr_clean = (city_fr or "Israël").replace("'", "").replace("`", "")
                    new_cities[city_he] = city_fr_clean
                    cities_cache[city_he] = city_fr_clean
                    city_fr = city_fr_clean
            
            store["_city_he"] = city_he
            store["_city_fr"] = city_fr or "Israël"
        
        # GPT pour noms + adresses par batch de 20
        BATCH = 20
        for i in range(0, len(stores), BATCH):
            batch = stores[i:i+BATCH]
            translations = translate_name_and_address(batch, cities_cache)
            
            for store, line in zip(batch, translations):
                try:
                    parts = line.split("|")
                    if len(parts) < 3:
                        continue
                    
                    nom_fr = parts[1].strip().replace("'", "").replace("`", "")
                    adresse_fr = parts[2].strip()
                    
                    city_he = store.get("_city_he")
                    city_fr = store.get("_city_fr", "Israël")
                    
                    # Vérifier nom de chaîne
                    chain_name = CHAIN_NAMES_FR.get(store.get("chain_id"), "")
                    if chain_name and not nom_fr.startswith(chain_name):
                        nom_fr = f"{chain_name} - {city_fr}" if city_fr and city_fr not in ("Israël", "En ligne") else chain_name
                    
                    # Supprimer hébreu du nom_fr
                    if city_he and city_he in nom_fr:
                        nom_fr = nom_fr.replace(city_he, city_fr)
                    
                    # Nettoyer "- Israël" à la fin
                    if nom_fr.endswith(" - Israël"):
                        nom_fr = nom_fr[:-9].strip()
                    
                    update_data = {}
                    if nom_fr:
                        update_data["store_name_fr"] = nom_fr
                    if city_he:
                        update_data["city_he"] = city_he
                    if city_fr:
                        update_data["city_fr"] = city_fr
                    if adresse_fr:
                        update_data["address_fr"] = adresse_fr
                    
                    if update_data:
                        supabase.table("stores")\
                            .update(update_data)\
                            .eq("id", store["id"])\
                            .execute()
                        total_updated += 1
                        
                except Exception as e:
                    print(f"⚠️ Erreur store {store.get('id')}: {e}")
            
            print(f"✅ {total_updated} mis à jour")
            time.sleep(0.5)
    
    # Sauvegarder nouvelles villes
    if new_cities:
        print(f"🏙️ {len(new_cities)} nouvelles villes...")
        for he, fr in new_cities.items():
            try:
                supabase.table("cities")\
                    .upsert({"name_he": he, "name_fr": fr, "verified": False})\
                    .execute()
            except Exception as e:
                print(f"⚠️ Erreur ville {he}: {e}")
    
    print(f"🎉 Terminé: {total_updated} magasins, {len(new_cities)} nouvelles villes")

if __name__ == "__main__":
    main()
