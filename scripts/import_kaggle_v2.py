import os, asyncio, logging, xml.etree.ElementTree as ET, importlib, re, gzip, shutil, time
from datetime import date, datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

CHAINS_FILTER = os.getenv("CHAINS_TO_SCRAPE", "").split(",")
CHAINS_FILTER = [c.strip() for c in CHAINS_FILTER if c.strip()]

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()])
log = logging.getLogger()

def fetch_with_retry(fn, max_retries=5, base_delay=30):
    """Exécute fn() avec retry exponentiel en cas d'erreur réseau/Supabase."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)  # 30s, 60s, 120s, 240s
            log.warning(f"Erreur Supabase (tentative {attempt+1}/{max_retries}): {e} — retry dans {delay}s...")
            time.sleep(delay)

# Chargement des barcodes connus dans products_new (une seule fois au démarrage)
log.info("Chargement des barcodes products_new...")
_known_barcodes = set()
offset = 0
while True:
    res = fetch_with_retry(
        lambda off=offset: supabase.table("products_new").select("barcode").range(off, off + 999).execute()
    )
    if not res.data:
        break
    for row in res.data:
        _known_barcodes.add(row["barcode"])
    if len(res.data) < 1000:
        break
    offset += 1000
log.info(f"{len(_known_barcodes)} barcodes chargés depuis products_new")

SCRAPERS = {
    "RAMI_LEVY":     ("il_supermarket_scarper.scrappers.ramilevy", "RamiLevy", "rami_levy"),
    "SHUFERSAL":     ("il_supermarket_scarper.scrappers.shufersal", "Shufersal", "shufersal"),
    "YOHANANOF":     ("il_supermarket_scarper.scrappers.yohananof", "Yohananof", "yohananof"),
    "VICTORY":       ("il_supermarket_scarper.scrappers.victory", "VictoryNewSource", "victory"),
    "HAZI_HINAM":    ("il_supermarket_scarper.scrappers.hazihinam", "HaziHinam", "hazi_hinam"),
    "OSHER_AD":      ("il_supermarket_scarper.scrappers.osherad", "Osherad", "osher_ad"),
    "TIV_TAAM":      ("il_supermarket_scarper.scrappers.tivtaam", "TivTaam", "tiv_taam"),
    "YEINOT_BITAN":  ("il_supermarket_scarper.scrappers.bitan", "YaynotBitanAndCarrefour", "yeinot_bitan"),
    "MAHSANI_ASHUK": ("il_supermarket_scarper.scrappers.machsani_ashuk", "MahsaniAShukNewSource", "mahsani_ashuk"),
    "ZOL_VEBEGADOL": ("il_supermarket_scarper.scrappers.zolvebegadol", "ZolVeBegadol", "zol_vebegadol"),
    "DOR_ALON":      ("il_supermarket_scarper.scrappers.doralon", "DorAlon", "dor_alon"),
    "STOP_MARKET":   ("il_supermarket_scarper.scrappers.stop_market", "StopMarket", "stop_market"),
    "SUPER_YUDA":    ("il_supermarket_scarper.scrappers.super_yuda", "SuperYuda", "super_yuda"),
    "SUPER_PHARM":   ("il_supermarket_scarper.scrappers.super_pharm", "SuperPharm", "super_pharm"),
    "SALACH_DABACH": ("il_supermarket_scarper.scrappers.salachdabach", "SalachDabach", "salach_dabach"),
    "NETIV_HASED":   ("il_supermarket_scarper.scrappers.nativ_hashed", "NetivHased", "netiv_hased"),
    "BAREKET":       ("il_supermarket_scarper.scrappers.bareket", "Bareket", "bareket"),
    "COFIX":         ("il_supermarket_scarper.scrappers.cofix", "Cofix", "cofix"),
    "CITY_MARKET":   ("il_supermarket_scarper.scrappers.city_market", "CityMarketShops", "city_market"),
    "GOOD_PHARM":    ("il_supermarket_scarper.scrappers.good_pharm", "GoodPharm", "good_pharm"),
    "HET_COHEN":     ("il_supermarket_scarper.scrappers.het_cohen", "HetCohen", "het_cohen"),
    "KESHET":        ("il_supermarket_scarper.scrappers.keshet", "Keshet", "keshet"),
    "KING_STORE":    ("il_supermarket_scarper.scrappers.king_store", "KingStore", "king_store"),
    "MAAYAN2000":    ("il_supermarket_scarper.scrappers.maayan2000", "Maayan2000", "maayan2000"),
    # MESHNAT_YOSEF: n'existe pas dans il-supermarket-scraper==1.0.15 (absent du package)
    "POLIZER":       ("il_supermarket_scarper.scrappers.polizer", "Polizer", "polizer"),
    "SHEFA_BARCART": ("il_supermarket_scarper.scrappers.shefa_barcart_ashem", "ShefaBarcartAshem", "shefa_barcart"),
    "SHUK_AHIR":     ("il_supermarket_scarper.scrappers.shuk_ahir", "ShukAhir", "shuk_ahir"),
    "SUPER_SAPIR":   ("il_supermarket_scarper.scrappers.super_sapir", "SuperSapir", "super_sapir"),
    "FRESH_MARKET":  ("il_supermarket_scarper.scrappers.superdosh", "FreshMarketAndSuperDosh", "fresh_market"),
    "YELLOW":        ("il_supermarket_scarper.scrappers.yellow", "Yellow", "yellow"),
}

def get_store_id_from_xml(root):
    """Lit le vrai StoreID depuis le XML (insensible à la casse du tag)."""
    for tag in ("StoreID", "StoreId", "store_id", "storeid"):
        val = root.findtext(tag)
        if val and val.strip():
            return val.strip()
    return ""

def extract_store_id_from_filename(filename):
    """Fallback: extrait le store_id depuis le nom de fichier."""
    m = re.findall(r'-(\d{3,4})-', filename)
    if len(m) >= 2:
        return m[1]
    elif len(m) == 1:
        return m[0]
    m2 = re.findall(r'(\d{3,4})', filename)
    if m2:
        return m2[-1]
    return "000"

def parse_price_xml(filepath, chain_id):
    items = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        store_id = get_store_id_from_xml(root) or extract_store_id_from_filename(os.path.basename(filepath)) or "000"

        for item in root.iter("Item"):
            code = (item.findtext("ItemCode") or item.findtext("barcode") or "").strip()
            price_str = (item.findtext("ItemPrice") or item.findtext("price") or "0").strip()
            try:
                price = float(price_str)
            except:
                price = 0.0
            if code and price > 0:
                items.append({"code": code, "price": price, "store_id": store_id})
    except Exception as e:
        log.error(f"Erreur parse prix {filepath}: {e}")
    return items

def parse_promo_xml(filepath, chain_id):
    items = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        store_id = get_store_id_from_xml(root) or extract_store_id_from_filename(os.path.basename(filepath)) or "000"

        for promo in root.iter("Promotion"):
            desc_he = (promo.findtext("PromotionDescription") or "").strip()
            date_start = (promo.findtext("PromotionStartDate") or (promo.findtext("PromotionStartDateTime") or "")[:10]).strip()[:10]
            date_end = (promo.findtext("PromotionEndDate") or (promo.findtext("PromotionEndDateTime") or "")[:10]).strip()[:10]

            if date_end and date_end < date.today().isoformat():
                continue

            price_promo_str = (promo.findtext("DiscountedPrice") or promo.findtext("DiscountRate") or "0").strip()
            try:
                price_promo = float(price_promo_str)
            except:
                price_promo = 0.0
            if price_promo >= 9999:
                continue

            discount_rate_str = (promo.findtext("DiscountRate") or "0").strip()
            try:
                discount_rate = float(discount_rate_str) or None
            except:
                discount_rate = None

            promotion_id = (promo.findtext("PromotionID") or "").strip() or None
            is_coupon_str = (promo.findtext("AdditionalIsCoupon") or promo.findtext("IsCoupon") or "0").strip()
            is_coupon = is_coupon_str in ("1", "true", "True")

            try:
                min_qty = float((promo.findtext("MinQty") or promo.findtext("MinimumQuantity") or "0").strip()) or None
            except:
                min_qty = None
            try:
                max_qty = float((promo.findtext("MaxQty") or promo.findtext("MaximumQuantity") or "0").strip()) or None
            except:
                max_qty = None

            item_codes = [el.text.strip() for el in promo.iter() if el.tag == "ItemCode" and el.text and el.text.strip()]
            if not item_codes:
                continue

            for code in item_codes:
                items.append({
                    "code": code, "store_id": store_id,
                    "price_promo": price_promo if price_promo > 0 else None,
                    "price_normal": None, "discount_rate": discount_rate,
                    "desc": desc_he or None,
                    "date_start": date_start or None, "date_end": date_end or None,
                    "promotion_id": promotion_id, "is_coupon": is_coupon,
                    "min_qty": min_qty, "max_qty": max_qty,
                })
    except Exception as e:
        log.error(f"Erreur parse promo {filepath}: {e}")
    return items

async def scrape_chain(key, module_path, class_name):
    from il_supermarket_scarper.utils import DiskFileOutput
    dump_dir = f"/tmp/scrape_v2_{key}"
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
        log.info(f"{key}: {count} fichiers téléchargés")
        today_str = datetime.now().strftime("%Y%m%d")
        kept = removed = 0
        for f in os.listdir(dump_dir):
            if f.endswith(".gz") or f.endswith(".zip"):
                continue
            fname_lower = f.lower()
            has_date = bool(re.search(r'202\d{5}', f))
            if has_date:
                is_today = today_str in f
                is_full = "pricefull" in fname_lower or "promofull" in fname_lower or fname_lower.startswith("promo")
                if not is_today or not is_full:
                    os.remove(os.path.join(dump_dir, f)); removed += 1
                else:
                    kept += 1
            else:
                kept += 1
        log.info(f"{key}: {kept} fichiers gardés, {removed} supprimés")
    except Exception as e:
        log.error(f"Erreur scraping {key}: {e}")
    return dump_dir

def upsert_stores(dump_dir, chain_id, key):
    """Extrait les store_ids depuis le XML (vrai ID gouvernemental) et les upsert dans stores."""
    xml_files = [f for f in os.listdir(dump_dir) if f.endswith(".xml")]
    store_ids = set()
    for f in xml_files:
        fpath = os.path.join(dump_dir, f)
        try:
            tree = ET.parse(fpath)
            root = tree.getroot()
            sid = get_store_id_from_xml(root)
            if not sid:
                sid = extract_store_id_from_filename(f)
            if sid and sid != "000":
                store_ids.add(sid)
        except:
            sid = extract_store_id_from_filename(f)
            if sid and sid != "000":
                store_ids.add(sid)
    batch = [{"chain_id": chain_id, "store_id": sid} for sid in store_ids]
    for i in range(0, len(batch), 100):
        try:
            fetch_with_retry(lambda b=batch[i:i+100]: supabase.table("stores").upsert(b, on_conflict="chain_id,store_id").execute())
        except Exception as e:
            log.error(f"Erreur upsert stores {key}: {e}")

def upsert_prices(items, chain_id, key):
    if not items:
        return 0
    seen = {}
    for item in items:
        seen[(item["code"], item["store_id"])] = item
    deduped = list(seen.values())
    filtered = [item for item in deduped if item["code"] in _known_barcodes]
    skipped = len(deduped) - len(filtered)
    if skipped > 0:
        log.info(f"{key}: {skipped} prix ignorés (barcode absent de products_new)")
    if not filtered:
        return 0
    batch = [{"barcode": item["code"], "chain_id": chain_id,
              "store_id": item["store_id"],
              "price": item["price"], "updated_at": "now()"} for item in filtered]
    errors = 0
    for i in range(0, len(batch), 200):
        try:
            fetch_with_retry(lambda b=batch[i:i+200]: supabase.table("prices_new").upsert(b, on_conflict="barcode,store_id").execute())
        except Exception as e:
            errors += 1
            if errors <= 2:
                log.error(f"Erreur upsert prices_new {key}: {e}")
    return len(filtered)

def upsert_promos(items, chain_id, key):
    if not items:
        return 0
    seen = {}
    for item in items:
        seen[(item["code"], item["store_id"], item.get("date_start"))] = item
    deduped = list(seen.values())
    filtered = [item for item in deduped if item["code"] in _known_barcodes]
    skipped = len(deduped) - len(filtered)
    if skipped > 0:
        log.info(f"{key}: {skipped} promos ignorées (barcode absent de products_new)")
    if not filtered:
        return 0
    batch = [{"barcode": item["code"], "chain_id": chain_id,
              "store_id": item["store_id"],
              "price_promo": item["price_promo"], "price_normal": item["price_normal"],
              "discount_rate": item["discount_rate"], "promo_description_he": item["desc"],
              "date_start": item["date_start"], "date_end": item["date_end"],
              "promotion_id": item["promotion_id"], "is_coupon": item["is_coupon"],
              "min_qty": item["min_qty"], "max_qty": item["max_qty"],
              "updated_at": "now()"} for item in filtered]
    errors = 0
    for i in range(0, len(batch), 200):
        try:
            fetch_with_retry(lambda b=batch[i:i+200]: supabase.table("promos_new").insert(b).execute())
        except Exception as e:
            errors += 1
            if errors <= 2:
                log.error(f"Erreur insert promos_new {key}: {e}")
    return len(filtered)

def cleanup_expired_promos():
    try:
        today = date.today().isoformat()
        result = fetch_with_retry(lambda: supabase.table("promos_new").delete().lt("date_end", today).execute())
        log.info(f"Promos expirées supprimées: {len(result.data) if result.data else 0}")
    except Exception as e:
        log.error(f"Erreur cleanup promos: {e}")

def import_chain(key, dump_dir, chain_id):
    for f in os.listdir(dump_dir):
        fpath = os.path.join(dump_dir, f)
        if not f.endswith(".xml") and not f.endswith(".gz") and not f.endswith(".zip"):
            try:
                with gzip.open(fpath, 'rb') as gz:
                    with open(fpath + ".xml", 'wb') as out:
                        out.write(gz.read())
                os.remove(fpath)
            except:
                pass
    xml_files = [os.path.join(dump_dir, f) for f in os.listdir(dump_dir) if f.endswith(".xml")]
    if not xml_files:
        log.warning(f"{key}: aucun fichier xml")
        return 0, 0
    upsert_stores(dump_dir, chain_id, key)
    price_items, promo_items = [], []
    for f in xml_files:
        fname = os.path.basename(f).lower()
        if "price" in fname:
            price_items.extend(parse_price_xml(f, chain_id))
        if "promo" in fname:
            promo_items.extend(parse_promo_xml(f, chain_id))
    n_prices = upsert_prices(price_items, chain_id, key) if price_items else 0
    n_promos = upsert_promos(promo_items, chain_id, key) if promo_items else 0
    log.info(f"{key}: {n_prices} prix, {n_promos} promos → prices_new / promos_new")
    return n_prices, n_promos

async def main():
    log.info("=== DEBUT IMPORT v2 (products_new) ===")
    total_prices = total_promos = 0
    for key, (module, cls, chain_id) in SCRAPERS.items():
        if CHAINS_FILTER and key not in CHAINS_FILTER:
            continue
        log.info(f"--- {key} ---")
        try:
            dump_dir = await scrape_chain(key, module, cls)
            n_p, n_pr = import_chain(key, dump_dir, chain_id)
            total_prices += n_p
            total_promos += n_pr
            shutil.rmtree(dump_dir, ignore_errors=True)
        except Exception as e:
            log.error(f"Erreur {key}: {e}")
    cleanup_expired_promos()
    log.info(f"=== TERMINÉ: {total_prices} prix, {total_promos} promos ===")

if __name__ == "__main__":
    asyncio.run(main())
