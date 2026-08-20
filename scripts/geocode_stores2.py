import os, time, requests
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

NORMALIZATIONS = {
    "Tel Aviv-Yafo": "Tel Aviv",
    "Tel Aviv-Jaffa": "Tel Aviv",
    "Be'er Sheva": "Beer Sheva",
    "Ra'anana": "Raanana",
    "Giv'atayim": "Givatayim",
    "Kefar Sava": "Kfar Saba",
    "Modi'in-Maccabim-Re'ut": "Modiin",
    "Modi'in Makabim-Re'ut": "Modiin",
    "Bet Shemesh": "Beit Shemesh",
    "El'ad": "Elad",
    "Qiryat Shemona": "Kiryat Shmona",
    "Pardes Hanna-Karkur": "Pardes Hanna",
    "Rosh Haayin": "Rosh HaAyin",
    "Yehud-Monosson": "Yehud",
    "Betar Illit": "Beitar Illit",
    "Nahariyya": "Nahariya",
    "Akko": "Acre",
    "Hod Hasharon": "Hod HaSharon",
    "Natsrat Ilit": "Nof HaGalil",
    "Jerusalem": "Jérusalem",
    "Haifa": "Haïfa",
    "Beersheba": "Beer Sheva",
    "Kiryat Tiv'on": "Kiryat Tivon",
    "Giv'at Shmuel": "Givat Shmuel",
    "Ma'ale Adumim": "Maale Adumim",
    "Ma'alot-Tarshiha": "Maalot Tarshiha",
    "Binyamina-Giv'at Ada": "Binyamina",
    "Yokne'am Illit": "Yokneam",
    "Peki'in": "Pekin",
    "Zikhron Ya'akov": "Zichron Yaakov",
    "Giv'at Ze'ev": "Givat Zeev",
    "Kokhav Ya'ir": "Kokhav Yair",
    "Yehud-Monosson": "Yehud",
    "Gan Shmu'el": "Gan Shmuel",
}

def geocode_store(store_name, address):
    """Géocode avec nom + adresse pour meilleure précision"""
    query = store_name or ""
    if address and "http" not in address:
        query = f"{query} {address}"
    query = query.strip() + ", Israel"
    
    result = {"lat": None, "lng": None, "city_fr": None, "city_he": None, "address_fr": None}
    
    # Appel français
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": query, "language": "fr", "region": "il", "key": GOOGLE_API_KEY},
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
                    city = comp["long_name"]
                    result["city_fr"] = NORMALIZATIONS.get(city, city)
                    break
    except Exception as e:
        print(f"⚠️ Erreur geocode FR: {e}")
        return None
    
    if not result["lat"]:
        return None
    
    # Appel hébreu
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": query, "language": "iw", "region": "il", "key": GOOGLE_API_KEY},
            timeout=10
        )
        data = r.json()
        if data["status"] == "OK" and data["results"]:
            for comp in data["results"][0]["address_components"]:
                if "locality" in comp["types"]:
                    result["city_he"] = comp["long_name"]
                    break
    except:
        pass
    
    return result

def main():
    print("🗺️ Regéocodage des 864 magasins démarré")
    
    # Charger les villes vérifiées pour identifier les 829 déjà traités
    cities_result = supabase.table("cities")\
        .select("name_he")\
        .eq("verified", True)\
        .execute()
    verified_cities = {r["name_he"] for r in cities_result.data}
    
    # Charger tous les magasins
    stores = []
    offset = 0
    while True:
        result = supabase.table("stores")\
            .select("id, store_name_he, address, city_fr, latitude, longitude")\
            .range(offset, offset + 999)\
            .execute()
        if not result.data:
            break
        stores.extend(result.data)
        if len(result.data) < 1000:
            break
        offset += 1000
    all_stores = stores
    
    # Filtrer uniquement les 864 sans ville dans le nom
    stores_to_process = []
    for store in all_stores:
        name = store.get("store_name_he") or ""
        has_city_in_name = any(
            len(city) >= 3 and city in name 
            for city in verified_cities
        )
        if not has_city_in_name:
            stores_to_process.append(store)
    
    print(f"📦 {len(stores_to_process)} magasins à regéocoder")
    
    updated = 0
    no_result = 0
    
    for i, store in enumerate(stores_to_process):
        geo = geocode_store(
            store.get("store_name_he", ""),
            store.get("address", "")
        )
        
        if not geo or not geo["lat"]:
            no_result += 1
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
        
        if (i+1) % 50 == 0:
            print(f"✅ [{i+1}/{len(stores_to_process)}] {updated} mis à jour, {no_result} sans résultat")
        
        time.sleep(0.13)
    
    print(f"🎉 Terminé: {updated} mis à jour, {no_result} sans résultat")

if __name__ == "__main__":
    main()
