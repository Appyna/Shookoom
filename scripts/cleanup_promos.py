import os, time
from supabase import create_client
from datetime import date

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def main():
    print("🧹 Nettoyage promos expirées démarré")
    
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
    
    print(f"🎉 Terminé: {deleted} promos expirées supprimées")

if __name__ == "__main__":
    main()
