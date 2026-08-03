import os
from supabase import create_client
from datetime import date

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

cutoff = date.today().isoformat()
print(f"Suppression de toutes les promos avec date_end < {cutoff}")

deleted = 0
batch = 0
while True:
    batch += 1
    result = supabase.table("promos")\
        .select("id")\
        .lt("date_end", cutoff)\
        .not_.is_("date_end", "null")\
        .limit(5000)\
        .execute()
    
    ids = [r["id"] for r in result.data] if result.data else []
    
    if not ids:
        break
    
    supabase.table("promos")\
        .delete()\
        .in_("id", ids)\
        .execute()
    
    deleted += len(ids)
    print(f"Batch {batch}: supprimé {len(ids)} promos (total: {deleted})")

print(f"✅ Terminé: {deleted} promos expirées supprimées")
