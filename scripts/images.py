"""
images.py — Collecte images produits
Sources : Pricez, Victory CloudFront, Rami Levy, SaveMyCart
"""
import os, time, urllib.request, json
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_image(url, min_size=5000):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=4)
        size = int(r.headers.get("Content-Length", 0))
        ct = r.headers.get("Content-Type", "")
        return "image" in ct and size > min_size
    except:
        return False

def get_image_pricez(barcode):
    url = f"https://m.pricez.co.il/ProductPictures/{barcode}.jpg"
    if check_image(url, min_size=5000):
        return url, "pricez"
    return None, None

def get_image_victory(barcode):
    try:
        api = f"https://www.victoryonline.co.il/api/products/{barcode}"
        req = urllib.request.Request(api, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.victoryonline.co.il/"
        })
        r = urllib.request.urlopen(req, timeout=4)
        data = json.loads(r.read())
        img = data.get("product", {}).get("images", {}).get("small")
        if img:
            return img, "victory"
    except:
        pass
    return None, None

def get_image_rami(barcode):
    url = f"https://img.rami-levy.co.il/product/{barcode}/small.jpg"
    if check_image(url, min_size=1000):
        return url, "rami_levy"
    return None, None

def get_image_savemycart(barcode):
    try:
        url = f"https://savemycart.net/api/v1/products/?search={barcode}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })
        r = urllib.request.urlopen(req, timeout=6)
        data = json.loads(r.read())
        results = data.get("results", [])
        matching = [p for p in results if p.get("item_code") == barcode]
        if not matching:
            return None, None
        prod_id = matching[0]["id"]
        url2 = f"https://savemycart.net/api/v1/products/{prod_id}/"
        req2 = urllib.request.Request(url2, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })
        r2 = urllib.request.urlopen(req2, timeout=6)
        data2 = json.loads(r2.read())
        img = data2.get("details", {}).get("picture_url") if data2.get("details") else None
        if img:
            return img, "savemycart"
    except:
        pass
    return None, None

def get_image(barcode):
    # Source 1: Pricez (35%)
    img, src = get_image_pricez(barcode)
    if img:
        return img, src
    # Source 2: Victory (15%)
    img, src = get_image_victory(barcode)
    if img:
        return img, src
    # Source 3: Rami Levy (0.3%)
    img, src = get_image_rami(barcode)
    if img:
        return img, src
    # Source 4: SaveMyCart (3%)
    img, src = get_image_savemycart(barcode)
    if img:
        return img, src
    return None, None

def main():
    print("🖼️ Collecte images démarrée")

    # Produits sans image
    result = supabase.table("products")\
        .select("id, barcode, image_url")\
        .is_("image_url", "null")\
        .limit(3000)\
        .execute()

    products = result.data
    print(f"📦 {len(products)} produits sans image")

    if not products:
        print("✅ Toutes les images sont déjà collectées!")
        return

    found = 0
    for i, p in enumerate(products):
        bc = p["barcode"]
        img_url, source = get_image(bc)

        if img_url:
            supabase.table("products")\
                .update({"image_url": img_url})\
                .eq("id", p["id"])\
                .execute()
            found += 1
            if found <= 20 or found % 50 == 0:
                print(f"✅ [{i+1}] {bc}: {source}")

        if (i+1) % 100 == 0:
            print(f"[{i+1}/{len(products)}] trouvés: {found}")

        time.sleep(0.15)

    print(f"🎉 Terminé: {found}/{len(products)} images trouvées")

if __name__ == "__main__":
    main()
