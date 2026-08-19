import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def main():
    print("🏙️ Correction villes depuis noms magasins")
    
    # Charger toutes les villes vérifiées
    cities_result = supabase.table("cities")\
        .select("name_he, name_fr")\
        .eq("verified", True)\
        .execute()
    
    cities = cities_result.data
    print(f"📦 {len(cities)} villes vérifiées")
    
    # Charger tous les magasins avec pagination
    stores = []
    offset = 0
    while True:
        result = supabase.table("stores")\
            .select("id, store_name_he, city_fr, city_he")\
            .range(offset, offset + 999)\
            .execute()
        if not result.data:
            break
        stores.extend(result.data)
        if len(result.data) < 1000:
            break
        offset += 1000
    
    print(f"📦 {len(stores)} magasins à analyser")
    
    updated = 0
    
    for store in stores:
        name = store.get("store_name_he") or ""
        if not name:
            continue
        
        found_city_he = None
        found_city_fr = None
        
        for city in cities:
            city_he = city["name_he"]
            if len(city_he) >= 3 and city_he in name:
                found_city_he = city_he
                found_city_fr = city["name_fr"]
                break
        
        if found_city_he and found_city_fr:
            if store.get("city_fr") != found_city_fr or store.get("city_he") != found_city_he:
                try:
                    supabase.table("stores")\
                        .update({"city_fr": found_city_fr, "city_he": found_city_he})\
                        .eq("id", store["id"])\
                        .execute()
                    updated += 1
                except Exception as e:
                    print(f"⚠️ Erreur {store['id']}: {e}")
    
    print(f"🎉 Terminé: {updated} villes corrigées")

if __name__ == "__main__":
    main()
