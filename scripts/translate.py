"""
translate.py — Traduit les produits non traduits via OpenAI
Traduit UNIQUEMENT les produits où name_fr = name_he ou name_fr IS NULL
Ne retraduit jamais ce qui est déjà traduit
"""
import os, json, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BATCH_SIZE = 50
MAX_PRODUCTS = 5000

def translate_batch(names):
    if not openai_client:
        return names
    prompt = (
        "Tu es un expert en produits alimentaires et de pharmacie israeliens. "
        "Traduis ces noms de produits en francais naturel et bien formule. "
        "Garde les noms de marques tels quels (Tnuva, Osem, Elite, Strauss, Materna, etc). "
        "1 ligne par produit, meme ordre, sans numerotation:\n" + "\n".join(names)
    )
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        translations = r.choices[0].message.content.strip().split("\n")
        if len(translations) == len(names):
            return [t.strip() for t in translations]
        return names
    except Exception as e:
        print(f"⚠️ Erreur traduction: {e}")
        return names

def main():
    print("🌍 Traduction démarrée")

    result = supabase.table("products")\
        .select("id, barcode, name_he")\
        .not_.is_("name_he", "null")\
        .or_("name_fr.is.null,name_fr.eq.name_he")\
        .limit(MAX_PRODUCTS)\
        .execute()

    products = [p for p in result.data if p.get("name_he") and (not p.get("name_fr") or p.get("name_fr") == p.get("name_he"))]

    print(f"📦 {len(products)} produits à traduire")

    if not products:
        print("✅ Tout est déjà traduit !")
        return

    translated = 0
    for i in range(0, len(products), BATCH_SIZE):
        batch = products[i:i+BATCH_SIZE]
        names_he = [p["name_he"] for p in batch]
        names_fr = translate_batch(names_he)

        updates = []
        for p, name_fr in zip(batch, names_fr):
            if name_fr != p["name_he"]:
                updates.append({
                    "id": p["id"],
                    "barcode": p["barcode"],
                    "name_fr": name_fr
                })

        if updates:
            supabase.table("products")\
                .upsert(updates, on_conflict="barcode")\
                .execute()
            translated += len(updates)

        print(f"✅ [{i+len(batch)}/{len(products)}] {translated} traduits")
        time.sleep(0.5)

    print(f"🎉 Terminé: {translated} produits traduits")

if __name__ == "__main__":
    main()
