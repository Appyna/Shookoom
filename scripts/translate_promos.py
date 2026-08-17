import os, time
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BATCH_SIZE = 50

def is_valid_translation(original, translated):
    """Vérifie que la traduction est valide"""
    if not translated or not translated.strip():
        return False
    if translated.strip() == original.strip():
        return False
    if len(translated) < 2:
        return False
    return True

def translate_one(name):
    """Traduit une seule description — utilisé en fallback"""
    if not openai_client:
        return name
    prompt = (
        "Tu es un expert en promotions de supermarchés israéliens. "
        "Traduis cette description de promotion en français naturel et précis. "
        "Règles: garde les marques, chiffres et unités. Réponds UNIQUEMENT avec la traduction.\n"
        f"Description: {name}"
    )
    try:
        r = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        result = r.choices[0].message.content.strip()
        return result if is_valid_translation(name, result) else name
    except:
        return name

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
            # Protection A: vérifier chaque traduction
            result = []
            for orig, trans in zip(names, translations):
                if is_valid_translation(orig, trans):
                    result.append(trans)
                else:
                    # Retenter 1 par 1
                    result.append(translate_one(orig))
            return result
        else:
            # Protection C: batch incomplet → retenter 1 par 1
            print(f"⚠️ Batch incomplet: {len(translations)} vs {len(names)} — retente 1 par 1")
            return [translate_one(n) for n in names]
            
    except Exception as e:
        print(f"⚠️ Erreur batch: {e}")
        return names

def main():
    print("🎯 Traduction promos démarrée")
    total_translated = 0

    while True:
        # Récupérer 1000 descriptions non traduites depuis la petite table
        result = supabase.table("promo_translations")\
            .select("description_he")\
            .is_("description_fr", "null")\
            .limit(1000)\
            .execute()

        if not result.data:
            print("✅ Toutes les promos sont traduites!")
            break

        unique_descs = [r["description_he"] for r in result.data if r.get("description_he")]
        print(f"📦 {len(unique_descs)} descriptions à traduire ce run")

        if not unique_descs:
            break

        # Traduire par batch de 50
        cache = {}
        for i in range(0, len(unique_descs), BATCH_SIZE):
            batch = unique_descs[i:i+BATCH_SIZE]
            translations = translate_batch(batch)
            for desc_he, desc_fr in zip(batch, translations):
                if is_valid_translation(desc_he, desc_fr):
                    cache[desc_he] = desc_fr
            if (i // BATCH_SIZE) % 10 == 0:
                print(f"✅ [{i+len(batch)}/{len(unique_descs)}] traduits")
            time.sleep(0.3)

        print(f"📝 {len(cache)} traductions valides — mise à jour...")

        # Mettre à jour promo_translations
        for he, fr in cache.items():
            try:
                supabase.table("promo_translations")\
                    .update({"description_fr": fr})\
                    .eq("description_he", he)\
                    .execute()
            except Exception as e:
                print(f"⚠️ Erreur update translation: {e}")

        # Appliquer vers promos via fonction SQL
        translations_json = [{"he": he, "fr": fr} for he, fr in cache.items()]
        try:
            supabase.rpc('apply_promo_translations', 
                {'translations': translations_json}).execute()
            print(f"✅ {len(cache)} traductions appliquées aux promos")
        except Exception as e:
            print(f"⚠️ Erreur apply: {e}")

        total_translated += len(cache)
        print(f"✅ Total: {total_translated} descriptions traduites")

        if len(unique_descs) < 1000:
            print("✅ Toutes les descriptions traduites!")
            break

    print(f"🎉 Terminé: {total_translated} descriptions traduites au total")

if __name__ == "__main__":
    main()
