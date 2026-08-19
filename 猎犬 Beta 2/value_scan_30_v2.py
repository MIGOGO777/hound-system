"""688板块30只价值扫描 v2 — 减少串行等待"""
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

def safe(fn, t, *a, **kw):
    try: return fn(t, *a, **kw)
    except: return None

# 1. 估值（腾讯行情，可批量，快）
print("=== 估值 ===", file=sys.stderr)
vals = {}
for t in TICKERS:
    v = safe(f.get_valuation, t)
    vals[t] = v

# 2. 财务（东财，慢，减少延时）
print("=== 财务 ===", file=sys.stderr)
fin = {}
for t in TICKERS:
    fi = safe(f.get_financials, t)
    fin[t] = fi
    sys.stderr.write(f"  {t} done\n"); sys.stderr.flush()

# 3. 收盘价
print("=== K线 ===", file=sys.stderr)
cls = {}
for t in TICKERS:
    c = safe(f.get_closes, t, 60)
    cls[t] = c

# 4. 研报 & 新闻（并行不了，但快）
print("=== 研报 ===", file=sys.stderr)
reps = {}
for t in TICKERS:
    r = safe(f.get_reports, t)
    reps[t] = r
    sys.stderr.write(f"  {t} done\n"); sys.stderr.flush()

print("=== 新闻 ===", file=sys.stderr)
nws = {}
for t in TICKERS:
    n = safe(f.get_stock_news, t)
    nws[t] = n
    sys.stderr.write(f"  {t} done\n"); sys.stderr.flush()

# ── 分析 ──
def judge(t):
    v, fi, c, r, n = vals.get(t), fin.get(t), cls.get(t), reps.get(t), nws.get(t)
    nm = v.get("name","?") if v else "?"
    pe = v.get("pe_ttm") if v else None
    pb = v.get("pb") if v else None
    mc = v.get("mcap_yi") if v else None
    px = v.get("price") if v else None

    # 便宜评分
    cheap, cheap_r = 0, []
    if pe is not None and pe > 0:
        if pe < 15: cheap+=2; cheap_r.append(f"PE={pe:.1f}<15")
        elif pe < 25: cheap+=1; cheap_r.append(f"PE={pe:.1f}<25")
        elif pe > 60: cheap-=1; cheap_r.append(f"PE={pe:.1f}>60偏贵")
        else: cheap_r.append(f"PE={pe:.1f}中性")
    elif pe is not None and pe <= 0:
        cheap_r.append(f"PE={pe:.1f}亏损")

    if pb is not None and pb > 0:
        if pb < 1: cheap+=2; cheap_r.append(f"PB={pb:.2f}破净")
        elif pb < 2: cheap+=1; cheap_r.append(f"PB={pb:.2f}<2")
        elif pb > 5: cheap-=1; cheap_r.append(f"PB={pb:.2f}>5偏贵")
        else: cheap_r.append(f"PB={pb:.2f}中性")

    # 质量评分
    quality, q_r = 0, []
    if fi:
        roe = fi.get("roe"); gm = fi.get("gross_margin")
        ocf = fi.get("op_cashflow_ps"); dr = fi.get("dividend_ratio")
        if roe is not None:
            if roe > 10: quality+=2; q_r.append(f"ROE={roe:.1f}%>10")
            elif roe > 5: quality+=1; q_r.append(f"ROE={roe:.1f}%")
            elif roe > 0: q_r.append(f"ROE={roe:.1f}%偏低")
            else: quality-=2; q_r.append(f"ROE={roe:.1f}%亏损")
        if gm is not None:
            if gm > 40: quality+=1; q_r.append(f"毛利率={gm:.1f}%>40")
            elif gm > 20: q_r.append(f"毛利率={gm:.1f}%")
            else: quality-=1; q_r.append(f"毛利率={gm:.1f}%偏低")
        if ocf is not None:
            if ocf > 0: quality+=1; q_r.append("经营现金流>0")
            else: quality-=1; q_r.append("经营现金流为负")
        if dr is not None and dr > 0: quality+=1; q_r.append(f"分红率={dr:.1f}%")
        fin_rd = fi.get("report_date","?")
    else:
        q_r.append("无财务数据"); fin_rd="?"

    # 趋势
    trend = "无K线数据"
    if c and len(c)>=2:
        p1=c[-1]; p5=c[-6] if len(c)>=6 else c[0]; p20=c[-21] if len(c)>=21 else c[0]
        r5=(p1-p5)/p5*100; r20=(p1-p20)/p20*100
        if r20<-20: trend=f"20日跌{r20:.1f}%加速下跌"; quality-=1
        elif r20<-10: trend=f"20日跌{r20:.1f}%弱势"; quality-=1
        elif r20>10: trend=f"20日涨{r20:.1f}%强势"; quality+=1
        else: trend=f"20日涨跌{r20:.1f}%震荡"
    else: quality-=1

    # 研报覆盖
    rp_note = ""
    if r and len(r)>=3: rp_note=f"研报{len(r)}份"; quality+=1
    elif r: rp_note=f"研报{len(r)}份"
    else: rp_note="无研报"; quality-=1

    # 新闻
    news_sig = ""
    if n:
        txt=" ".join([x.get("title","") for x in n[:5]])
        neg=[kw for kw in["减持","预警","亏损","立案","退市","风险"] if kw in txt]
        pos=[kw for kw in["增持","回购","中标","合同","突破","获批"] if kw in txt]
        if neg: news_sig=f"负面:{','.join(neg[:3])}"; quality-=1
        elif pos: news_sig=f"正面:{','.join(pos[:3])}"; quality+=1
        else: news_sig="中性"
    else: news_sig="无新闻"

    total = cheap + quality

    # 裁决
    if pe is not None and pe < 0:
        if quality <= -2: verdict="便宜在变坏⚠️"; summ="持续亏损+质量恶化，价值毁灭型"
        elif total <= 0: verdict="便宜在变坏⚠️"; summ="亏损且质量承压"
        else: verdict="便宜待验证❓"; summ="亏损但有亮点"
    elif cheap >= 2 and quality >= 1: verdict="便宜没坏✅"; summ="低估+质量尚可，价值洼地"
    elif cheap >= 2 and quality <= 0: verdict="便宜在变坏⚠️"; summ="低估但质量恶化，价值陷阱"
    elif cheap >= 1 and quality >= 2: verdict="便宜没坏✅"; summ="估值合理+质地不错"
    elif cheap >= 0 and quality <= -2: verdict="便宜在变坏⚠️"; summ="质量明显恶化"
    elif cheap <= -1 and quality >= 1: verdict="贵但好公司⭐"; summ="质地好但估值偏贵"
    elif cheap <= -1 and quality <= -1: verdict="贵且差❌"; summ="既不便宜也不好"
    elif total > 1: verdict="便宜没坏✅"; summ="整体偏积极"
    elif total < -1: verdict="便宜在变坏⚠️"; summ="整体偏负面"
    else: verdict="模糊❓"; summ="信号不明确"

    return {
        "code": t, "name": nm, "price": px, "mcap_yi": mc,
        "pe_ttm": pe, "pb": pb, "roe": fi.get("roe") if fi else None,
        "gm": fi.get("gross_margin") if fi else None,
        "ocf": fi.get("op_cashflow_ps") if fi else None,
        "div": fi.get("dividend_ratio") if fi else None,
        "report_date": fin_rd,
        "verdict": verdict, "summary": summ,
        "cheap_score": cheap, "quality_score": quality, "total_score": total,
        "cheap_reasons": "; ".join(cheap_r),
        "quality_notes": "; ".join(q_r),
        "trend": trend, "reports": rp_note, "news": news_sig,
    }

cards = [judge(t) for t in TICKERS]

print("\n\n========== 价值扫描30只 议题卡 ==========\n")
for c in cards:
    print(f"## {c['name']}（{c['code']}）")
    print(f"**裁决**：{c['verdict']}")
    print(f"**摘要**：{c['summary']}")
    print(f"- **估值**：PE_TTM={c['pe_ttm']}  PB={c['pb']}  市值={c['mcap_yi']}亿  收盘价={c['price']}")
    print(f"- **财务**：ROE={c['roe']}%  毛利率={c['gm']}%  经营现金流={c['ocf']}  分红率={c['div']}%  报告期={c['report_date']}")
    print(f"- **趋势**：{c['trend']}")
    print(f"- **关注度**：{c['reports']}")
    print(f"- **新闻信号**：{c['news']}")
    print(f"- **评分**：便宜{c['cheap_score']}  质量{c['quality_score']}  总分{c['total_score']}")
    print()

from collections import Counter
vc = Counter(c['verdict'] for c in cards)
print(f"\n=== 汇总 ===")
for k,v in vc.most_common(): print(f"  {k}: {v}只")
print(f"  总计: {len(cards)}只")

json.dump(cards, open("/tmp/value_30.json","w"), ensure_ascii=False, indent=2, default=str)
