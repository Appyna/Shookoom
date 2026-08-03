import os, time
from supabase import create_client
from datetime import date

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

cutoff = date.today().isoformat()
print(f"Suppression de toutes les promos avec date_end < {cutoff}")

deleted = 0
batch = 0
errors = 0

while True:
    batch += 1
    try:
        result = supabase.table("promos")\
            .select("id")\
            .lt("date_end", cutoff)\
            .not_.is_("date_end", "null")\
            .limit(500)\
            .execute()
        
        ids = [r["id"] for r in result.data] if result.data else []
        
        if not ids:
            print("✅ Plus rien à supprimer!")
            break
        
        supabase.table("promos")\
            .delete()\
            .in_("id", ids)\
            .execute()
        
        deleted += len(ids)
        if batch % 10 == 0:
            print(f"Batch {batch}: total supprimé {deleted}")
        
        time.sleep(0.1)
        
    except Exception as e:
        errors += 1
        print(f"⚠️ Erreur batch {batch}: {e}")
        time.sleep(2)
        if errors > 10:
            print("Trop d'erreurs, arrêt")
            break

print(f"✅ Terminé: {deleted} promos supprimées, {errors} erreurs")
