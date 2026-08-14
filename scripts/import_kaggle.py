import os, asyncio, logging, xml.etree.ElementTree as ET, importlib, re, json, shutil
from datetime import date, datetime
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

load_dotenv()
# Chaînes à scraper (depuis variable d'environnement ou toutes par défaut)
CHAINS_FILTER = os.getenv("CHAINS_TO_SCRAPE", "").split(",")
CHAINS_FILTER = [c.strip() for c in CHAINS_FILTER if c.strip()]
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()])
log = logging.getLogger()

# Cache traduction persistant
CACHE_FILE = os.path.join(os.getenv("RUNNER_TEMP", "/tmp"), "translate_cache.json")
try:
    with open(CACHE_FILE) as f:
        translate_cache = json.load(f)
    log.info(f"Cache traduction charge: {len(translate_cache)} entrees")
except:
    translate_cache = {}
    log.info("Nouveau cache traduction")

def save_cache():
    with open(CACHE_FILE, 'w') as f:
        json.dump(translate_cache, f, ensure_ascii=False)

SCRAPERS = {
    "RAMI_LEVY":     ("il_supermarket_scarper.scrappers.ramilevy", "RamiLevy", "Rami Levy"),
    "SHUFERSAL":     ("il_supermarket_scarper.scrappers.shufersal", "Shufersal", "Shufersal"),
    "YOHANANOF":     ("il_supermarket_scarper.scrappers.yohananof", "Yohananof", "Yohananof"),
    "VICTORY":       ("il_supermarket_scarper.scrappers.victory", "VictoryNewSource", "Victory"),
    "HAZI_HINAM":    ("il_supermarket_scarper.scrappers.hazihinam", "HaziHinam", "Hazi Hinam"),
    "OSHER_AD":      ("il_supermarket_scarper.scrappers.osherad", "Osherad", "Osher Ad"),
    "TIV_TAAM":      ("il_supermarket_scarper.scrappers.tivtaam", "TivTaam", "Tiv Taam"),
    "YEINOT_BITAN":  ("il_supermarket_scarper.scrappers.bitan", "YaynotBitanAndCarrefour", "Yeinot Bitan & Carrefour"),
    "MAHSANI_ASHUK": ("il_supermarket_scarper.scrappers.machsani_ashuk", "MahsaniAShukNewSource", "Mahsaney HaShuk"),
    "ZOL_VEBEGADOL": ("il_supermarket_scarper.scrappers.zolvebegadol", "ZolVeBegadol", "Zol VeBegadol"),
    "DOR_ALON":      ("il_supermarket_scarper.scrappers.doralon", "DorAlon", "Dor Alon"),
    "STOP_MARKET":   ("il_supermarket_scarper.scrappers.stop_market", "StopMarket", "Stop Market"),
    "SUPER_YUDA":    ("il_supermarket_scarper.scrappers.super_yuda", "SuperYuda", "Super Yuda"),
    "SUPER_PHARM":   ("il_supermarket_scarper.scrappers.super_pharm", "SuperPharm", "Super-Pharm"),
    "SALACH_DABACH": ("il_supermarket_scarper.scrappers.salachdabach", "SalachDabach", "Salach Dabach"),
    "NETIV_HASED":   ("il_supermarket_scarper.scrappers.nativ_hashed", "NetivHased", "Netiv HaSed"),
    "BAREKET":       ("il_supermarket_scarper.scrappers.bareket", "Bareket", "Bareket"),
    "COFIX":         ("il_supermarket_scarper.scrappers.cofix", "Cofix", "Cofix"),
    "CITY_MARKET":   ("il_supermarket_scarper.scrappers.city_market", "CityMarketShops", "City Market"),
    "GOOD_PHARM":    ("il_supermarket_scarper.scrappers.good_pharm", "GoodPharm", "Good Pharm"),
    "HET_COHEN":     ("il_supermarket_scarper.scrappers.het_cohen", "HetCohen", "Het Cohen"),
    "KESHET":        ("il_supermarket_scarper.scrappers.keshet", "Keshet", "Keshet"),
    "KING_STORE":    ("il_supermarket_scarper.scrappers.king_store", "KingStore", "King Store"),
    "MAAYAN2000":    ("il_supermarket_scarper.scrappers.maayan2000", "Maayan2000", "Maayan 2000"),
    "MESHNAT_YOSEF": ("il_supermarket_scarper.scrappers.meshnat_yosef", "MeshnatYosef", "Meshnat Yosef"),
    "POLIZER":       ("il_supermarket_scarper.scrappers.polizer", "Polizer", "Polizer"),
    "SHEFA_BARCART": ("il_supermarket_scarper.scrappers.shefa_barcart_ashem", "ShefaBarcartAshem", "Shefa Barcart"),
    "SHUK_AHIR":     ("il_supermarket_scarper.scrappers.shuk_ahir", "ShukAhir", "Shuk Ahir"),
    "SUPER_SAPIR":   ("il_supermarket_scarper.scrappers.super_sapir", "SuperSapir", "Super Sapir"),
    "FRESH_MARKET":  ("il_supermarket_scarper.scrappers.superdosh", "FreshMarketAndSuperDosh", "Fresh Market"),
    "YELLOW":        ("il_supermarket_scarper.scrappers.yellow", "Yellow", "Yellow"),
}

def translate_batch(names):
    to_translate = [n for n in names if n not in translate_cache]
    if not to_translate:
        return
    for i in range(0, len(to_translate), 50):
        batch = to_translate[i:i+50]
        prompt = (
            "Tu es un expert en produits alimentaires et de pharmacie israeliens. "
            "Traduis ces noms de produits en francais naturel et bien formule. "
            "Garde les noms de marques tels quels (Tnuva, Osem, Elite, Strauss, Materna, etc). "
            "1 ligne par produit, meme ordre, sans numerotation:\n" + "\n".join(batch)
        )
        try:
            r = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            translations = r.choices[0].message.content.strip().split("\n")
            for orig, trans in zip(batch, translations):
                translate_cache[orig] = trans.strip()
            save_cache()
            log.info(f"Traduit {len(batch)} noms, cache total: {len(translate_cache)}")
        except Exception as e:
            log.error(f"Erreur traduction batch: {e}")
            for orig in batch:
                translate_cache[orig] = orig

def image_url(barcode):
    # Pricez comme source principale - Open Food Facts en fallback cote frontend
    return f"https://m.pricez.co.il/ProductPictures/{barcode}.jpg"

def extract_store_id(filename):
    m = re.findall(r'-(\d{3,4})-', filename)
    if len(m) >= 2:
        return m[1]
    elif len(m) == 1:
        return m[0]
    # Pour les fichiers API type Victory sans tirets
    m2 = re.findall(r'(\d{3,4})', filename)
    if m2:
        return m2[-1]
    return "000"

def parse_price_xml(filepath, chain_id):
    items = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        store_id_xml = (root.findtext("StoreId") or root.findtext("store_id") or "").strip()
        store_id_file = extract_store_id(os.path.basename(filepath))
        store_id = store_id_xml or store_id_file or "000"

        for item in root.iter("Item"):
            code = (item.findtext("ItemCode") or item.findtext("barcode") or "").strip()
            name = (item.findtext("ItemName") or item.findtext("ItemNm") or item.findtext("name") or "").strip()
            price_str = (item.findtext("ItemPrice") or item.findtext("price") or "0").strip()
            manufacturer = (item.findtext("ManufacturerName") or item.findtext("manufacturerName") or "").strip()
            unit_qty = (item.findtext("UnitQty") or "").strip()
            unit_measure = (item.findtext("UnitOfMeasure") or item.findtext("unitOfMeasure") or "").strip()
            country = (item.findtext("ManufactureCountry") or "").strip()

            try:
                price = float(price_str)
            except:
                price = 0.0

            if code and name and price > 0:
                items.append({
                    "code": code,
                    "name": name,
                    "price": price,
                    "store_id": store_id,
                    "manufacturer": manufacturer,
                    "unit_qty": unit_qty,
                    "unit_measure": unit_measure,
                    "country": country,
                })
    except Exception as e:
        log.error(f"Erreur parse prix {filepath}: {e}")
    return items

def parse_promo_xml(filepath, chain_id):
    items = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        store_id_xml = (root.findtext("StoreId") or "").strip()
        store_id_file = extract_store_id(os.path.basename(filepath))
        store_id = store_id_xml or store_id_file or "000"

        for promo in root.iter("Promotion"):
            desc_he = (promo.findtext("PromotionDescription") or "").strip()
            
            # Dates — format standard ou Shufersal
            date_start = (
                promo.findtext("PromotionStartDate") or
                (promo.findtext("PromotionStartDateTime") or "")[:10]
            ).strip()[:10]
            date_end = (
                promo.findtext("PromotionEndDate") or
                (promo.findtext("PromotionEndDateTime") or "")[:10]
            ).strip()[:10]

            # Ignorer les promos expirées
            if date_end and date_end < date.today().isoformat():
                continue

            # Prix promo — format standard
            price_promo_str = (
                promo.findtext("DiscountedPrice") or
                promo.findtext("DiscountRate") or
                "0"
            ).strip()
            try:
                price_promo = float(price_promo_str)
            except:
                price_promo = 0.0

            # Filtrer seulement les prix aberrants
            if price_promo >= 9999:
                continue

            promotion_id = (promo.findtext("PromotionID") or "").strip()
            club_id = (promo.findtext("ClubID") or "").strip()
            is_coupon_str = (promo.findtext("AdditionalIsCoupon") or promo.findtext("IsCoupon") or "0").strip()
            is_coupon = is_coupon_str in ("1", "true", "True")

            # Chercher les produits — format standard (Item) ou Shufersal (Groups/Group/Item)
            import xml.etree.ElementTree as ET2
            if len(items) == 0:
                log.info(f"DEBUG XML: {ET2.tostring(promo, encoding='unicode')[:500]}")
            item_codes = []
            for item in promo.iter("Item"):
                code = (item.findtext("ItemCode") or "").strip()
                if not code and len(item_codes) == 0:
                    log.info(f"DEBUG Item tags: {[c.tag for c in item][:5]}, text={item.text}")
                if code:
                    item_codes.append(code)

            if not item_codes:
                groups = promo.find("Groups")
                if groups is not None:
                    first_group = groups.find("Group")
                    if first_group is not None:
                        log.info(f"DEBUG Groups/Group children: {[c.tag for c in first_group][:5]}")
                        first_item = first_group[0] if len(first_group) > 0 else None
                        if first_item is not None:
                            log.info(f"DEBUG first item children: {[c.tag for c in first_item]}")
                continue

            for code in item_codes:
                items.append({
                    "code": code,
                    "store_id": store_id,
                    "price_promo": price_promo,
                    "price_normal": None,
                    "desc": desc_he,
                    "date_start": date_start or None,
                    "date_end": date_end or None,
                    "promotion_id": promotion_id or None,
                    "club_id": club_id or None,
                    "is_coupon": is_coupon,
                })

    except Exception as e:
        log.error(f"Erreur parse promo {filepath}: {e}")
    return items

async def scrape_chain(key, module_path, class_name):
    from il_supermarket_scarper.utils.file_output import DiskFileOutput

    dump_dir = f"/tmp/scrape4_{key}"
    os.makedirs(dump_dir, exist_ok=True)
    log.info(f"Scraping {key}...")

    count = 0
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        output = DiskFileOutput(storage_path=dump_dir)
        scraper = cls(file_output=output)
        today_dt = datetime.combine(date.today(), datetime.min.time())

        async for result in scraper.scrape(when_date=today_dt):
            if result.downloaded:
                count += 1

        log.info(f"{key}: {count} fichiers telecharges")

        # Filtrage: garder uniquement PriceFull + PromoFull
        # Pour les fichiers dates: ne garder que ceux d'aujourd'hui et Full
        # Pour les fichiers sans date (API): garder tous Price/Promo
        today_str = datetime.now().strftime("%Y%m%d")
        kept = 0
        removed = 0
        for f in os.listdir(dump_dir):
            if f.endswith(".gz") or f.endswith(".zip"):
                continue
            fname_lower = f.lower()
            has_date = bool(re.search(r'202\d{5}', f))

            if has_date:
                is_today = today_str in f
                is_full = "pricefull" in fname_lower or "promofull" in fname_lower or fname_lower.startswith("promo")
                if not is_today or not is_full:
                    os.remove(os.path.join(dump_dir, f))
                    removed += 1
                else:
                    kept += 1
            else:
                # Fichiers API sans date: garder tout
                kept += 1

        log.info(f"{key}: {kept} fichiers gardes, {removed} supprimes")

    except Exception as e:
        log.error(f"Erreur scraping {key}: {e}")

    return dump_dir

def upsert_stores(dump_dir, chain_id, key):
    xml_files = [f for f in os.listdir(dump_dir) if f.endswith(".xml")]
    store_ids = set()
    for f in xml_files:
        sid = extract_store_id(f)
        if sid and sid != "000":
            store_ids.add(sid)

    batch = [{"id": f"{chain_id}-{sid}", "chain_id": chain_id, "scraper_key": sid}
             for sid in store_ids]

    for i in range(0, len(batch), 100):
        try:
            supabase.table("stores").upsert(batch[i:i+100], on_conflict="id").execute()
        except Exception as e:
            log.error(f"Erreur upsert stores {key}: {e}")

def upsert_products_and_prices(items, chain_id, key):
    if not items:
        return 0

    # Deduplication par (code, store_id) - garder dernier
    seen = {}
    for item in items:
        seen[(item["code"], item["store_id"])] = item
    deduped = list(seen.values())

    # Traduire noms uniques
    # Traduction désactivée - gérée par translate.py

    prod_batch = []
    price_batch = []
    for item in deduped:
        barcode = item["code"]
        name_he = item["name"]
        name_fr = name_he
        store_full_id = f"{chain_id}-{item['store_id']}"

        prod_batch.append({
            "barcode": barcode,
            "name_he": name_he,
            "name_fr": name_fr,
            "image_url": image_url(barcode),
            "unit_qty": item.get("unit_qty") or None,
            "unit_measure": item.get("unit_measure") or None,
        })
        price_batch.append({
            "barcode": barcode,
            "chain_id": chain_id,
            "store_id": store_full_id,
            "price": item["price"],
            "updated_at": "now()",
        })

    # Upsert produits
    for i in range(0, len(prod_batch), 200):
        try:
            supabase.table("products").upsert(
                prod_batch[i:i+200], on_conflict="barcode"
            ).execute()
        except Exception as e:
            log.error(f"Erreur upsert products {key}: {e}")

    # Upsert prix
    errors = 0
    for i in range(0, len(price_batch), 200):
        try:
            supabase.table("prices").upsert(
                price_batch[i:i+200],
                on_conflict="barcode,chain_id,store_id"
            ).execute()
        except Exception as e:
            errors += 1
            if errors <= 2:
                log.error(f"Erreur upsert prices {key}: {e}")

    return len(deduped)

def upsert_promos(items, chain_id, key):
    if not items:
        return 0

    seen = {}
    for item in items:
        seen[(item["code"], item["store_id"], item.get("date_start"))] = item
    deduped = list(seen.values())

    batch = []
    for item in deduped:
        store_full_id = f"{chain_id}-{item['store_id']}"
        batch.append({
            "barcode": item["code"],
            "chain_id": chain_id,
            "store_id": store_full_id,
            "price_promo": item["price_promo"],
            "price_normal": item["price_normal"],
            "promo_description_he": item["desc"] or None,
            "date_start": item["date_start"],
            "date_end": item["date_end"],
            "updated_at": "now()",
        })

    errors = 0
    for i in range(0, len(batch), 200):
        try:
            supabase.table("promos").upsert(
                batch[i:i+200],
                on_conflict="barcode,chain_id,store_id,date_start"
            ).execute()
        except Exception as e:
            errors += 1
            if errors <= 2:
                log.error(f"Erreur upsert promos {key}: {e}")

    return len(deduped)

def import_chain(key, dump_dir, chain_id):
    import gzip, shutil
    # Décompresser les fichiers sans extension (King Store format)
    for f in os.listdir(dump_dir):
        fpath = os.path.join(dump_dir, f)
        if not f.endswith(".xml") and not f.endswith(".gz") and not f.endswith(".zip"):
            try:
                with gzip.open(fpath, 'rb') as gz:
                    xml_path = fpath + ".xml"
                    with open(xml_path, 'wb') as out:
                        out.write(gz.read())
                os.remove(fpath)
            except:
                pass

    xml_files = [os.path.join(dump_dir, f) for f in os.listdir(dump_dir) if f.endswith(".xml")]
    if not xml_files:
        log.warning(f"{key}: aucun fichier xml")
        return 0, 0

    upsert_stores(dump_dir, chain_id, key)

    price_items = []
    promo_items = []
    for f in xml_files:
        fname = os.path.basename(f).lower()
        if "price" in fname:
            price_items.extend(parse_price_xml(f, chain_id))
        if "promo" in fname:
            promo_items.extend(parse_promo_xml(f, chain_id))

    n_prices = upsert_products_and_prices(price_items, chain_id, key) if price_items else 0
    n_promos = upsert_promos(promo_items, chain_id, key) if promo_items else 0

    log.info(f"{key}: {n_prices} prix, {n_promos} promos")
    return n_prices, n_promos

async def main():
    log.info("=== DEBUT IMPORT v4 ===")
    total_prices = 0
    total_promos = 0

    for key, (module, cls, name_fr) in SCRAPERS.items():
        if CHAINS_FILTER and key not in CHAINS_FILTER:
            continue
        log.info(f"--- {key} ---")
        try:
            supabase.table("chains").upsert(
                {"scraper_key": key, "name_fr": name_fr, "name_he": name_fr},
                on_conflict="scraper_key"
            ).execute()
            res = supabase.table("chains").select("id").eq("scraper_key", key).execute()
            if not res.data:
                log.error(f"Pas de chain_id pour {key}")
                continue
            chain_id = res.data[0]["id"]

            dump_dir = await scrape_chain(key, module, cls)
            n_p, n_pr = import_chain(key, dump_dir, chain_id)
            total_prices += n_p
            total_promos += n_pr

            shutil.rmtree(dump_dir, ignore_errors=True)

        except Exception as e:
            log.error(f"Erreur {key}: {e}")

    save_cache()
    log.info(f"=== TERMINE: {total_prices} prix, {total_promos} promos ===")

if __name__ == "__main__":
    asyncio.run(main())
