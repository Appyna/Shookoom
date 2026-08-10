import os, time
from supabase import create_client
from datetime import date

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

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
        print(f"Expirées supprimées: {deleted_expired}")

    print(f"✅ Expirées: {deleted_expired} supprimées")

    # Étape 2: Supprimer doublons - garder MIN(id) par groupe
    deleted_dupes = 0
    offset = 0
    while True:
        # Trouver les IDs à garder
        result = supabase.table("promos")\
            .select("id, barcode, chain_id, store_id, date_start")\
            .range(offset, offset + 5000)\
            .execute()
        
        if not result.data:
            break

        seen = {}
        to_delete = []
        for row in result.data:
            key = (row["barcode"], row["chain_id"], row["store_id"], row.get("date_start"))
            if key in seen:
                to_delete.append(row["id"])
            else:
                seen[key] = row["id"]

        if to_delete:
            supabase.table("promos").delete().in_("id", to_delete).execute()
            deleted_dupes += len(to_delete)
            print(f"Doublons supprimés: {deleted_dupes}")

        offset += 5000
        time.sleep(0.1)

    print(f"✅ Doublons: {deleted_dupes} supprimés")
    print(f"🎉 Terminé")

if __name__ == "__main__":
    main()
