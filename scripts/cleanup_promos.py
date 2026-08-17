import os, time
from supabase import create_client
from datetime import date

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def main():
    print("🧹 Nettoyage promos expirées démarré")
    
    # Étape 1: Supprimer promos expirées
    cutoff = date.today().isoformat()
    deleted = 0
    batch = 0
    
    while True:
        batch += 1
        result = supabase.table("promos")\
            .select("id")\
            .lt("date_end", cutoff)\
            .not_.is_("date_end", "null")\
            .limit(2000)\
            .execute()
        
        ids = [r["id"] for r in result.data] if result.data else []
        
        if not ids:
            print(f"✅ Plus rien à supprimer!")
            break
        
        supabase.table("promos").delete().in_("id", ids).execute()
        deleted += len(ids)
        
        if batch % 10 == 0:
            print(f"Batch {batch}: {deleted} promos expirées supprimées")
        
        time.sleep(0.1)
    
    print(f"✅ Expirées: {deleted} supprimées")

    # Étape 2: Insérer nouvelles descriptions dans promo_translations
    print("📝 Synchronisation promo_translations...")
    try:
        result = supabase.rpc('sync_promo_translations').execute()
        print(f"✅ {result.data} nouvelles descriptions ajoutées")
    except Exception as e:
        print(f"⚠️ Erreur sync: {e}")

    print(f"🎉 Terminé")

if __name__ == "__main__":
    main()
