import os, time, requests
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def geocode(query):
    """
    Appel unique Google Maps — retourne tout en une requête.
    On fait 2 appels : un en français pour city_fr/address_fr, un en hébreu pour city_he.
    """
    if not query or not GOOGLE_API_KEY:
        return None
    
    result = {"lat": None, "lng": None, "city_fr": None, "city_he": None, "address_fr": None}
    
    # Appel 1 — français
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": query + ", Israel", "language": "fr", "region": "il", "key": GOOGLE_API_KEY},
            timeout=10
        )
        data = r.json()
        if data["status"] == "OK" and data["results"]:
            res = data["results"][0]
            result["lat"] = res["geometry"]["location"]["lat"]
            result["lng"] = res["geometry"]["location"]["lng"]
            result["address_fr"] = res.get("formatted_address", "").replace(", Israël", "").replace(", Israel", "").strip()
            for comp in res["address_components"]:
                if "locality" in comp["types"]:
                    result["city_fr"] = comp["long_name"]
                    break
    except Exception as e:
        print(f"⚠️ Erreur geocode FR: {e}")
        return None
    
    if not result["lat"]:
        return None
    
    # Appel 2 — hébreu pour city_he
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": query + ", Israel", "language": "iw", "region": "il", "key": GOOGLE_API_KEY},
            timeout=10
        )
        data = r.json()
        if data["status"] == "OK" and data["results"]:
            for comp in data["results"][0]["address_components"]:
                if "locality" in comp["types"]:
                    result["city_he"] = comp["long_name"]
                    break
    except Exception as e:
        print(f"⚠️ Erreur geocode HE: {e}")
    
    return result

def build_query(store):
    """Construit la meilleure requête possible pour chaque magasin"""
    address = (store.get("address") or "").strip()
    city_he = (store.get("city_he") or "").strip()
    name = (store.get("store_name_he") or "").strip()
    
    # Priorité 1 — adresse complète
    if address and len(address) > 5:
        return address
    
    # Priorité 2 — adresse dans le nom (City Market format: "nom, adresse ville")
    if "," in name:
        parts = name.split(",")
        if len(parts) >= 2:
            addr_part = parts[-1].strip()
            if any(char.isdigit() for char in addr_part) or len(addr_part) > 5:
                return addr_part
    
    # Priorité 3 — ville en hébreu seule
    if city_he and len(city_he) > 2:
        return city_he
    
    # Priorité 4 — nom du magasin
    return name

def main():
    print("🗺️ Géocodage des magasins démarré")
    
    # Charger tous les magasins
    result = supabase.table("stores")\
        .select("id, chain_id, store_name_he, address, city_he, city_fr, latitude, longitude")\
        .is_("latitude", "null")\
        .limit(2000)\
        .execute()
    
    stores = result.data
    print(f"📦 {len(stores)} magasins à géocoder")
    
    updated = 0
    failed = 0
    
    for i, store in enumerate(stores):
        query = build_query(store)
        
        if not query:
            failed += 1
            continue
        
        geo = geocode(query)
        
        if not geo:
            failed += 1
            # Marquer comme traité avec ville = Israël
            try:
                supabase.table("stores")\
                    .update({"city_fr": "Israël", "latitude": 31.5, "longitude": 34.75})\
                    .eq("id", store["id"])\
                    .execute()
            except:
                pass
            continue
        
        update_data = {
            "latitude": geo["lat"],
            "longitude": geo["lng"],
        }
        if geo["city_fr"]:
            update_data["city_fr"] = geo["city_fr"]
        else:
            update_data["city_fr"] = "Israël"
        if geo["city_he"]:
            update_data["city_he"] = geo["city_he"]
        if geo["address_fr"]:
            update_data["address_fr"] = geo["address_fr"]
        
        try:
            supabase.table("stores")\
                .update(update_data)\
                .eq("id", store["id"])\
                .execute()
            updated += 1
        except Exception as e:
            print(f"⚠️ Erreur update {store['id']}: {e}")
            failed += 1
        
        if (i+1) % 50 == 0:
            print(f"✅ [{i+1}/{len(stores)}] {updated} géocodés, {failed} échoués")
        
        time.sleep(0.12)  # Max ~8 req/sec pour rester safe
    
    print(f"🎉 Terminé: {updated} géocodés, {failed} sans résultat")

if __name__ == "__main__":
    main()
