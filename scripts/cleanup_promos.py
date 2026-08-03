import os
from supabase import create_client
from datetime import date, timedelta

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

cutoff_date = date.today().isoformat()
cutoff_scraped = (date.today() - timedelta(days=7)).isoformat()

print(f"Suppression promos avec date_end < {cutoff_date} ET scraped_at < {cutoff_scraped}")

deleted = 0
batch = 0
while True:
    batch += 1
    result = supabase.table("promos")\
        .delete()\
        .lt("date_end", cutoff_date)\
        .lt("scraped_at", cutoff_scraped)\
        .not_.is_("date_end", "null")\
        .limit(500)\
        .execute()
    
    count = len(result.data) if result.data else 0
    deleted += count
    print(f"Batch {batch}: supprimé {count} promos (total: {deleted})")
    
    if count < 500:
        break

print(f"✅ Terminé: {deleted} promos expirées supprimées")
