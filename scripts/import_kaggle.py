"""
import_kaggle.py — Shookoom
Import CSV Kaggle → Supabase (products + prices + chains)
"""
import os, re, json, time, subprocess, sys, csv
from datetime import datetime
import urllib.request, urllib.error

print("🚀  Import Shookoom démarré")
print(f"🕐  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATA_DIR = "./kaggle_data"

def supa_post(table, records, upsert_on=None):
    if not records:
        return
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if upsert_on:
        headers["Prefer"] = f"resolution=merge-duplicates,return=representation"
    else:
        headers["Prefer"] = "return=representation"
    data = json.dumps(records, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}",
        data=data, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  ⚠️  Supabase {table} {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"  ⚠️  Supabase {table}: {e}")

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
        print(f"  ⚠️  Supabase GET {table}: {e}")
        return []

# ── 1. Téléchargement ─────────────────────────────────────────────────────────
print("📥  Téléchargement des données Kaggle...")
os.makedirs(DATA_DIR, exist_ok=True)
result = subprocess.run(
    ["kaggle", "datasets", "download",
     "-d", "erlichsefi/israeli-supermarkets-2024",
     "--unzip", "-p", DATA_DIR],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(f"❌  {result.stderr}")
    sys.exit(1)
print("✅  Téléchargé")

# ── 2. Fichiers CSV ───────────────────────────────────────────────────────────
all_files = []
for root, dirs, files in os.walk(DATA_DIR):
    for f in files:
        all_files.append(os.path.join(root, f))

csv_files = [f for f in all_files if f.endswith(".csv") and "price_full_file" in f]
print(f"📂  {len(csv_files)} fichiers CSV trouvés")

# ── 3. Traduction OpenAI ──────────────────────────────────────────────────────
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
        print(f"  ⚠️  Traduction: {e}")
        return texts

# ── 4. Traitement ─────────────────────────────────────────────────────────────
total_imported = 0
BATCH = 50

# Cache produits déjà insérés (barcode → product_id)
product_cache = {}

for filepath in csv_files[:10]:
    chain_name = os.path.basename(filepath)
    for suffix in ["_price_full_file.csv", "_price_file.csv", ".csv"]:
        chain_name = chain_name.replace(suffix, "")

    print(f"\n🏪  Traitement: {chain_name}")

    # Lire le CSV
    rows = []
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 2000:
                    break
                name_he = re.sub(r'[\x00-\x1f\x7f]', ' ',
                    (row.get("itemname") or row.get("ItemName") or "").strip())
                if not name_he:
                    continue
                rows.append({
                    "barcode": str(row.get("itemcode") or row.get("ItemCode") or ""),
                    "name_he": name_he,
                    "chain_id": str(row.get("chainid") or row.get("chainId") or chain_name),
                    "store_id": str(row.get("storeid") or row.get("storeId") or ""),
                    "price_raw": row.get("itemprice") or row.get("ItemPrice") or "0",
                })
    except Exception as e:
        print(f"  ⚠️  Lecture: {e}")
        continue

    print(f"  📦  {len(rows)} lignes")
    if not rows:
        continue

    # Insérer la chaîne
    chain_id = rows[0]["chain_id"] if rows else chain_name
    supa_post("chains", [{
        "id": chain_id,
        "name_fr": chain_name.replace("_", " ").title(),
        "name_he": chain_name
    }], upsert_on="id")

    # Traduire les noms
    print(f"  🌐  Traduction...")
    names_he = [r["name_he"] for r in rows]
    names_fr = list(names_he)
    for i in range(0, len(rows), BATCH):
        batch = names_he[i:i+BATCH]
        translated = translate_batch(batch)
        for j in range(len(batch)):
            names_fr[i+j] = translated[j] if j < len(translated) else batch[j]
        time.sleep(0.3)

    # Insérer les produits par batch et récupérer les IDs
    print(f"  💾  Insertion produits...")
    product_records = []
    for i, row in enumerate(rows):
        if row["barcode"] not in product_cache:
            product_records.append({
                "barcode": row["barcode"],
                "name_he": row["name_he"],
                "name_fr": names_fr[i],
            })

    # Upsert produits par batch
    for i in range(0, len(product_records), BATCH):
        batch = product_records[i:i+BATCH]
        result = supa_post("products", batch, upsert_on="barcode")
        if result and isinstance(result, list):
            for p in result:
                if p.get("barcode"):
                    product_cache[p["barcode"]] = p["id"]

    # Récupérer les IDs manquants
    missing = [r["barcode"] for r in rows if r["barcode"] not in product_cache and r["barcode"]]
    if missing:
        for i in range(0, len(missing), 20):
            batch_barcodes = missing[i:i+20]
            in_clause = ",".join([f'"{b}"' for b in batch_barcodes])
            results = supa_get("products", f"barcode=in.({in_clause})&select=id,barcode")
            if results:
                for p in results:
                    product_cache[p["barcode"]] = p["id"]

    # Insérer les prix
    print(f"  💰  Insertion prix...")
    price_records = []
    for i, row in enumerate(rows):
        product_id = product_cache.get(row["barcode"])
        if not product_id:
            continue
        try:
            price = float(str(row["price_raw"]).replace(",", "."))
        except:
            price = 0
        price_records.append({
            "product_id": product_id,
            "chain_id": chain_id,
            "store_id": row["store_id"],
            "price": price,
            "price_updated_at": datetime.now().isoformat(),
            "imported_at": datetime.now().isoformat(),
        })

    for i in range(0, len(price_records), BATCH):
        supa_post("prices", price_records[i:i+BATCH])

    total_imported += len(price_records)
    print(f"  ✅  {len(price_records)} prix importés")

print(f"\n🎉  Import terminé: {total_imported} entrées au total")