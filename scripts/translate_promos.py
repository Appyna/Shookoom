import os, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

PAGE_SIZE = 1000

def translate_promo(desc):
    if not openai_client or not desc:
        return desc
    prompt = (
        "Tu es un expert en promotions de supermarchés israéliens. "
        "Traduis cette description de promotion en français naturel et précis. "
        "Règles importantes:\n"
        "- Garde les noms de marques tels quels (Tnuva, Osem, Elite, Coca-Cola, etc)\n"
        "- Garde les chiffres, pourcentages et unités tels quels (3%, 250g, 1L, 10₪, etc)\n"
        "- Traduis précisément les types de promos:\n"
        "  * קופון = Coupon\n"
        "  * מועדון = Club membres\n"
        "  * 1+1 = 1 acheté 1 offert\n"
        "  * 2+1 = 2 achetés 1 offert\n"
        "  * הנחה = Réduction\n"
        "  * מתנה = Cadeau offert\n"
        "  * פיצוי = Compensation/remboursement\n"
        "- Réponds UNIQUEMENT avec la traduction, rien d'autre\n"
        f"Description: {desc}"
    )
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Erreur: {e}")
        return desc

def main():
    print("🎯 Traduction promos démarrée")

    translated = 0
    offset = 0
    page = 0

    while True:
        # Charger promos sans traduction française
        result = supabase.table("promos")\
            .select("id, promo_description_he, promo_description_fr")\
            .is_("promo_description_fr", "null")\
            .not_.is_("promo_description_he", "null")\
            .range(offset, offset + PAGE_SIZE - 1)\
            .execute()

        if not result.data:
            print("✅ Toutes les promos sont traduites!")
            break

        page += 1
        print(f"📄 Page {page} — {len(result.data)} promos à traduire")

        for p in result.data:
            desc_he = p.get("promo_description_he", "")
            if not desc_he:
                continue

            desc_fr = translate_promo(desc_he)

            if desc_fr and desc_fr != desc_he:
                try:
                    supabase.table("promos")\
                        .update({"promo_description_fr": desc_fr})\
                        .eq("id", p["id"])\
                        .execute()
                    translated += 1
                except Exception as e:
                    print(f"⚠️ Erreur update {p['id']}: {e}")

            time.sleep(0.2)

        print(f"✅ Total: {translated} promos traduites")
        offset += PAGE_SIZE

        if len(result.data) < PAGE_SIZE:
            print("✅ Dernière page!")
            break

    print(f"🎉 Terminé: {translated} promos traduites")

if __name__ == "__main__":
    main()
