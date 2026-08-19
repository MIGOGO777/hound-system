"""Test single stock fetch"""
import json, sys, os
sys.path.insert(0, "/home/sui/claude workspace/猎犬系统/猎犬 Beta 2")

from hound_system.data.fetcher import HoundFetcher

f = HoundFetcher()

# Test a single stock
code = "600331"
fin = f.get_financials(code)
print(f"600331 financials: {json.dumps(fin, ensure_ascii=False, default=str)[:200]}")

news = f.get_stock_news(code)
print(f"news count: {len(news) if news else 0}")
if news:
    for n in news[:3]:
        print(f"  - {n.get('title','')[:80]}")

eps = f.get_eps_forecast(code)
print(f"eps forecast: {eps}")

reports = f.get_reports(code)
print(f"reports count: {len(reports) if reports else 0}")
