"""Fetch valuation data for 30 stocks — output to JSON for analysis."""
import json, sys, time, logging
from hound_system.data.fetcher import HoundFetcher

logging.basicConfig(level=logging.WARNING)
f = HoundFetcher()

TICKERS = [
    "603983","603985","603986","603989","603990",
    "603991","603993","603997","605117","605118",
    "605123","605128","605133","605167","605168",
    "605178","605186","605196","605198","605199",
    "605376","605377","605389","605399","605488",
    "605499","605507","605555","605566","605580"
]

def fetch_all():
    result = {}
    for i, t in enumerate(TICKERS, 1):
        print(f"[{i}/30] {t}...", file=sys.stderr)
        card = {"code": t}

        # 1. Valuation
        try:
            card["valuation"] = f.get_valuation(t)
        except Exception as e:
            card["valuation"] = {"error": str(e)}

        # 2. Financials
        try:
            card["financials"] = f.get_financials(t)
        except Exception as e:
            card["financials"] = {"error": str(e)}

        # 3. Closes 250
        try:
            closes = f.get_closes(t, days=250)
            if closes and len(closes) >= 2:
                card["close_now"] = closes[-1]
                card["close_250d_ago"] = closes[0]
                card["return_250d"] = round((closes[-1] - closes[0]) / closes[0] * 100, 2)
                # 60d return
                if len(closes) >= 60:
                    card["return_60d"] = round((closes[-1] - closes[-60]) / closes[-60] * 100, 2)
                # 20d return
                if len(closes) >= 20:
                    card["return_20d"] = round((closes[-1] - closes[-20]) / closes[-20] * 100, 2)
                # max/min in 250d
                card["high_250d"] = max(closes)
                card["low_250d"] = min(closes)
                card["from_high_pct"] = round((closes[-1] - max(closes)) / max(closes) * 100, 2)
            else:
                card["closes_error"] = "insufficient data"
        except Exception as e:
            card["closes_error"] = str(e)

        # 4. Reports
        try:
            reports = f.get_reports(t)
            card["report_count"] = len(reports) if reports else 0
            if reports:
                card["latest_report_date"] = reports[0].get("publishDate", "")
                card["latest_report_org"] = reports[0].get("orgSName", "")
        except Exception as e:
            card["reports_error"] = str(e)

        # 5. News
        try:
            news = f.get_stock_news(t)
            card["news_count"] = len(news) if news else 0
        except Exception as e:
            card["news_error"] = str(e)

        result[t] = card
        time.sleep(0.3)  # rate limit courtesy

    return result

data = fetch_all()
with open("/tmp/value_data.json", "w", encoding="utf-8") as out:
    json.dump(data, out, ensure_ascii=False, indent=2)
print(f"\nDone. {len(data)} stocks saved to /tmp/value_data.json", file=sys.stderr)
