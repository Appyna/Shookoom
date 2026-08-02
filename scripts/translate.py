import os, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BATCH_SIZE = 50
PAGE_SIZE = 1000

def translate_batch(names):
    if not openai_client:
        return names
    prompt = (
        "Tu es un expert en produits alimentaires et de pharmacie israeliens. "
        "Traduis ces noms de produits hebreux en francais naturel et bien formule. "
        "Regles importantes:\n"
        "- Garde les noms de marques tels quels (Tnuva, Osem, Elite, Strauss, Materna, Telma, Willi Food, etc)\n"
        "- Garde les chiffres, pourcentages et unites tels quels (3%, 250g, 1L, etc)\n"
        "- Si le nom est deja en francais ou anglais, garde-le tel quel\n"
        "- Si le nom est un chiffre ou caractere unique, garde-le tel quel\n"
        "- 1 ligne par produit, meme ordre exact, sans numerotation ni tiret\n"
        "Noms a traduire:\n" + "\n".join(names)
    )
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        translations = r.choices[0].message.content.strip().split("\n")
        translations = [t.strip().lstrip("- ").lstrip("0123456789. ") for t in translations if t.strip()]
        if len(translations) == len(names):
            return translations
        print(f"⚠️ Batch incomplet: {len(translations)} vs {len(names)} - on garde l'hébreu")
        return names
    except Exception as e:
        print(f"⚠️ Erreur traduction: {e}")
        return names

def fetch_all_untranslated():
    all_products = []
    offset = 0
    while True:
        result = supabase.table("products")\
            .select("id, barcode, name_he, name_fr")\
            .range(offset, offset + PAGE_SIZE - 1)\
            .execute()
        batch = result.data
        if not batch:
            break
        filtered = [
            p for p in batch
            if p.get("name_he")
            and p.get("name_he").strip()
            and (not p.get("name_fr") or p.get("name_fr") == p.get("name_he"))
        ]
        all_products.extend(filtered)
        print(f"  Chargé {offset + len(batch)} produits, {len(all_products)} à traduire...")
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_products

def main():
    print("🌍 Traduction démarrée - chargement de tous les produits...")

    products = fetch_all_untranslated()
    print(f"📦 {len(products)} produits à traduire au total")

    if not products:
        print("✅ Tout est déjà traduit !")
        return

    translated = 0
    errors = 0
    for i in range(0, len(products), BATCH_SIZE):
        batch = products[i:i+BATCH_SIZE]
        names_he = [p["name_he"] for p in batch]
        names_fr = translate_batch(names_he)

        for p, name_fr in zip(batch, names_fr):
            if name_fr and name_fr.strip() and name_fr != p["name_he"]:
                try:
                    supabase.table("products")\
                        .update({"name_fr": name_fr.strip()})\
                        .eq("id", p["id"])\
                        .execute()
                    translated += 1
                except Exception as e:
                    errors += 1
                    print(f"⚠️ Erreur update {p['barcode']}: {e}")

        if (i // BATCH_SIZE) % 10 == 0:
            print(f"✅ [{i+len(batch)}/{len(products)}] {translated} traduits, {errors} erreurs")
        time.sleep(0.5)

    print(f"🎉 Terminé: {translated} produits traduits, {errors} erreurs")

if __name__ == "__main__":
    main()
