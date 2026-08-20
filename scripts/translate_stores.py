import os, time
from supabase import create_client
from anthropic import Anthropic

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = Anthropic(api_key=ANTHROPIC_API_KEY)

def translate_names(stores):
    if not stores:
        return []
    
    lines = []
    for s in stores:
        lines.append(f"ID:{s['id']}|{s.get('store_name_he') or ''}")
    
    prompt = (
        "Tu es un expert en translittération hébreu-français.\n"
        "Pour chaque magasin israélien, translittère et traduis le nom hébreu en français.\n\n"
        "RÈGLES:\n"
        "- Translittère les mots hébreux en caractères latins\n"
        "- Garde les mots déjà en latin tels quels (AM-PM, BE, ONLINE, etc.)\n"
        "- Traduis les mots communs: דיל=Deal, אקספרס=Express, שלי=Sheli, יש=Yesh, חסד=Hesed, מרקט=Market, סיטי=City, היפר=Hyper, סופר=Super, מגה=Mega, קניון=Canyon, מרכז=Centre\n"
        "- Garde les noms de villes en français si possible\n"
        "- Retourne: ID|nom_translittéré\n"
        "- 1 ligne par magasin, même ordre\n"
        "- JAMAIS de texte hébreu dans la réponse\n"
        "- JAMAIS d'apostrophe\n\n"
        "Exemples:\n"
        "ID:100|שלי חיפה- כרמל → ID:100|Sheli Haïfa - Carmel\n"
        "ID:101|דיל אשדוד- שבט לוי → ID:101|Deal Ashdod - Shevet Levi\n"
        "ID:102|יש חסד עפולה עילית → ID:102|Yesh Hesed Afula Ilit\n"
        "ID:103|AM-PM אלנבי → ID:103|AM-PM Allenby\n"
        "ID:104|קרפור מרקט נתניה → ID:104|Carrefour Market Netanya\n\n"
        "Magasins:\n" + "\n".join(lines)
    )
    
    try:
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text.strip().split("\n")
    except Exception as e:
        print(f"⚠️ Erreur Claude: {e}")
        return []

def main():
    print("🏪 Traduction noms magasins démarrée")
    
    total_updated = 0
    
    while True:
        stores = []
        offset = 0
        while True:
            result = supabase.table("stores")\
                .select("id, store_name_he, store_name_fr")\
                .is_("store_name_fr", "null")\
                .not_.is_("store_name_he", "null")\
                .range(offset, offset + 999)\
                .execute()
            if not result.data:
                break
            stores.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000
        
        if not stores:
            print("✅ Tous les noms sont traduits!")
            break
        
        print(f"📦 {len(stores)} magasins à traduire...")
        
        BATCH = 30
        for i in range(0, len(stores), BATCH):
            batch = stores[i:i+BATCH]
            translations = translate_names(batch)
            
            for line in translations:
                try:
                    parts = line.split("|")
                    if len(parts) < 2:
                        continue
                    store_id = int(parts[0].replace("ID:", "").strip())
                    nom_fr = parts[1].strip().replace("'", "").replace("`", "")
                    
                    if nom_fr:
                        supabase.table("stores")\
                            .update({"store_name_fr": nom_fr})\
                            .eq("id", store_id)\
                            .execute()
                        total_updated += 1
                except Exception as e:
                    print(f"⚠️ Erreur: {e}")
            
            print(f"✅ {total_updated} noms traduits")
            time.sleep(0.5)
    
    print(f"🎉 Terminé: {total_updated} noms traduits")

if __name__ == "__main__":
    main()
