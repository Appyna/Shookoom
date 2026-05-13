"""
import_kaggle.py — Shookoom
Import complet Kaggle → Supabase avec traduction Claude API
Fichiers supportés : price_full_file_[chain].json / price_file_[chain].json

Usage:
  pip install -r requirements.txt
  python import_kaggle.py --data-dir ./kaggle_data
"""

import os, re, json, time, argparse, requests
from pathlib import Path
from datetime import datetime

SUPABASE_URL  = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "https://iwqaichmldpsutfujoco.supabase.co")
SUPABASE_KEY  = os.environ.get("SUPABASE_SERVICE_KEY")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")

HEADERS_SB = {
    "apikey": SUPABASE_KEY or "",
    "Authorization": f"Bearer {SUPABASE_KEY or ''}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

# 33 chaînes complètes
CHAINS = {
    "rami_levy":                   ("Rami Levy",              "רמי לוי"),
    "shufersal":                   ("Shufersal",              "שופרסל"),
    "osher_ad":                    ("Osher Ad",               "אושר עד"),
    "victory":                     ("Victory",                "ויקטורי"),
    "tiv_taam":                    ("Tiv Taam",               "טיב טעם"),
    "yohananof":                   ("Yohananof",              "יוחננוף"),
    "hazi_hinam":                  ("Hazi Hinam",             "חצי חינם"),
    "yeinot_bitan":                ("Yeinot Bitan/Carrefour", "יינות ביתן"),
    "mega":                        ("Mega",                   "מגה"),
    "dor_alon":                    ("Dor Alon",               "דור אלון"),
    "bareket":                     ("Bareket",                "ברקת"),
    "mahsani_ashuk":               ("Mahsani A'Shuk",         "מחסני השוק"),
    "zol_vebegadol":               ("Zol VeBegadol",          "זול ובגדול"),
    "super_pharm":                 ("Super-Pharm",            "סופר פארם"),
    "king_store":                  ("King Store",             "קינג סטור"),
    "stop_market":                 ("Stop Market",            "סטופ מרקט"),
    "polizer":                     ("Polizer",                "פוליצר"),
    "good_pharm":                  ("Good Pharm",             "גוד פארם"),
    "keshet_taamim":               ("Keshet Taamim",          "קשת טעמים"),
    "cofix":                       ("Cofix",                  "קופיקס"),
    "het_cohen":                   ("Het Cohen",              "ח. כהן"),
    "salach_dabach":               ("Salach D'abach",         "סאלח דבאח"),
    "super_yuda":                  ("Super Yuda",             "סופר יודה"),
    "super_sapir":                 ("Super Sapir",            "סופר ספיר"),
    "quik":                        ("Quik",                   "קוויק"),
    "maayan_2000":                 ("Maayan 2000",            "מעיין אלפיים"),
    "netiv_hahesed":               ("Netiv HaHesed",          "נתיב החסד"),
    "shefa_birkat_hashem":         ("Shefa Birkat Hashem",    "שפע ברכת השם"),
    "shuk_hair":                   ("Shuk Ha'Ir",             "שוק העיר"),
    "yellow":                      ("Yellow",                 "יילו"),
    "fresh_market_and_super_dosh": ("Fresh Market/Super Dosh","פרש מרקט"),
    "meshnat_yosef":               ("Meshnat Yosef",          "משנת יוסף"),
    "city_market_shops":           ("City Market",            "סיטי מרקט"),
}

# Catégorisation automatique par mots-clés hébreux
CATEGORY_KEYWORDS = {
    1:  ["חלב", "גבינ", "יוגורט", "קוטג", "שמנת", "חמאה", "ביצ"],
    2:  ["עוף", "בשר", "פרג", "כבש", "הודו", "נקניק", "סלמי", "שניצל"],
    3:  ["תפוח", "בננ", "עגבני", "מלפפ", "גזר", "תפוז", "פלפל", "ירק", "פרי"],
    4:  ["לחם", "פית", "חלה", "עוגי", "ביסקו", "קרקר", "מאפ"],
    5:  ["קפוא", "גלידה", "פיצ"],
    6:  ["מיץ", "מים", "קולה", "פפסי", "בירה", "יין", "אלכוהול", "קפה", "תה", "משקה"],
    7:  ["אורז", "פסטה", "שמן", "סוכר", "מלח", "רוטב", "שימור", "קמח", "דגן"],
    8:  ["שמפו", "סבון", "קרם", "משחת שינ", "דאודור", "טיפוח", "קרן"],
    9:  ["ניקוי", "סבון כלים", "אקונומיקה", "מגבון", "נייר טואלט"],
    10: ["טיטול", "מוצץ", "פורמולה", "דייסה"],
}

def categorize(name_he):
    for cat_id, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_he:
                return cat_id
    return 7

def translate_batch(names_he):
    if not names_he or not ANTHROPIC_KEY:
        return names_he
    prompt = (
        "Tu es un traducteur expert hébreu→français spécialisé en produits de supermarché israélien.\n"
        "Traduis chaque nom de produit en français naturel et commercial.\n"
        "Règles: sois concis, garde les marques (Tnuva, Elite, Osem...), "
        "si déjà en anglais/français garde tel quel.\n"
        "Réponds UNIQUEMENT avec un JSON array de strings, même ordre, rien d'autre.\n\n"
        f"Noms: {json.dumps(names_he, ensure_ascii=False)}"
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        text = r.json()["content"][0]["text"].strip()
        text = re.sub(r"^```json|^```|```$", "", text, flags=re.MULTILINE).strip()
        result = json.loads(text)
        return result if len(result) == len(names_he) else names_he
    except Exception as e:
        print(f"  ⚠️  Traduction échouée: {e}")
        return names_he

def sb_upsert(table, rows):
    if not rows:
        return
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS_SB, json=rows)
    if r.status_code not in (200, 201):
        print(f"  ⚠️  {table}: {r.status_code} {r.text[:150]}")

def sb_get_translated_barcodes():
    r = requests.get(f"{SUPABASE_URL}/rest/v1/products?select=barcode&translated_at=not.is.null&limit=200000", headers=HEADERS_SB)
    return {row["barcode"] for row in r.json()} if r.status_code == 200 else set()

def sb_get_barcode_ids(barcodes):
    result = {}
    for i in range(0, len(barcodes), 500):
        chunk = barcodes[i:i+500]
        r = requests.get(f"{SUPABASE_URL}/rest/v1/products?select=id,barcode&barcode=in.({','.join(chunk)})", headers=HEADERS_SB)
        if r.status_code == 200:
            for row in r.json():
                result[row["barcode"]] = row["id"]
    return result

def load_json(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return raw
    # Structure Kaggle : {"rows": [...]} ou {"data": [...]}
    for key in ("rows", "data", "items", "products", "prices", "records"):
        if key in raw and isinstance(raw[key], list):
            return raw[key]
    # Parfois la structure est {"root": {"events": [...]}}
    if "root" in raw and "events" in raw["root"]:
        return raw["root"]["events"]
    return []

def import_chain(slug, name_fr, data_dir):
    print(f"\n{'─'*50}")
    print(f"  📦  {name_fr}  ({slug})")

    # Cherche le fichier prix (full snapshot en priorité)
    candidates = [
        data_dir / f"price_full_file_{slug}.json",
        data_dir / f"{slug}_price_full_file.json",
        data_dir / f"price_file_{slug}.json",
        data_dir / f"{slug}_price_file.json",
    ]
    price_file = next((p for p in candidates if p.exists()), None)
    if not price_file:
        print(f"  ⚠️  Aucun fichier prix — ignoré")
        return

    print(f"  📄  {price_file.name}")
    rows = load_json(price_file)
    if not rows:
        print(f"  ⚠️  Fichier vide ou format inconnu")
        return
    print(f"  🔢  {len(rows)} lignes")

    translated_barcodes = sb_get_translated_barcodes()
    seen = set()
    products_new = []
    all_prices = []

    for row in rows:
        barcode = str(row.get("ItemCode") or row.get("item_code") or row.get("barcode") or "").strip()
        name_he = str(row.get("ItemName") or row.get("item_name") or row.get("name") or "").strip()
        price_raw = row.get("ItemPrice") or row.get("price") or 0
        store_id = str(row.get("StoreID") or row.get("store_id") or "").strip()
        updated = row.get("PriceUpdateTime") or row.get("price_updated_at")

        if not barcode or not name_he:
            continue
        try:
            price = float(str(price_raw).replace(",", "."))
        except:
            continue
        if price <= 0:
            continue

        key = f"{barcode}_{slug}"
        if key in seen:
            continue
        seen.add(key)

        if barcode not in translated_barcodes:
            products_new.append({"barcode": barcode, "name_he": name_he})

        all_prices.append({
            "barcode": barcode,
            "price": price,
            "chain_id": slug,
            "store_id": f"{slug}_{store_id}" if store_id else None,
            "price_updated_at": str(updated) if updated else None,
        })

    print(f"  🧹  {len(all_prices)} produits uniques | {len(products_new)} nouveaux à traduire")

    # Traduction par batch de 50
    upsert_products = []
    BATCH = 50
    for i in range(0, len(products_new), BATCH):
        batch = products_new[i:i+BATCH]
        print(f"  🌐  Traduction {i+1}–{min(i+BATCH, len(products_new))}/{len(products_new)} …")
        names_fr = translate_batch([p["name_he"] for p in batch])
        time.sleep(0.3)
        for j, prod in enumerate(batch):
            upsert_products.append({
                "barcode": prod["barcode"],
                "name_he": prod["name_he"],
                "name_fr": names_fr[j] if j < len(names_fr) else prod["name_he"],
                "category_id": categorize(prod["name_he"]),
                "translated_at": datetime.utcnow().isoformat(),
            })

    for i in range(0, len(upsert_products), 200):
        sb_upsert("products", upsert_products[i:i+200])

    # Résolution barcode → ID
    bc_to_id = sb_get_barcode_ids(list({p["barcode"] for p in all_prices}))

    prices_rows = []
    for p in all_prices:
        pid = bc_to_id.get(p["barcode"])
        if not pid:
            continue
        prices_rows.append({
            "product_id": pid,
            "chain_id": p["chain_id"],
            "store_id": p["store_id"],
            "price": p["price"],
            "price_updated_at": p["price_updated_at"],
            "imported_at": datetime.utcnow().isoformat(),
        })

    for i in range(0, len(prices_rows), 500):
        sb_upsert("prices", prices_rows[i:i+500])

    print(f"  ✅  {len(prices_rows)} prix importés")

def ensure_chains():
    rows = [{"id": slug, "name_fr": name_fr, "name_he": name_he} for slug, (name_fr, name_he) in CHAINS.items()]
    sb_upsert("chains", rows)
    print(f"✅  {len(rows)} chaînes synchronisées dans Supabase")

def main():
    parser = argparse.ArgumentParser(description="Import Kaggle → Supabase pour Shookoom")
    parser.add_argument("--data-dir", default="./kaggle_data")
    parser.add_argument("--only", nargs="*", help="Chaînes spécifiques (ex: rami_levy shufersal)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌  Dossier introuvable: {data_dir}")
        print("Télécharge depuis: https://www.kaggle.com/datasets/erlichsefi/israeli-supermarkets-2024")
        return
    if not SUPABASE_KEY:
        print("❌  SUPABASE_SERVICE_KEY manquante dans les variables d'environnement")
        return

    print("🚀  Import Shookoom démarré")
    print(f"📁  {data_dir.resolve()}")
    print(f"🕐  {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    ensure_chains()

    for slug in (args.only or list(CHAINS.keys())):
        if slug in CHAINS:
            import_chain(slug, CHAINS[slug][0], data_dir)
        else:
            print(f"⚠️  Chaîne inconnue: {slug}")

    print(f"\n{'═'*50}")
    print("🎉  Import terminé !")

if __name__ == "__main__":
    main()
