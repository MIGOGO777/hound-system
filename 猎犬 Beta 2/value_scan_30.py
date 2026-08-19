"""688板块30只价值扫描：便宜没坏 or 便宜在变坏？"""
import json, sys, time
from hound_system.data.fetcher import HoundFetcher

TICKERS = [
    "688216","688218","688219","688220","688221","688222","688223",
    "688226","688228","688229","688230","688231","688233","688235",
    "688236","688238","688239","688246","688247","688248","688249",
    "688250","688251","688252","688253","688255","688256","688258",
    "688259","688260"
]

f = HoundFetcher()

def safe_get(fn, ticker, *args, **kwargs):
    try:
        return fn(ticker, *args, **kwargs)
    except Exception as e:
        return None

# 1. Batch get valuations (腾讯行情可以批量)
print("=== 批量获取估值 ===", file=sys.stderr)
valuations = {}
for t in TICKERS:
    v = safe_get(f.get_valuation, t)
    valuations[t] = v
    if v:
        print(f"  {t}: {v.get('name','?')} PE={v.get('pe_ttm','?')} PB={v.get('pb','?')} 市值={v.get('mcap_yi','?')}亿", file=sys.stderr)
    time.sleep(0.3)

# 2. Financials
print("\n=== 批量获取财务 ===", file=sys.stderr)
fin_data = {}
for t in TICKERS:
    fi = safe_get(f.get_financials, t)
    fin_data[t] = fi
    time.sleep(0.5)

# 3. Closes (price trend)
print("\n=== 批量获取价格趋势 ===", file=sys.stderr)
closes_data = {}
for t in TICKERS:
    c = safe_get(f.get_closes, t, 60)
    closes_data[t] = c
    time.sleep(0.3)

# 4. Reports (analyst coverage)
print("\n=== 批量获取研报 ===", file=sys.stderr)
reports_data = {}
for t in TICKERS:
    r = safe_get(f.get_reports, t)
    reports_data[t] = r
    time.sleep(0.5)

# 5. News
print("\n=== 批量获取新闻 ===", file=sys.stderr)
news_data = {}
for t in TICKERS:
    n = safe_get(f.get_stock_news, t)
    news_data[t] = n
    time.sleep(0.5)

# ── 分析 ─────────────────────────────────────────────────────────
def judge_value(ticker):
    """判断便宜没坏还是便宜在变坏"""
    v = valuations.get(ticker)
    fi = fin_data.get(ticker)
    cls = closes_data.get(ticker)
    reps = reports_data.get(ticker)
    nws = news_data.get(ticker)

    name = v.get("name", "?") if v else "?"
    pe = v.get("pe_ttm") if v else None
    pb = v.get("pb") if v else None
    mcap = v.get("mcap_yi") if v else None

    # ── 便宜度 ──
    cheap_score = 0
    cheap_reasons = []

    # PE判断（科创板合理PE区间宽，用行业感知）
    if pe is not None and pe > 0:
        if pe < 15:
            cheap_score += 2
            cheap_reasons.append(f"PE={pe:.1f}<15")
        elif pe < 25:
            cheap_score += 1
            cheap_reasons.append(f"PE={pe:.1f}<25")
        elif pe > 50:
            cheap_score -= 1
            cheap_reasons.append(f"PE={pe:.1f}>50（偏贵）")
        else:
            cheap_reasons.append(f"PE={pe:.1f}（中性）")
    elif pe is not None and pe < 0:
        cheap_reasons.append(f"PE={pe:.1f}（亏损）")

    if pb is not None and pb > 0:
        if pb < 1.0:
            cheap_score += 2
            cheap_reasons.append(f"PB={pb:.2f}<1（破净）")
        elif pb < 2:
            cheap_score += 1
            cheap_reasons.append(f"PB={pb:.2f}<2")
        elif pb > 5:
            cheap_score -= 1
            cheap_reasons.append(f"PB={pb:.2f}>5（偏贵）")
        else:
            cheap_reasons.append(f"PB={pb:.2f}（中性）")

    # ── 质量 ──
    quality_score = 0
    quality_notes = []

    if fi:
        roe = fi.get("roe")
        gm = fi.get("gross_margin")
        ocf = fi.get("op_cashflow_ps")
        dr = fi.get("dividend_ratio")

        if roe is not None:
            if roe > 10:
                quality_score += 2
                quality_notes.append(f"ROE={roe:.1f}%>10")
            elif roe > 5:
                quality_score += 1
                quality_notes.append(f"ROE={roe:.1f}%")
            elif roe > 0:
                quality_notes.append(f"ROE={roe:.1f}%（偏低）")
            else:
                quality_score -= 2
                quality_notes.append(f"ROE={roe:.1f}%（亏损）")

        if gm is not None:
            if gm > 40:
                quality_score += 1
                quality_notes.append(f"毛利率={gm:.1f}%>40")
            elif gm > 20:
                quality_notes.append(f"毛利率={gm:.1f}%")
            else:
                quality_score -= 1
                quality_notes.append(f"毛利率={gm:.1f}%（偏低）")

        if ocf is not None:
            if ocf > 0:
                quality_score += 1
                quality_notes.append(f"经营现金流>0")
            else:
                quality_score -= 1
                quality_notes.append(f"经营性现金流为负")

        if dr is not None and dr > 0:
            quality_score += 1
            quality_notes.append(f"分红率={dr:.1f}%")
    else:
        quality_notes.append("无财务数据")

    # ── 趋势（动量辅助判断变坏） ──
    trend_note = ""
    if cls and len(cls) >= 2:
        p1 = cls[-1]
        p5 = cls[-6] if len(cls) >= 6 else cls[0]
        p20 = cls[-21] if len(cls) >= 21 else cls[0]
        ret_5d = (p1 - p5) / p5 * 100
        ret_20d = (p1 - p20) / p20 * 100
        if ret_20d < -20:
            trend_note = f"20日跌{ret_20d:.1f}%（加速下跌⚠️）"
            quality_score -= 1
        elif ret_20d < -10:
            trend_note = f"20日跌{ret_20d:.1f}%（弱势）"
            quality_score -= 1
        elif ret_20d > 10:
            trend_note = f"20日涨{ret_20d:.1f}%（强势）"
            quality_score += 1
        else:
            trend_note = f"20日涨跌{ret_20d:.1f}%（震荡）"
    else:
        trend_note = "无K线数据"

    # ── 研报覆盖（机构关注度） ──
    rep_note = ""
    if reps and len(reps) >= 3:
        rep_note = f"近{len(reps)}份研报"
        quality_score += 1
    elif reps:
        rep_note = f"仅{len(reps)}份研报"
    else:
        rep_note = "无近期研报"
        quality_score -= 1

    # ── 新闻线索 ──
    news_signal = ""
    if nws:
        # 找负面关键词
        neg_kw = ["减持","预警","亏损","立案","调查","退市","风险提示","st"]
        pos_kw = ["增持","回购","中标","合同","订单","增长","突破","获批"]
        all_text = " ".join([n.get("title","") for n in nws[:5]])
        neg_hits = [kw for kw in neg_kw if kw in all_text]
        pos_hits = [kw for kw in pos_kw if kw in all_text]
        if neg_hits:
            news_signal = f"负面: {','.join(neg_hits[:3])}"
            quality_score -= 1
        elif pos_hits:
            news_signal = f"正面: {','.join(pos_hits[:3])}"
            quality_score += 1
        else:
            news_signal = "中性/无关键信号"
    else:
        news_signal = "无新闻"

    # ── 综合裁决 ──
    total = cheap_score + quality_score

    if pe is not None and pe < 0:
        # 亏损股：便宜但可能价值毁灭
        if quality_score <= -2:
            verdict = "便宜在变坏 ⚠️"
            summary = "持续亏损+质量恶化，价值毁灭型"
        elif total <= 0:
            verdict = "便宜在变坏 ⚠️"
            summary = "亏损且质量承压"
        else:
            verdict = "便宜待验证 ❓"
            summary = "亏损但有亮点（看拐点）"
    elif cheap_score >= 2 and quality_score >= 1:
        verdict = "便宜没坏 ✅"
        summary = "低估+质量尚可，价值洼地"
    elif cheap_score >= 2 and quality_score <= 0:
        verdict = "便宜在变坏 ⚠️"
        summary = "低估但质量在恶化，价值陷阱"
    elif cheap_score >= 1 and quality_score >= 2:
        verdict = "便宜没坏 ✅"
        summary = "估值合理偏低+质地不错"
    elif cheap_score >= 0 and quality_score <= -2:
        verdict = "便宜在变坏 ⚠️"
        summary = "质量明显恶化"
    elif cheap_score <= -1 and quality_score >= 1:
        verdict = "贵但好公司 ⭐"
        summary = "质地好但估值偏贵"
    elif cheap_score <= -1 and quality_score <= -1:
        verdict = "贵且差 ❌"
        summary = "既不便宜也不好"
    elif total > 1:
        verdict = "便宜没坏 ✅"
        summary = "整体偏积极"
    elif total < -1:
        verdict = "便宜在变坏 ⚠️"
        summary = "整体偏负面"
    else:
        verdict = "模糊 ❓"
        summary = "信号不明确，需进一步验证"

    return {
        "code": ticker,
        "name": name,
        "price": v.get("price") if v else None,
        "mcap_yi": mcap,
        "pe_ttm": pe,
        "pb": pb,
        "verdict": verdict,
        "summary": summary,
        "cheap_score": cheap_score,
        "quality_score": quality_score,
        "total_score": total,
        "cheap_reasons": "; ".join(cheap_reasons),
        "quality_notes": "; ".join(quality_notes),
        "trend": trend_note,
        "reports": rep_note,
        "news": news_signal,
        "roe": fi.get("roe") if fi else None,
        "gm": fi.get("gross_margin") if fi else None,
        "ocf": fi.get("op_cashflow_ps") if fi else None,
        "div": fi.get("dividend_ratio") if fi else None,
        "report_date": fi.get("report_date") if fi else None,
        "fin_raw": fi,
    }


cards = []
for t in TICKERS:
    card = judge_value(t)
    cards.append(card)
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"【{card['name']} ({card['code']}】 verdict={card['verdict']}", file=sys.stderr)
    print(f"  价格={card['price']} 市值={card['mcap_yi']}亿", file=sys.stderr)
    print(f"  PE={card['pe_ttm']} PB={card['pb']}", file=sys.stderr)
    print(f"  ROE={card['roe']}% 毛利率={card['gm']}%", file=sys.stderr)
    print(f"  经营现金流={card['ocf']} 分红率={card['div']}%", file=sys.stderr)
    print(f"  {card['cheap_reasons']}", file=sys.stderr)
    print(f"  {card['quality_notes']}", file=sys.stderr)
    print(f"  趋势={card['trend']}", file=sys.stderr)
    print(f"  研报={card['reports']}", file=sys.stderr)
    print(f"  新闻={card['news']}", file=sys.stderr)
    print(f"  裁决: {card['verdict']} — {card['summary']}", file=sys.stderr)
    sys.stderr.flush()

# ── 输出最终卡片 ──
print("\n\n========== 价值扫描30只 议题卡 ==========\n")

for c in cards:
    print(f"## {c['name']}（{c['code']}）")
    print(f"**裁决**：{c['verdict']}")
    print(f"**摘要**：{c['summary']}")
    print(f"- **估值**：PE_TTM={c['pe_ttm']}  PB={c['pb']}  市值={c['mcap_yi']}亿  收盘价={c['price']}")
    print(f"- **财务**：ROE={c['roe']}%  毛利率={c['gm']}%  经营现金流/股={c['ocf']}  分红率={c['div']}%  报告期={c.get('report_date','?')}")
    print(f"- **趋势**：{c['trend']}")
    print(f"- **关注度**：{c['reports']}")
    print(f"- **新闻信号**：{c['news']}")
    print(f"- **便宜评分**：{c['cheap_score']}  **质量评分**：{c['quality_score']}  **总分**：{c['total_score']}")
    print()

# ── 统计 ──
from collections import Counter
vc = Counter(c['verdict'] for c in cards)
print(f"\n=== 汇总 ===")
for k, v in vc.most_common():
    print(f"  {k}: {v}只")
print(f"  总计: {len(cards)}只")

# 输出JSON供后续使用
with open("/tmp/value_scan_30.json", "w") as jf:
    json.dump(cards, jf, ensure_ascii=False, indent=2, default=str)
print(f"\nJSON已保存到 /tmp/value_scan_30.json", file=sys.stderr)
