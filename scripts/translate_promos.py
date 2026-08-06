import os, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BATCH_SIZE = 50

def translate_batch(names):
    if not openai_client or not names:
        return names
    prompt = (
        "Tu es un expert en promotions de supermarchés israéliens. "
        "Traduis ces descriptions de promotions en français naturel et précis. "
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
        "  * פיצוי = Compensation\n"
        "  * ב-X ש\"ח = à X ₪\n"
        "- 1 ligne par description, même ordre exact, sans numérotation\n"
        "Descriptions:\n" + "\n".join(names)
    )
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
        )
        translations = r.choices[0].message.content.strip().split("\n")
        translations = [t.strip() for t in translations if t.strip()]
        if len(translations) == len(names):
            return translations
        print(f"⚠️ Batch incomplet: {len(translations)} vs {len(names)}")
        return names
    except Exception as e:
        print(f"⚠️ Erreur: {e}")
        return names

def main():
    print("🎯 Traduction promos démarrée - mode optimisé")

    # Charger toutes les descriptions uniques non traduites
    result = supabase.table("promos")\
        .select("promo_description_he")\
        .is_("promo_description_fr", "null")\
        .not_.is_("promo_description_he", "null")\
        .execute()

    if not result.data:
        print("✅ Toutes les promos sont traduites!")
        return

    # Dédupliquer
    unique_descs = list(set(p["promo_description_he"] for p in result.data if p.get("promo_description_he")))
    print(f"📦 {len(unique_descs)} descriptions uniques à traduire")

    # Traduire par batch de 50
    cache = {}
    translated = 0

    for i in range(0, len(unique_descs), BATCH_SIZE):
        batch = unique_descs[i:i+BATCH_SIZE]
        translations = translate_batch(batch)
        for desc_he, desc_fr in zip(batch, translations):
            if desc_fr and desc_fr != desc_he:
                cache[desc_he] = desc_fr
        translated += len(batch)
        if (i // BATCH_SIZE) % 10 == 0:
            print(f"✅ [{translated}/{len(unique_descs)}] descriptions traduites")
        time.sleep(0.3)

    print(f"📝 Cache: {len(cache)} traductions — mise à jour Supabase...")

    # Mettre à jour toutes les promos avec la traduction
    updated = 0
    for desc_he, desc_fr in cache.items():
        try:
            supabase.table("promos")\
                .update({"promo_description_fr": desc_fr})\
                .eq("promo_description_he", desc_he)\
                .is_("promo_description_fr", "null")\
                .execute()
            updated += 1
        except Exception as e:
            print(f"⚠️ Erreur update: {e}")
        time.sleep(0.05)

    print(f"🎉 Terminé: {updated} descriptions uniques traduites → appliquées à toutes les promos")

if __name__ == "__main__":
    main()
