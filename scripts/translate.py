import os, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BATCH_SIZE = 1
PAGE_SIZE = 1000

def translate_one(name):
    if not openai_client:
        return name
    prompt = (
        "Tu es un expert en produits alimentaires et de pharmacie israeliens. "
        "Traduis ce nom de produit en francais naturel et bien formule. "
        "Regles importantes:\n"
        "- Garde les noms de marques tels quels (Tnuva, Osem, Elite, Strauss, Materna, Telma, Pampers, Lays, Snickers, etc)\n"
        "- Garde les chiffres, pourcentages et unites tels quels (3%, 250g, 1L, etc)\n"
        "- Si le nom est deja en francais ou anglais, garde-le tel quel\n"
        "- Si le nom est un chiffre ou caractere unique, garde-le tel quel\n"
        "- Reponds UNIQUEMENT avec la traduction, rien d'autre\n"
        f"Nom a traduire: {name}"
    )
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        translation = r.choices[0].message.content.strip()
        return translation if translation else name
    except Exception as e:
        print(f"⚠️ Erreur traduction: {e}")
        return name

def main():
    print("🌍 Traduction démarrée - mode 1 par 1")

    translated = 0
    errors = 0
    offset = 0
    page = 0

    while True:
        result = supabase.table("products")\
            .select("id, barcode, name_he, name_fr")\
            .range(offset, offset + PAGE_SIZE - 1)\
            .execute()

        if not result.data:
            print("✅ Plus de produits - terminé!")
            break

        page_products = [
            p for p in result.data
            if p.get("name_he")
            and p.get("name_he").strip()
            and (not p.get("name_fr") or p.get("name_fr") == p.get("name_he"))
        ]

        page += 1
        print(f"📄 Page {page} (offset {offset}) — {len(page_products)}/{len(result.data)} à traduire")

        for p in page_products:
            name_fr = translate_one(p["name_he"])
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
            time.sleep(0.2)

        print(f"✅ Total: {translated} traduits, {errors} erreurs")
        offset += PAGE_SIZE

        if len(result.data) < PAGE_SIZE:
            print("✅ Dernière page!")
            break

    print(f"🎉 Terminé: {translated} produits traduits, {errors} erreurs")

if __name__ == "__main__":
    main()
