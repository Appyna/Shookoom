import os, asyncio, importlib, gzip, xml.etree.ElementTree as ET
from datetime import date, datetime

SCRAPERS = {
    "SHUFERSAL": ("il_supermarket_scarper.scrappers.shufersal", "Shufersal"),
    "RAMI_LEVY": ("il_supermarket_scarper.scrappers.ramilevy", "RamiLevy"),
    "YEINOT_BITAN": ("il_supermarket_scarper.scrappers.bitan", "YaynotBitanAndCarrefour"),
    "TIV_TAAM": ("il_supermarket_scarper.scrappers.tivtaam", "TivTaam"),
    "YOHANANOF": ("il_supermarket_scarper.scrappers.yohananof", "Yohananof"),
    "VICTORY": ("il_supermarket_scarper.scrappers.victory", "VictoryNewSource"),
    "KESHET": ("il_supermarket_scarper.scrappers.keshet", "Keshet"),
    "OSHER_AD": ("il_supermarket_scarper.scrappers.osherad", "Osherad"),
    "MAHSANI_ASHUK": ("il_supermarket_scarper.scrappers.machsani_ashuk", "MahsaniAShukNewSource"),
    "ZOL_VEBEGADOL": ("il_supermarket_scarper.scrappers.zolvebegadol", "ZolVeBegadol"),
    "DOR_ALON": ("il_supermarket_scarper.scrappers.doralon", "DorAlon"),
    "STOP_MARKET": ("il_supermarket_scarper.scrappers.stop_market", "StopMarket"),
    "SUPER_YUDA": ("il_supermarket_scarper.scrappers.super_yuda", "SuperYuda"),
    "SALACH_DABACH": ("il_supermarket_scarper.scrappers.salachdabach", "SalachDabach"),
    "NETIV_HASED": ("il_supermarket_scarper.scrappers.nativ_hashed", "NetivHased"),
    "BAREKET": ("il_supermarket_scarper.scrappers.bareket", "Bareket"),
    "CITY_MARKET": ("il_supermarket_scarper.scrappers.city_market", "CityMarketShops"),
    "GOOD_PHARM": ("il_supermarket_scarper.scrappers.good_pharm", "GoodPharm"),
    "HAZI_HINAM": ("il_supermarket_scarper.scrappers.hazihinam", "HaziHinam"),
    "KING_STORE": ("il_supermarket_scarper.scrappers.king_store", "KingStore"),
    "MAAYAN2000": ("il_supermarket_scarper.scrappers.maayan2000", "Maayan2000"),
    "POLIZER": ("il_supermarket_scarper.scrappers.polizer", "Polizer"),
    "SHEFA_BARCART": ("il_supermarket_scarper.scrappers.shefa_barcart_ashem", "ShefaBarcartAshem"),
    "SHUK_AHIR": ("il_supermarket_scarper.scrappers.shuk_ahir", "ShukAhir"),
    "SUPER_SAPIR": ("il_supermarket_scarper.scrappers.super_sapir", "SuperSapir"),
    "FRESH_MARKET": ("il_supermarket_scarper.scrappers.superdosh", "FreshMarketAndSuperDosh"),
    "YELLOW": ("il_supermarket_scarper.scrappers.yellow", "Yellow"),
    "DOR_ALON": ("il_supermarket_scarper.scrappers.doralon", "DorAlon"),
    "HAZI_HINAM": ("il_supermarket_scarper.scrappers.hazihinam", "HaziHinam"),
}

def read_xml(filepath):
    """Lit un fichier XML (compressé ou non)"""
    try:
        with gzip.open(filepath, 'rb') as f:
            content = f.read()
    except:
        with open(filepath, 'rb') as f:
            content = f.read()
    try:
        root = ET.fromstring(content)
        return root
    except:
        return None

def analyze_promo_file(filepath):
    """Analyse un fichier promo et retourne les tags disponibles"""
    root = read_xml(filepath)
    if root is None:
        return None, 0
    promos = list(root.iter("Promotion"))
    if not promos:
        return None, 0
    tags = [child.tag for child in promos[0]]
    return tags, len(promos)

async def check_chain(key, module_path, class_name):
    from il_supermarket_scarper.utils.file_output import DiskFileOutput
    dump_dir = f"/tmp/check_{key}"
    os.makedirs(dump_dir, exist_ok=True)
    
    result_lines = []
    result_lines.append(f"\n{'='*60}")
    result_lines.append(f"CHAÎNE: {key}")
    
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        output = DiskFileOutput(storage_path=dump_dir)
        scraper = cls(file_output=output)
        today_dt = datetime.combine(date.today(), datetime.min.time())
        
        count = 0
        async for result in scraper.scrape(when_date=today_dt):
            if result.downloaded:
                count += 1
        
        files = os.listdir(dump_dir)
        
        # Analyser les fichiers
        price_full = [f for f in files if "pricefull" in f.lower()]
        price_partial = [f for f in files if "price" in f.lower() and "pricefull" not in f.lower()]
        promo_full = [f for f in files if "promofull" in f.lower()]
        promo_partial = [f for f in files if "promo" in f.lower() and "promofull" not in f.lower()]
        
        result_lines.append(f"  📦 Total fichiers téléchargés: {count}")
        result_lines.append(f"  💰 PriceFull: {len(price_full)} | Price: {len(price_partial)}")
        result_lines.append(f"  🏷️  PromoFull: {len(promo_full)} | Promo: {len(promo_partial)}")
        
        # Analyser le format des promos si disponibles
        promo_files = promo_full + promo_partial
        if promo_files:
            filepath = os.path.join(dump_dir, promo_files[0])
            tags, nb_promos = analyze_promo_file(filepath)
            if tags:
                result_lines.append(f"  📋 Format promo: {tags}")
                result_lines.append(f"  📊 Promos dans premier fichier: {nb_promos}")
                # Vérifier les champs clés
                has_discount = "DiscountedPrice" in tags or "DiscountRate" in tags
                has_date_end = "PromotionEndDate" in tags or "PromotionEndDateTime" in tags
                has_items = "Items" in tags or "Groups" in tags
                result_lines.append(f"  ✅ Prix promo: {'OUI' if has_discount else 'NON'}")
                result_lines.append(f"  ✅ Date fin: {'OUI' if has_date_end else 'NON'}")
                result_lines.append(f"  ✅ Produits: {'OUI' if has_items else 'NON'}")
            else:
                result_lines.append(f"  ⚠️ Impossible de parser le fichier promo")
        else:
            result_lines.append(f"  ❌ Aucun fichier promo trouvé")
            
    except Exception as e:
        result_lines.append(f"  ❌ ERREUR: {str(e)[:200]}")
    
    print("\n".join(result_lines))

async def main():
    print("🔍 Analyse de toutes les chaînes...")
    print(f"Date: {date.today()}")
    
    for key, (module, cls) in SCRAPERS.items():
        await check_chain(key, module, cls)
    
    print(f"\n{'='*60}")
    print("✅ Analyse terminée")

asyncio.run(main())
