"""
import_kaggle.py — Shookoom
Debug structure JSON Kaggle
"""
import os, re, json, time, subprocess, sys
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
print(f"✅  Téléchargé")

# ── 2. Lister fichiers ────────────────────────────────────────────────────────
all_files = []
for root, dirs, files in os.walk(DATA_DIR):
    for f in files:
        all_files.append(os.path.join(root, f))

print(f"📂  {len(all_files)} fichiers au total")
print(f"Exemples: {[os.path.basename(f) for f in all_files[:5]]}")

json_files = [f for f in all_files if f.endswith(".json") and "price_full_file" in f]
print(f"📂  {len(json_files)} fichiers price_full_file")

# ── 3. Debug structure des 3 premiers fichiers ────────────────────────────────
for filepath in json_files[:3]:
    print(f"\n📄  Fichier: {os.path.basename(filepath)}")
    try:
        with open(filepath, encoding="utf-8") as f:
            raw = json.load(f)
        print(f"  Type racine: {type(raw).__name__}")
        if isinstance(raw, dict):
            print(f"  Keys: {list(raw.keys())[:8]}")
            for k, v in list(raw.items())[:4]:
                if isinstance(v, list):
                    print(f"    '{k}': liste de {len(v)} items")
                    if v and isinstance(v[0], dict):
                        print(f"      Premier item keys: {list(v[0].keys())[:8]}")
                        print(f"      Premier item: {json.dumps(v[0], ensure_ascii=False)[:300]}")
                elif isinstance(v, dict):
                    print(f"    '{k}': dict avec keys {list(v.keys())[:5]}")
                else:
                    print(f"    '{k}': {type(v).__name__} = {str(v)[:100]}")
        elif isinstance(raw, list):
            print(f"  Liste de {len(raw)} items")
            if raw and isinstance(raw[0], dict):
                print(f"  Premier item keys: {list(raw[0].keys())[:8]}")
                print(f"  Premier item: {json.dumps(raw[0], ensure_ascii=False)[:400]}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")

print("\n🔍  Debug terminé — analyse de la structure ci-dessus")