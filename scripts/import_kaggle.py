"""
import_kaggle.py — Shookoom
Import Kaggle → Supabase avec traduction OpenAI
"""
import os, re, json, time, subprocess, sys
from datetime import datetime

print("🚀  Import Shookoom démarré")
print(f"🕐  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATA_DIR = "./kaggle_data"

# ── 1. Téléchargement via kaggle CLI ──────────────────────────────────────────
print("📥  Téléchargement des données Kaggle...")
os.makedirs(DATA_DIR, exist_ok=True)

result = subprocess.run(
    ["kaggle", "datasets", "download",
     "-d", "erlichsefi/israeli-supermarkets-2024",
     "--unzip", "-p", DATA_DIR],
    capture_output=True, text=True
)

print(f"STDOUT: {result.stdout}")
print(f"STDERR: {result.stderr}")
print(f"CODE: {result.returncode}")

if result.returncode != 0:
    print("❌  Échec téléchargement Kaggle")
    sys.exit(1)

print(f"✅  Données téléchargées dans {DATA_DIR}")

# ── 2. Lister les fichiers JSON de prix ───────────────────────────────────────
json_files = []
for root, dirs, files in os.walk(DATA_DIR):
    for f in files:
        if f.endswith(".json") and "price_full_file" in f:
            json_files.append(os.path.join(root, f))

if not json_files:
    for root, dirs, files in os.walk(DATA_DIR):
        for f in files:
            if f.endswith(".json") and "price" in f:
                json_files.append(os.path.join(root, f))

print(f"📂  {len(json_files)} fichiers de prix trouvés")

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

# ── 5. Traitement des fichiers ────────────────────────────────────────────────
total_imported = 0
BATCH = 50

for filepath in json_files[:10]:
    chain = os.path.basename(filepath).replace("price_full_file_","").replace("price_file_","").replace(".json","")
    print(f"\n🏪  Traitement: {chain}")
    try:
        with open(filepath, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"  ⚠️  Erreur lecture: {e}")
        continue

    items = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        for key in ["Products", "products", "items", "Prices", "root"]:
            if key in raw:
                val = raw[key]
                if isinstance(val, list):
                    items = val
                    break
        if not items:
            for v in raw.values():
                if isinstance(v, list) and len(v) > 0:
                    items = v
                    break

    print(f"  📦  {len(items)} entrées trouvées")
    items = items[:2000]

    records = []
    names_he = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name_he = (item.get("ItemName") or item.get("name") or item.get("Name") or "").strip()
        if not name_he:
            continue
        barcode = str(item.get("ItemCode") or item.get("barcode") or item.get("Barcode") or "")
        price = item.get("ItemPrice") or item.get("price") or item.get("Price") or 0
        try:
            price = float(str(price).replace(",","."))
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

    if not records:
        print(f"  ⚠️  Aucun produit extrait")
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