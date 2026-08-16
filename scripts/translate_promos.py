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
        "  * X יח' = X unités\n"
        "  * קניית X = achat de X\n"
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
    print("🎯 Traduction promos démarrée")
    total_translated = 0

    while True:
        result = supabase.rpc('get_untranslated_promo_descs').execute()

        if not result.data:
            print("✅ Toutes les promos sont traduites!")
            break

        unique_descs = [r["description_he"] for r in result.data if r.get("description_he")]
        print(f"📦 {len(unique_descs)} descriptions à traduire ce run")

        if not unique_descs:
            break

        cache = {}
        for i in range(0, len(unique_descs), BATCH_SIZE):
            batch = unique_descs[i:i+BATCH_SIZE]
            translations = translate_batch(batch)
            for desc_he, desc_fr in zip(batch, translations):
                if desc_fr and desc_fr != desc_he:
                    cache[desc_he] = desc_fr
            if (i // BATCH_SIZE) % 20 == 0:
                print(f"✅ [{i+len(batch)}/{len(unique_descs)}] traduits")
            time.sleep(0.3)

        print(f"📝 {len(cache)} traductions — mise à jour Supabase via fonction SQL...")

        # Préparer les traductions en JSON
        translations_json = [{"he": he, "fr": fr} for he, fr in cache.items()]
        
        # Appliquer en une seule requête SQL
        try:
            result = supabase.rpc('apply_promo_translations', 
                {'translations': translations_json}).execute()
            updated = result.data if result.data else 0
            print(f"✅ {updated} descriptions mises à jour")
        except Exception as e:
            print(f"⚠️ Erreur: {e}")
            updated = 0

        total_translated += updated
        print(f"✅ {updated} descriptions mises à jour (total: {total_translated})")

        if len(unique_descs) < 10000:
            print("✅ Toutes les descriptions traduites!")
            break

    print(f"🎉 Terminé: {total_translated} descriptions traduites au total")

if __name__ == "__main__":
    main()
