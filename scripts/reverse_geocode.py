import os, time, requests
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DEFAULT_LAT = 31.046051
DEFAULT_LNG = 34.851612

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
    "Kokhav Ya'akov": "Kochav Yaakov",
    "Ma'ale Adumim": "Maale Adumim",
    "Ma'alot-Tarshiha": "Maalot Tarshiha",
    "Binyamina-Giv'at Ada": "Binyamina",
    "Yokne'am Illit": "Yokneam",
    "Peki'in": "Pekin",
    "Zikhron Ya'akov": "Zichron Yaakov",
    "Kiryat Tiv'on": "Kiryat Tivon",
    "Giv'at Shmuel": "Givat Shmuel",
    "Giv'at Ze'ev": "Givat Zeev",
    "Kiryat-Ata": "Kiryat Ata",
    "Kiryat-Yam": "Kiryat Yam",
    "Kiryat-Malakhi": "Kiryat Malakhi",
    "Gan Shmu'el": "Gan Shmuel",
    "Yesud HaMa'ala": "Yesud HaMaala",
    "Ne'ot Mordehai": "Neot Mordechai",
    "Ge'alya": "Gealya",
    "HaMa'apil": "HaMaapil",
    "Ami'ad": "Amiad",
    "Bi'ina": "Biina",
    "Tur'an": "Turan",
    "Yas'ur": "Yasur",
    "Ma'anit": "Maanit",
    "Ya'af": "Yaaf",
    "Mele'a": "Melea",
    "Hashmona'im": "Hashmonaim",
    "Jérusalem": "Jérusalem",
    "Jerusalem": "Jérusalem",
    "Haifa": "Haïfa",
}

def reverse_geocode(lat, lng):
    """Reverse geocoding depuis GPS — retourne ville FR et HE"""
    result = {"city_fr": None, "city_he": None, "address_fr": None}
    
    # Appel français
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"latlng": f"{lat},{lng}", "language": "fr", "region": "il", "key": GOOGLE_API_KEY},
            timeout=10
        )
        data = r.json()
        if data["status"] == "OK" and data["results"]:
            res = data["results"][0]
            result["address_fr"] = res.get("formatted_address", "").replace(", Israël", "").replace(", Israel", "").strip()
            for comp in res["address_components"]:
                if "locality" in comp["types"]:
                    city = comp["long_name"]
                    result["city_fr"] = NORMALIZATIONS.get(city, city)
                    break
    except Exception as e:
        print(f"⚠️ Erreur reverse FR: {e}")
    
    # Appel hébreu
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"latlng": f"{lat},{lng}", "language": "iw", "region": "il", "key": GOOGLE_API_KEY},
            timeout=10
        )
        data = r.json()
        if data["status"] == "OK" and data["results"]:
            for comp in data["results"][0]["address_components"]:
                if "locality" in comp["types"]:
                    result["city_he"] = comp["long_name"]
                    break
    except Exception as e:
        print(f"⚠️ Erreur reverse HE: {e}")
    
    return result

def main():
    print("🗺️ Reverse geocoding démarré")
    
    # Charger magasins avec vrai GPS (pas le GPS par défaut)
    result = supabase.table("stores")\
        .select("id, store_name_he, latitude, longitude, city_fr")\
        .is_("city_fr", "null")\
        .limit(2000)\
        .execute()
    
    stores = [s for s in result.data 
              if s["latitude"] != DEFAULT_LAT or s["longitude"] != DEFAULT_LNG]
    
    print(f"📦 {len(stores)} magasins à reverse geocoder")
    
    updated = 0
    no_city = 0
    
    for i, store in enumerate(stores):
        geo = reverse_geocode(store["latitude"], store["longitude"])
        
        update_data = {}
        if geo["city_fr"]:
            update_data["city_fr"] = geo["city_fr"]
        else:
            update_data["city_fr"] = "Israël"
            no_city += 1
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
        
        if (i+1) % 100 == 0:
            print(f"✅ [{i+1}/{len(stores)}] {updated} mis à jour, {no_city} sans ville")
        
        time.sleep(0.12)
    
    print(f"🎉 Terminé: {updated} mis à jour, {no_city} sans ville trouvée")

if __name__ == "__main__":
    main()
