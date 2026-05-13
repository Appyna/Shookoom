"""
import_kaggle.py — Shookoom
Import CSV Kaggle → Supabase avec traduction OpenAI
"""
import os, re, json, time, subprocess, sys, csv
from datetime import datetime

print("🚀  Import Shookoom démarré")
print(f"🕐  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATA_DIR = "./kaggle_data"

# ── 1. Téléchargement ─────────────────────────────────────────────────────────
print("📥  Téléchargement des données Kaggle...")
os.makedirs(DATA_DIR, exist_ok=True)
result = subprocess.run(
    ["kaggle", "datasets", "download",
     "-d", "erlichsefi/israeli-supermarkets-2024",
     "--unzip", "-p", DATA_DIR],
    capture_output=True, text=True
)
print(f"CODE: {result.returncode}")
if result.returncode != 0:
    print(f"STDERR: {result.stderr}")
    sys.exit(1)
print("✅  Téléchargé")

# ── 2. Trouver les fichiers CSV de prix ───────────────────────────────────────
all_files = []
for root, dirs, files in os.walk(DATA_DIR):
    for f in files:
        all_files.append(os.path.join(root, f))

csv_files = [f for f in all_files if f.endswith(".csv") and "price_full_file" in f]
if not csv_files:
    csv_files = [f for f in all_files if f.endswith(".csv") and "price" in f]

print(f"📂  {len(csv_files)} fichiers CSV de prix trouvés")

# ── 3. Traduction OpenAI ──────────────────────────────────────────────────────
import urllib.request

def translate_batch(texts):
    if not OPENAI_API_KEY:
        return texts
    prompt = "Traduis ces noms de produits hébreux en français. Réponds UNIQUEMENT avec un JSON array des traductions dans le même ordre:\n" + json.dumps(texts, ensure_ascii=False)
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
        print(f"  ⚠️  Traduction échouée: {e}")
        return texts

# ── 4. Envoyer dans Supabase ──────────────────────────────────────────────────
def supabase_upsert(records):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("⚠️  Variables Supabase manquantes")
        return
    data = json.dumps(records).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/products",
        data=data,
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except Exception as e:
        print(f"  ⚠️  Erreur Supabase: {e}")

# ── 5. Traitement des fichiers CSV ────────────────────────────────────────────
total_imported = 0
BATCH = 50

for filepath in csv_files[:10]:
    chain = os.path.basename(filepath)
    for suffix in ["_price_full_file.csv", "_price_file.csv", ".csv"]:
        chain = chain.replace(suffix, "")
    chain = chain.replace("price_full_file_", "").replace("price_file_", "")

    print(f"\n🏪  Traitement: {chain}")
    records = []
    names_he = []

    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 2000:
                    break
                name_he = (
                    row.get("itemname") or
                    row.get("ItemName") or
                    row.get("item_name") or
                    row.get("name") or ""
                ).strip()
                if not name_he:
                    continue
                barcode = str(
                    row.get("itemcode") or
                    row.get("ItemCode") or
                    row.get("item_code") or
                    row.get("barcode") or ""
                )
                price_raw = (
                    row.get("itemprice") or
                    row.get("ItemPrice") or
                    row.get("item_price") or
                    row.get("price") or "0"
                )
                try:
                    price = float(str(price_raw).replace(",", "."))
                except:
                    price = 0
                records.append({
                    "barcode": barcode,
                    "name_he": name_he,
                    "name_fr": "",
                    "price": price,
                    "chain": chain,
                    "updated_at": datetime.now().isoformat()
                })
                names_he.append(name_he)
    except Exception as e:
        print(f"  ⚠️  Erreur lecture: {e}")
        continue

    print(f"  📦  {len(records)} produits trouvés")
    if not records:
        continue

    print(f"  🌐  Traduction de {len(records)} produits...")
    for i in range(0, len(records), BATCH):
        batch_names = names_he[i:i+BATCH]
        translated = translate_batch(batch_names)
        for j, rec in enumerate(records[i:i+BATCH]):
            rec["name_fr"] = translated[j] if j < len(translated) else rec["name_he"]
        time.sleep(0.5)

    print(f"  💾  Envoi dans Supabase...")
    for i in range(0, len(records), BATCH):
        supabase_upsert(records[i:i+BATCH])

    total_imported += len(records)
    print(f"  ✅  {len(records)} produits importés")

print(f"\n🎉  Import terminé: {total_imported} produits au total")