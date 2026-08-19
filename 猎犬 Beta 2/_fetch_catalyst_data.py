"""Fetch catalyst data for 30 stocks: financials, eps_forecast, news, reports"""
import json, time, logging, sys
from hound_system.data.fetcher import HoundFetcher

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
f = HoundFetcher()

CODES = [
    "601288","601298","601318","601319","601328","601333","601336","601360",
    "601375","601377","601388","601390","601398","601399","601456","601515",
    "601519","601555","601567","601577","601579","601600","601601","601606",
    "601607","601608","601609","601611","601615","601618"
]

result = {}
for code in CODES:
    print(f"[{code}] fetching...", file=sys.stderr)
    entry = {"code": code}
    try:
        fin = f.get_financials(code)
        entry["financials"] = fin if fin else None
    except Exception as e:
        entry["financials"] = {"error": str(e)}
    time.sleep(0.3)

    try:
        eps = f.get_eps_forecast(code)
        entry["eps_forecast"] = eps if eps else None
    except Exception as e:
        entry["eps_forecast"] = {"error": str(e)}
    time.sleep(0.3)

    try:
        news = f.get_stock_news(code)
        entry["news"] = news[:10] if news else None
    except Exception as e:
        entry["news"] = {"error": str(e)}
    time.sleep(0.3)

    try:
        rpt = f.get_reports(code)
        entry["reports"] = rpt[:5] if rpt else None
    except Exception as e:
        entry["reports"] = {"error": str(e)}
    time.sleep(0.3)

    result[code] = entry
    print(f"[{code}] done", file=sys.stderr)

SAVE_PATH = "/home/sui/claude workspace/猎犬系统/猎犬 Beta 2/_catalyst_data.json"
with open(SAVE_PATH, "w", encoding="utf-8") as fp:
    json.dump(result, fp, ensure_ascii=False, indent=2)

print(f"Saved {len(result)} stocks to {SAVE_PATH}", file=sys.stderr)
