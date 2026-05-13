"""
import_scarper.py — Poomby
Scrape toutes les chaînes israéliennes → Supabase
"""
import os, re, json, time, gzip, xml.etree.ElementTree as ET
import urllib.request, urllib.error
from datetime import datetime

print("🚀 Import Poomby démarré")
print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DUMP_FOLDER = "./scraper_dumps"

# ── Polyfill anext pour Python < 3.10 ────────────────────────────────────────
import builtins
if not hasattr(builtins, "anext"):
    async def _anext(it, *args):
        try:
            return await it.__anext__()
        except StopAsyncIteration:
            if args:
                return args[0]
            raise
    builtins.anext = _anext

# ── Supabase helpers ──────────────────────────────────────────────────────────
def supa_post(table, records, upsert_on=None):
    if not records:
        return []
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation" if upsert_on else "return=representation"
    }
    data = json.dumps(records, ensure_ascii=False).encode("utf-8")
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if upsert_on:
        url += f"?on_conflict={upsert_on}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ Supabase {table} {e.code}: {e.read().decode()[:200]}")
        return []
    except Exception as e:
        print(f"  ⚠️ Supabase {table}: {e}")
        return []

def supa_get(table, params=""):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{params}",
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠️ Supabase GET {table}: {e}")
        return []

# ── Traduction OpenAI ─────────────────────────────────────────────────────────
def translate_batch(texts):
    if not OPENAI_API_KEY:
        return texts
    clean = [re.sub(r'[\x00-\x1f\x7f]', ' ', t).strip() for t in texts]
    prompt = "Traduis ces noms de produits hébreux en français. Réponds UNIQUEMENT avec un JSON array des traductions dans le même ordre:\n" + json.dumps(clean, ensure_ascii=False)
    data = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            content = resp["choices"][0]["message"]["content"].strip()
            content = re.sub(r"```json|```", "", content).strip()
            return json.loads(content)
    except Exception as e:
        print(f"  ⚠️ Traduction: {e}")
        return texts

# ── Parse XML ─────────────────────────────────────────────────────────────────
def parse_xml_file(filepath):
    rows = []
    try:
        if filepath.endswith(".gz"):
            with gzip.open(filepath, 'rb') as f:
                content = f.read()
        else:
            with open(filepath, 'rb') as f:
                content = f.read()
        root = ET.fromstring(content)
        chain_id = ""
        store_id = ""
        for tag in ["ChainId", "ChainID"]:
            el = root.find(f".//{tag}")
            if el is not None:
                chain_id = el.text or ""
                break
        for tag in ["StoreId", "StoreID"]:
            el = root.find(f".//{tag}")
            if el is not None:
                store_id = el.text or ""
                break
        for item in root.iter("Item"):
            name = ""
            for tag in ["ItemName", "itemname"]:
                el = item.find(tag)
                if el is not None and el.text:
                    name = el.text.strip()
                    break
            if not name:
                continue
            barcode = ""
            for tag in ["ItemCode", "itemcode"]:
                el = item.find(tag)
                if el is not None and el.text:
                    barcode = el.text.strip()
                    break
            price_raw = "0"
            for tag in ["ItemPrice", "itemprice"]:
                el = item.find(tag)
                if el is not None and el.text:
                    price_raw = el.text.strip()
                    break
            rows.append({
                "barcode": barcode,
                "name_he": name,
                "chain_id": chain_id,
                "store_id": store_id,
                "price_raw": price_raw,
            })
    except Exception as e:
        print(f"  ⚠️ Parse {filepath}: {e}")
    return rows

# ── Main ──────────────────────────────────────────────────────────────────────
from il_supermarket_scarper import ScraperFactory
from il_supermarket_scarper.utils.file_output import DiskFileOutput

CHAIN_NAMES_FR = {
    "BAREKET": "Bareket",
    "YAYNO_BITAN_AND_CARREFOUR": "Carrefour / Yeinot Bitan",
    "COFIX": "Cofix",
    "CITY_MARKET_SHOPS": "City Market",
    "CITY_MARKET_KIRYATGAT": "City Market Kiryat Gat",
    "DOR_ALON": "Dor Alon",
    "FRESH_MARKET_AND_SUPER_DOSH": "Fresh Market",
    "GOOD_PHARM": "Good Pharm",
    "HAZI_HINAM": "Hazi Hinam",
    "HET_COHEN": "Het Cohen",
    "KESHET": "Keshet",
    "KING_STORE": "King Store",
    "MAAYAN_2000": "Maayan 2000",
    "MAHSANI_ASHUK": "Mahsani Ashuk",
    "MESHMAT_YOSEF_1": "Meshnat Yosef",
    "MESHMAT_YOSEF_2": "Meshnat Yosef 2",
    "NETIV_HASED": "Netiv Hased",
    "OSHER_AD": "Osher Ad",
    "POLIZER": "Polizer",
    "RAMI_LEVY": "Rami Levy",
    "SALACH_DABACH": "Salach Dabach",
    "SHEFA_BARCART_ASHEM": "Shefa Barchat Hashem",
    "SHUFERSAL": "Shufersal",
    "SHUK_AHIR": "Shuk Hair",
    "STOP_MARKET": "Stop Market",
    "SUPER_PHARM": "Super Pharm",
    "SUPER_SAPIR": "Super Sapir",
    "SUPER_YUDA": "Super Yuda",
    "TIV_TAAM": "Tiv Taam",
    "VICTORY": "Victory",
    "VICTORY_NEW_SOURCE": "Victory",
    "WOLT": "Wolt",
    "YELLOW": "Yellow",
    "YOHANANOF": "Yohananof",
    "ZOL_VEBEGADOL": "Zol Vebegadol",
}

os.makedirs(DUMP_FOLDER, exist_ok=True)
total_imported = 0
product_cache = {}
BATCH = 50

all_chains = ScraperFactory.all_scrapers_name()
print(f"📋 {len(all_chains)} chaînes à traiter")

for chain_name in all_chains:
    print(f"\n🏪 {chain_name}")
    chain_dump = os.path.join(DUMP_FOLDER, chain_name)
    os.makedirs(chain_dump, exist_ok=True)

    try:
        scraper_class = ScraperFactory.get(chain_name)
        output = DiskFileOutput(storage_path=os.path.abspath(chain_dump))
        scraper = scraper_class(file_output=output)
        results = list(scraper.scrape(limit=50))
        downloaded = [r for r in results if getattr(r, 'downloaded', False)]
        print(f"  📥 {len(downloaded)} fichiers téléchargés")
    except Exception as e:
        print(f"  ⚠️ Scraping échoué: {e}")
        continue

    # Trouver les fichiers XML téléchargés
    xml_files = []
    for root_dir, dirs, files in os.walk(chain_dump):
        for f in files:
            if "Price" in f and not "Promo" in f:
                xml_files.append(os.path.join(root_dir, f))

    if not xml_files:
        print(f"  ⚠️ Aucun fichier Prix trouvé")
        continue

    print(f"  📂 {len(xml_files)} fichiers prix")

    all_rows = []
    for xml_file in xml_files[:10]:
        rows = parse_xml_file(xml_file)
        all_rows.extend(rows)

    print(f"  📦 {len(all_rows)} produits")
    if not all_rows:
        continue

    chain_id = all_rows[0]["chain_id"] or chain_name
    name_fr = CHAIN_NAMES_FR.get(chain_name, chain_name)

    # Insertion chaîne
    supa_post("chains", [{
        "id": chain_id,
        "name_fr": name_fr,
        "name_he": chain_name
    }], upsert_on="id")

    # Insertion stores
    stores_seen = set()
    stores_to_insert = []
    for row in all_rows:
        if row["store_id"] and row["store_id"] not in stores_seen:
            stores_seen.add(row["store_id"])
            stores_to_insert.append({
                "id": f"{chain_id}_{row['store_id']}",
                "chain_id": chain_id,
                "store_id": row["store_id"],
            })
    for i in range(0, len(stores_to_insert), BATCH):
        supa_post("stores", stores_to_insert[i:i+BATCH], upsert_on="id")

    # Traduction
    print(f"  🌐 Traduction...")
    names_he = [r["name_he"] for r in all_rows]
    names_fr = list(names_he)
    for i in range(0, len(all_rows), BATCH):
        batch = names_he[i:i+BATCH]
        translated = translate_batch(batch)
        for j in range(len(batch)):
            names_fr[i+j] = translated[j] if j < len(translated) else batch[j]
        time.sleep(0.2)

    # Insertion produits
    print(f"  💾 Produits...")
    product_records = []
    seen_barcodes = set()
    for i, row in enumerate(all_rows):
        if row["barcode"] and row["barcode"] not in product_cache and row["barcode"] not in seen_barcodes:
            seen_barcodes.add(row["barcode"])
            product_records.append({
                "barcode": row["barcode"],
                "name_he": row["name_he"],
                "name_fr": names_fr[i],
            })
    for i in range(0, len(product_records), BATCH):
        result = supa_post("products", product_records[i:i+BATCH], upsert_on="barcode")
        if result and isinstance(result, list):
            for p in result:
                if p.get("barcode"):
                    product_cache[p["barcode"]] = p["id"]

    # IDs manquants
    missing = [r["barcode"] for r in all_rows if r["barcode"] and r["barcode"] not in product_cache]
    for i in range(0, len(missing), 20):
        batch = missing[i:i+20]
        in_clause = ",".join([f'"{b}"' for b in batch])
        results = supa_get("products", f"barcode=in.({in_clause})&select=id,barcode")
        for p in (results or []):
            product_cache[p["barcode"]] = p["id"]

    # Insertion prix
    print(f"  💰 Prix...")
    price_records = []
    for i, row in enumerate(all_rows):
        product_id = product_cache.get(row["barcode"])
        if not product_id:
            continue
        try:
            price = float(str(row["price_raw"]).replace(",", "."))
        except:
            price = 0.0
        price_records.append({
            "product_id": product_id,
            "chain_id": chain_id,
            "store_id": f"{chain_id}_{row['store_id']}",
            "price": price,
            "price_updated_at": datetime.now().isoformat(),
        })
    for i in range(0, len(price_records), BATCH):
        supa_post("prices", price_records[i:i+BATCH])

    total_imported += len(price_records)
    print(f"  ✅ {len(price_records)} prix importés")

print(f"\n🎉 Import terminé: {total_imported} prix au total")