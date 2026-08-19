"""批量取数：催化分析30只股票"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from hound_system.data.fetcher import HoundFetcher

CODES = [
    "600331","600332","600338","600339","600343","600345","600346",
    "600348","600352","600353","600360","600361","600362","600363",
    "600366","600367","600369","600372","600376","600377","600378",
    "600379","600380","600382","600383","600388","600389","600390",
    "600391","600392"
]

f = HoundFetcher()
results = {}

for code in CODES:
    print(f"[{code}] fetching...", flush=True)
    card = {"code": code}

    # 基本面
    try:
        fin = f.get_financials(code)
        card["financials"] = fin
    except Exception as e:
        card["financials"] = {"error": str(e)}

    # 分析师预期
    try:
        eps = f.get_eps_forecast(code)
        card["eps_forecast"] = eps
    except Exception as e:
        card["eps_forecast"] = {"error": str(e)}

    # 个股新闻
    try:
        news = f.get_stock_news(code)
        # 取最新10条
        if news and len(news) > 10:
            news = news[:10]
        card["stock_news"] = news
    except Exception as e:
        card["stock_news"] = {"error": str(e)}

    # 研报
    try:
        reports = f.get_reports(code)
        card["reports"] = reports
    except Exception as e:
        card["reports"] = {"error": str(e)}

    results[code] = card

with open("/tmp/catalyst_data.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"\nDone. {len(results)} stocks fetched.")
print(f"Saved to /tmp/catalyst_data.json")
