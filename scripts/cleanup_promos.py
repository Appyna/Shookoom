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
        .delete()\
        .lt("date_end", cutoff)\
        .not_.is_("date_end", "null")\
        .limit(500)\
        .execute()
    
    count = len(result.data) if result.data else 0
    deleted += count
    print(f"Batch {batch}: supprimé {count} promos (total: {deleted})")
    
    if count < 500:
        break

print(f"✅ Terminé: {deleted} promos expirées supprimées")
