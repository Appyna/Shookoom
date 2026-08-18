import os, time, re
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Villes invalides à ignorer
INVALID_CITY_VALUES = {"לא קיים", "אין עיר", "INCONNU", "", "null", "None"}

# Noms de chaînes officiels — intouchables
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
    """Détecte les magasins en ligne"""
    address = store.get("address") or ""
    name = store.get("store_name_he") or ""
    return "http" in address or "אינטרנט" in name or "אונליין" in name or "online" in name.lower()

def clean_city_he(city_he, store_name_he):
    """Nettoie city_he — retourne None si invalide"""
    if not city_he:
        return None
    city_he = city_he.strip()
    if city_he in INVALID_CITY_VALUES:
        return None
    # Si city_he ressemble au nom du magasin → invalide
    if store_name_he and len(city_he) > 8 and city_he in (store_name_he or ""):
        return None
    # Supprimer "ה" en trop au début (article hébreu)
    # On garde car certaines villes commencent vraiment par ה
    return city_he

def translate_batch(stores, cities_cache):
    if not openai_client or not stores:
        return []
    
    chain_names_list = "\n".join([f"- {v}" for v in CHAIN_NAMES_FR.values()])
    
    lines = []
    for s in stores:
        chain_name = CHAIN_NAMES_FR.get(s.get("chain_id"), s.get("chain_id", ""))
        lines.append(
            f"ID:{s['id']}|"
            f"CHAINE:{chain_name}|"
            f"NOM_HE:{s.get('store_name_he') or ''}|"
            f"ADRESSE:{s.get('address') or ''}|"
            f"VILLE_HE:{s.get('city_he') or ''}"
        )
    
    prompt = (
        "Tu es un expert en géographie israélienne.\n"
        "Pour chaque magasin, retourne exactement: ID|nom_fr|ville_he|ville_fr|adresse_fr\n\n"
        "=== RÈGLES CRITIQUES ===\n\n"
        "RÈGLE 1 - NOMS DE CHAÎNES (JAMAIS traduire):\n"
        f"{chain_names_list}\n"
        "'Yellow' = TOUJOURS 'Yellow' (JAMAIS 'Jaune')\n"
        "'Shufersal' = TOUJOURS 'Shufersal'\n\n"
        "RÈGLE 2 - nom_fr:\n"
        "Format: '[NOM_CHAINE] [description courte si utile] - [VILLE_FR]'\n"
        "Exemples:\n"
        "- 'Shufersal Express - Tel Aviv'\n"
        "- 'Rami Levy - Jérusalem'\n"
        "- 'Yellow - Haïfa'\n"
        "- 'Shufersal Deal - Beer Sheva'\n"
        "JAMAIS mettre de texte hébreu dans nom_fr\n\n"
        "RÈGLE 3 - ville_he:\n"
        "Extraire UNIQUEMENT le nom de la ville en hébreu.\n"
        "PAS le nom du magasin. PAS le nom de la rue. PAS le nom du quartier.\n"
        "Villes valides: תל אביב, ירושלים, חיפה, באר שבע, נתניה, רחובות, etc.\n"
        "Si VILLE_HE est déjà fournie et semble correcte → utilise-la.\n"
        "Si pas de ville claire → laisse VIDE (ne mets pas 'לא קיים' ou 'INCONNU')\n\n"
        "RÈGLE 4 - ville_fr:\n"
        "Translittération française SANS apostrophe:\n"
        "רעננה = Raanana (pas Ra'anana)\n"
        "כוכב יעקב = Kochav Yaakov (pas Ya'akov)\n"
        "מודיעין = Modiin (pas Modi'in)\n"
        "Autres exemples: Tel Aviv, Jérusalem, Haïfa, Netanya, Beer Sheva,\n"
        "Bnei Brak, Petah Tikva, Rishon LeZion, Ashdod, Ashkelon,\n"
        "Raanana, Kfar Saba, Herzliya, Holon, Bat Yam, Rehovot\n"
        "Si pas de ville → Israël\n\n"
        "RÈGLE 5 - adresse_fr:\n"
        "Traduis l'adresse en français. Garde les numéros.\n"
        "Si pas d'adresse → laisse VIDE\n\n"
        "RÈGLE 6 - JAMAIS de | dans les champs\n"
        "RÈGLE 7 - 1 ligne par magasin, même ordre exact\n\n"
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
    print(f"📦 {len(cities_cache)} villes en cache")
    
    new_cities = {}
    total_updated = 0
    
    while True:
        result = supabase.table("stores")\
            .select("id, chain_id, store_name_he, store_name_fr, city_he, city_fr, address, address_fr")\
            .is_("store_name_fr", "null")\
            .limit(20)\
            .execute()
        
        stores = result.data
        if not stores:
            print("✅ Tous les magasins sont traduits!")
            break
        
        print(f"📦 {len(stores)} magasins restants...")
        
        BATCH = 20
        for i in range(0, len(stores), BATCH):
            batch = stores[i:i+BATCH]
            translations = translate_batch(batch, cities_cache)
            
            for store, line in zip(batch, translations):
                try:
                    parts = line.split("|")
                    if len(parts) < 5:
                        continue
                    
                    nom_fr = parts[1].strip()
                    ville_he_raw = parts[2].strip()
                    ville_fr_gpt = parts[3].strip()
                    adresse_fr = parts[4].strip()
                    
                    # Détecter magasin en ligne
                    if is_online_store(store):
                        ville_fr = "En ligne"
                        ville_he = None
                    else:
                        # Nettoyer ville_he
                        ville_he = clean_city_he(ville_he_raw, store.get("store_name_he"))
                        
                        # Normaliser via cache
                        if ville_he and ville_he in cities_cache:
                            ville_fr = cities_cache[ville_he]
                        elif ville_he:
                            # Supprimer apostrophes
                            ville_fr_clean = ville_fr_gpt.replace("'", "").replace("`", "")
                            ville_fr = ville_fr_clean if ville_fr_clean else "Israël"
                            new_cities[ville_he] = ville_fr
                            cities_cache[ville_he] = ville_fr
                        else:
                            ville_fr = "Israël"
                    
                    # Nettoyer nom_fr
                    # Supprimer apostrophes
                    nom_fr = nom_fr.replace("'", "").replace("`", "")
                    
                    # Vérifier que le nom de chaîne n'est pas traduit
                    chain_name = CHAIN_NAMES_FR.get(store.get("chain_id"), "")
                    if chain_name and not nom_fr.startswith(chain_name):
                        nom_fr = f"{chain_name} - {ville_fr}" if ville_fr and ville_fr not in ("Israël", "En ligne") else chain_name
                    
                    # Si ville en hébreu dans nom_fr → remplacer par ville_fr
                    if ville_he and ville_he in nom_fr:
                        nom_fr = nom_fr.replace(ville_he, ville_fr)
                    
                    # Si nom_fr se termine par " - Israël" → enlever Israël
                    if nom_fr.endswith(" - Israël"):
                        nom_fr = nom_fr[:-9]
                    
                    update_data = {}
                    if nom_fr:
                        update_data["store_name_fr"] = nom_fr
                    if ville_he:
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
                        total_updated += 1
                        
                except Exception as e:
                    print(f"⚠️ Erreur store {store.get('id')}: {e}")
            
            print(f"✅ {total_updated} mis à jour")
            time.sleep(0.5)
    
    # Sauvegarder nouvelles villes avec verified=FALSE
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
