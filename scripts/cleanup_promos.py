import os, time
from supabase import create_client
from datetime import date

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def dedupe_chain(chain_id):
    print(f"  Déduplication {chain_id}...")
    deleted = 0
    seen = {}
    offset = 0
    
    while True:
        result = supabase.table("promos")\
            .select("id, barcode, store_id, date_start")\
            .eq("chain_id", chain_id)\
            .range(offset, offset + 2000)\
            .execute()
        
        if not result.data:
            break
        
        to_delete = []
        for row in result.data:
            key = (row["barcode"], row["store_id"], row.get("date_start"))
            if key in seen:
                to_delete.append(row["id"])
            else:
                seen[key] = row["id"]
        
        if to_delete:
            supabase.table("promos").delete().in_("id", to_delete).execute()
            deleted += len(to_delete)
        
        offset += 2000
        time.sleep(0.2)
    
    print(f"  ✅ {chain_id}: {deleted} doublons supprimés")
    return deleted

def main():
    print("🧹 Nettoyage démarré")
    
    # Étape 1: Supprimer promos expirées
    cutoff = date.today().isoformat()
    deleted_expired = 0
    while True:
        result = supabase.table("promos")\
            .select("id")\
            .lt("date_end", cutoff)\
            .not_.is_("date_end", "null")\
            .limit(2000)\
            .execute()
        ids = [r["id"] for r in result.data] if result.data else []
        if not ids:
            break
        supabase.table("promos").delete().in_("id", ids).execute()
        deleted_expired += len(ids)
    print(f"✅ Expirées: {deleted_expired} supprimées")

    # Étape 2: Dédupliquer chaîne par chaîne
    chains = supabase.table("promos")\
        .select("chain_id")\
        .execute()
    
    chain_ids = list(set(r["chain_id"] for r in chains.data)) if chains.data else []
    print(f"📦 {len(chain_ids)} chaînes à dédupliquer")
    
    total_deleted = 0
    for chain_id in chain_ids:
        total_deleted += dedupe_chain(chain_id)
    
    print(f"🎉 Terminé: {total_deleted} doublons supprimés au total")

if __name__ == "__main__":
    main()
