import asyncio, os, re, xml.etree.ElementTree as ET, importlib
from datetime import datetime, date

SCRAPERS = {
    "RAMI_LEVY":     ("il_supermarket_scarper.scrappers.ramilevy", "RamiLevy"),
    "SHUFERSAL":     ("il_supermarket_scarper.scrappers.shufersal", "Shufersal"),
    "YOHANANOF":     ("il_supermarket_scarper.scrappers.yohananof", "Yohananof"),
    "VICTORY":       ("il_supermarket_scarper.scrappers.victory", "VictoryNewSource"),
    "HAZI_HINAM":    ("il_supermarket_scarper.scrappers.hazihinam", "HaziHinam"),
    "OSHER_AD":      ("il_supermarket_scarper.scrappers.osherad", "Osherad"),
    "TIV_TAAM":      ("il_supermarket_scarper.scrappers.tivtaam", "TivTaam"),
    "YEINOT_BITAN":  ("il_supermarket_scarper.scrappers.bitan", "YaynotBitanAndCarrefour"),
    "MAHSANI_ASHUK": ("il_supermarket_scarper.scrappers.machsani_ashuk", "MahsaniAShukNewSource"),
    "ZOL_VEBEGADOL": ("il_supermarket_scarper.scrappers.zolvebegadol", "ZolVeBegadol"),
    "DOR_ALON":      ("il_supermarket_scarper.scrappers.doralon", "DorAlon"),
    "STOP_MARKET":   ("il_supermarket_scarper.scrappers.stop_market", "StopMarket"),
    "SUPER_YUDA":    ("il_supermarket_scarper.scrappers.super_yuda", "SuperYuda"),
    "SUPER_PHARM":   ("il_supermarket_scarper.scrappers.super_pharm", "SuperPharm"),
    "SALACH_DABACH": ("il_supermarket_scarper.scrappers.salachdabach", "SalachDabach"),
    "NETIV_HASED":   ("il_supermarket_scarper.scrappers.nativ_hashed", "NetivHased"),
    "BAREKET":       ("il_supermarket_scarper.scrappers.bareket", "Bareket"),
    "COFIX":         ("il_supermarket_scarper.scrappers.cofix", "Cofix"),
    "CITY_MARKET":   ("il_supermarket_scarper.scrappers.city_market", "CityMarketShops"),
    "GOOD_PHARM":    ("il_supermarket_scarper.scrappers.good_pharm", "GoodPharm"),
    "HET_COHEN":     ("il_supermarket_scarper.scrappers.het_cohen", "HetCohen"),
    "KESHET":        ("il_supermarket_scarper.scrappers.keshet", "Keshet"),
    "KING_STORE":    ("il_supermarket_scarper.scrappers.king_store", "KingStore"),
    "MAAYAN2000":    ("il_supermarket_scarper.scrappers.maayan2000", "Maayan2000"),
    "MESHNAT_YOSEF": ("il_supermarket_scarper.scrappers.meshnat_yosef", "MeshnatYosef"),
    "POLIZER":       ("il_supermarket_scarper.scrappers.polizer", "Polizer"),
    "SHEFA_BARCART": ("il_supermarket_scarper.scrappers.shefa_barcart_ashem", "ShefaBarcartAshem"),
    "SHUK_AHIR":     ("il_supermarket_scarper.scrappers.shuk_ahir", "ShukAhir"),
    "SUPER_SAPIR":   ("il_supermarket_scarper.scrappers.super_sapir", "SuperSapir"),
    "FRESH_MARKET":  ("il_supermarket_scarper.scrappers.superdosh", "FreshMarketAndSuperDosh"),
    "YELLOW":        ("il_supermarket_scarper.scrappers.yellow", "Yellow"),
}

def sid_xml(root):
    for t in ("StoreID","StoreId","store_id","storeid"):
        v = root.findtext(t)
        if v and v.strip(): return v.strip()
    return "ABSENT"

def sid_file(fname):
    m = re.findall(r'-(\d{3,4})-', fname)
    return m[1] if len(m)>=2 else (m[0] if m else "ABSENT")

async def test(key, mod_path, cls_name):
    from il_supermarket_scarper.utils import DiskFileOutput
    d = f"/tmp/test_sid_{key}"
    os.makedirs(d, exist_ok=True)
    try:
        mod = importlib.import_module(mod_path)
        s = getattr(mod, cls_name)(file_output=DiskFileOutput(storage_path=d))
        n = 0
        async for r in s.scrape(when_date=datetime.combine(date.today(), datetime.min.time())):
            if r.downloaded:
                n += 1
                if n >= 2: break
    except Exception as e:
        print(f"[{key}] ERREUR: {e}"); return
    xmls = [f for f in os.listdir(d) if f.endswith(".xml")]
    if not xmls:
        print(f"[{key}] Aucun XML"); return
    print(f"\n=== {key} ===")
    for f in xmls[:2]:
        sf = sid_file(f)
        try: sx = sid_xml(ET.parse(os.path.join(d,f)).getroot())
        except: sx = "ERREUR"
        ok = "✅" if sx==sf else "⚠️ DIFFERENT"
        print(f"  {f}\n  XML={sx}  Fichier={sf}  {ok}")

async def main():
    await asyncio.gather(*[test(k,m,c) for k,(m,c) in SCRAPERS.items()])
    print("\n=== FIN ===")

asyncio.run(main())
