import os, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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

def translate_names(stores):
    """GPT traduit uniquement le nom du magasin — la ville vient de Google Maps"""
    if not openai_client or not stores:
        return []
    
    chain_names_list = "\n".join([f"- {v}" for v in CHAIN_NAMES_FR.values()])
    
    lines = []
    for s in stores:
        chain_name = CHAIN_NAMES_FR.get(s.get("chain_id"), "")
        city_fr = s.get("city_fr") or "Israël"
        lines.append(f"ID:{s['id']}|CHAINE:{chain_name}|NOM_HE:{s.get('store_name_he') or ''}|VILLE:{city_fr}")
    
    prompt = (
        "Tu es un expert en supermarchés israéliens.\n"
        "Pour chaque magasin, retourne: ID|nom_fr\n\n"
        "RÈGLES CRITIQUES:\n"
        f"Noms de chaînes INTOUCHABLES (jamais traduire):\n{chain_names_list}\n\n"
        "Format nom_fr: '[NOM_CHAINE] [type si utile] - [VILLE]'\n"
        "Exemples:\n"
        "- 'Shufersal Express - Tel Aviv'\n"
        "- 'Shufersal Deal - Jérusalem'\n"
        "- 'Rami Levy - Netanya'\n"
        "- 'Yellow - Haïfa'\n"
        "- 'Good Pharm - Beer Sheva'\n\n"
        "JAMAIS de texte hébreu dans nom_fr\n"
        "JAMAIS d'apostrophe\n"
        "1 ligne par magasin, même ordre exact\n"
        "PAS de | dans les champs\n\n"
        "Magasins:\n" + "\n".join(lines)
    )
    
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
        )
        return r.choices[0].message.content.strip().split("\n")
    except Exception as e:
        print(f"⚠️ Erreur GPT: {e}")
        return []

def main():
    print("🏪 Traduction noms magasins démarrée")
    
    total_updated = 0
    
    while True:
        # Magasins avec city_fr mais sans store_name_fr
        result = supabase.table("stores")\
            .select("id, chain_id, store_name_he, store_name_fr, city_fr")\
            .is_("store_name_fr", "null")\
            .not_.is_("city_fr", "null")\
            .limit(200)\
            .execute()
        
        stores = result.data
        if not stores:
            print("✅ Tous les noms sont traduits!")
            break
        
        print(f"📦 {len(stores)} magasins à nommer...")
        
        BATCH = 20
        for i in range(0, len(stores), BATCH):
            batch = stores[i:i+BATCH]
            translations = translate_names(batch)
            
            for store, line in zip(batch, translations):
                try:
                    parts = line.split("|")
                    if len(parts) < 2:
                        continue
                    
                    nom_fr = parts[1].strip().replace("'", "").replace("`", "")
                    
                    # Vérifier que le nom de chaîne est correct
                    chain_name = CHAIN_NAMES_FR.get(store.get("chain_id"), "")
                    if chain_name and not nom_fr.startswith(chain_name):
                        city_fr = store.get("city_fr") or "Israël"
                        nom_fr = f"{chain_name} - {city_fr}" if city_fr != "Israël" else chain_name
                    
                    if nom_fr:
                        supabase.table("stores")\
                            .update({"store_name_fr": nom_fr})\
                            .eq("id", store["id"])\
                            .execute()
                        total_updated += 1
                        
                except Exception as e:
                    print(f"⚠️ Erreur {store.get('id')}: {e}")
            
            print(f"✅ {total_updated} noms traduits")
            time.sleep(0.3)
    
    print(f"🎉 Terminé: {total_updated} noms traduits")

if __name__ == "__main__":
    main()
