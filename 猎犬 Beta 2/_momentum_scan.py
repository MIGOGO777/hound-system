"""动量分析扫描 — 批量取数+计算+输出"""

import sys, json, math
from datetime import datetime
from hound_system.data.fetcher import HoundFetcher

CODES = [
    "601818","601825","601838","601857","601858","601865","601866","601868","601869","601872",
    "601877","601878","601880","601881","601882","601888","601890","601898","601899","601901",
    "601908","601916","601918","601919","601929","601933","601939","601958","601963","601965",
]

def sma(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n

def ema(vals, n):
    if len(vals) < n:
        return None
    k = 2 / (n + 1)
    result = sum(vals[:n]) / n
    for v in vals[n:]:
        result = v * k + result * (1 - k)
    return result

def calc_rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    gains, losses = 0, 0
    for i in range(-n, 0):
        diff = closes[i] - closes[i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    avg_g = gains / n
    avg_l = losses / n
    if avg_l == 0: return 100
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))

def calc_macd(closes):
    """return (macd_line, signal_line, histogram)"""
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)
    if e12 is None or e26 is None:
        return None, None, None
    macd = e12 - e26
    # signal = ema of macd values
    return macd, None, None

def trend_stage(closes):
    """Determine trend stage: 早期/中期/加速/衰退/下跌"""
    if len(closes) < 60:
        return "数据不足"
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)
    ma10 = sma(closes, 10)
    if ma20 is None or ma60 is None:
        return "数据不足"
    price = closes[-1]
    price_5ago = closes[-6] if len(closes) >= 6 else closes[0]
    price_20ago = closes[-21] if len(closes) >= 21 else closes[0]
    price_60ago = closes[-61] if len(closes) >= 61 else closes[0]

    # Trend direction
    ma20_trend = ma20 - sma(closes[:-10], 20) if len(closes) > 30 else 0

    # % above MA60
    above_ma60 = (price - ma60) / ma60 * 100 if ma60 > 0 else 0

    # Recent return
    ret_5d = (price - price_5ago) / price_5ago * 100
    ret_20d = (price - price_20ago) / price_20ago * 100
    ret_60d = (price - price_60ago) / price_60ago * 100

    # Check for higher highs / higher lows (simplified)
    recent_high = max(closes[-20:])
    high_60 = max(closes[-60:])
    recent_low = min(closes[-20:])

    # Distribution check: lower highs in last 10 days
    last_10 = closes[-10:]
    lower_highs = all(last_10[i] >= last_10[i+1] for i in range(len(last_10)-1))

    # Rate of change acceleration
    roc_20 = ret_20d
    roc_10 = ret_5d

    # Stage logic
    if above_ma60 < -5:
        return "深度下跌"
    elif above_ma60 < 0:
        return "弱势震荡"
    elif above_ma60 < 5 and ret_20d > 0 and ret_5d > 0:
        return "早期回升"
    elif above_ma60 < 15 and ma20 > ma60 and ret_20d > 0:
        return "中期趋势"
    elif above_ma60 >= 15 and ret_5d > 0 and ret_20d > 0:
        # Check acceleration
        if roc_10 > roc_20 * 1.5 and roc_20 > 5:
            return "加速冲顶"
        return "强势主升"
    elif above_ma60 >= 15 and ret_5d < 0:
        return "高位回调"
    elif price < ma20 and ma20 < ma60:
        return "下跌趋势"
    elif price < ma20 and price > ma60:
        return "短期回调"
    else:
        return "震荡整理"

def relative_strength(closes, idx_closes, period=20):
    """相对强度: 个股涨幅 - 指数涨幅"""
    if len(closes) < period + 1 or len(idx_closes) < period + 1:
        return None
    ret_stock = (closes[-1] - closes[-period-1]) / closes[-period-1] * 100
    ret_idx = (idx_closes[-1] - idx_closes[-period-1]) / idx_closes[-period-1] * 100
    return round(ret_stock - ret_idx, 2)

def volume_analysis(hist):
    """量价分析"""
    if not hist or len(hist) < 20:
        return {}

    closes = [r.get("close", 0) for r in hist]
    volumes = [r.get("volume", 0) for r in hist]

    # Volume ratio
    avg_v20 = sum(volumes[-20:]) / 20
    latest_v = volumes[-1]
    vr = latest_v / avg_v20 if avg_v20 > 0 else 1

    # Up volume vs down volume
    up_vol, down_vol = 0, 0
    for i in range(-20, 0):
        if closes[i] > closes[i-1]:
            up_vol += volumes[i]
        else:
            down_vol += volumes[i]
    v_ratio_20 = up_vol / down_vol if down_vol > 0 else float('inf')

    # Volume increasing trend (last 5d vs prior 15d)
    v_5 = sum(volumes[-5:]) / 5
    v_prev_15 = sum(volumes[-20:-5]) / 15
    v_trend = v_5 / v_prev_15 if v_prev_15 > 0 else 1

    return {
        "vol_ratio": round(vr, 2),
        "up_down_vol_ratio_20d": round(v_ratio_20, 2) if v_ratio_20 != float('inf') else "inf",
        "vol_trend_5d_vs_15d": round(v_trend, 2),
    }

def failure_patterns(hist):
    """识别失败形态"""
    if not hist or len(hist) < 30:
        return []
    patterns = []
    closes = [r.get("close", 0) for r in hist]
    highs = [r.get("high", 0) for r in hist]
    lows = [r.get("low", 0) for r in hist]
    volumes = [r.get("volume", 0) for r in hist]

    # 1. Failed breakout: price > previous high but closes below
    if len(closes) >= 10:
        prev_high = max(highs[-15:-5]) if len(highs) >= 15 else 0
        if closes[-1] > prev_high * 0.98 and closes[-1] < prev_high:
            patterns.append("突破失败(近5日上试前高未站上)")

    # 2. Distribution: price up but volume decreasing
    recent_up = closes[-1] > closes[-2] if len(closes) >= 2 else False
    if recent_up and len(volumes) >= 3:
        if volumes[-1] < volumes[-2] < volumes[-3]:
            patterns.append("缩量上涨(量能持续萎缩)")

    # 3. Bearish engulfing / shooting star
    if len(closes) >= 2:
        range_today = highs[-1] - lows[-1]
        body = abs(closes[-1] - hist[-1].get("open", closes[-1]))
        if range_today > 0 and body / range_today < 0.3 and highs[-1] > closes[-1]:
            if closes[-1] < hist[-1].get("open", closes[-1]):
                patterns.append("上影线(高开低走)")

    # 4. High volume reversal
    if len(volumes) >= 5:
        avg_v = sum(volumes[-6:-1]) / 5
        if volumes[-1] > avg_v * 2 and closes[-1] < hist[-1].get("open", closes[-1]):
            patterns.append("放量反转(高量收跌)")

    # 5. Divergence (price making higher highs, RSI making lower highs)
    rsi_vals = []
    for i in range(-20, 0):
        if abs(i) >= 14:
            segment = closes[:i+1] if i < 0 else closes
            if len(segment) >= 15:
                r = calc_rsi(segment, 14)
                rsi_vals.append(r)
    if len(rsi_vals) >= 2:
        if closes[-1] > closes[-5] and rsi_vals[-1] < rsi_vals[-2] if rsi_vals[-1] and rsi_vals[-2] else False:
            patterns.append("顶背离(价创新高RSI走低)")

    return patterns

def check_trap(hist, quote):
    """检查误判类型"""
    traps = []
    if not hist or not quote:
        return traps

    close = hist[-1].get("close", 0)
    open_ = hist[-1].get("open", 0)
    high = hist[-1].get("high", 0)
    low = hist[-1].get("low", 0)
    volume = hist[-1].get("volume", 0)
    name = quote.get("name", "")
    change_pct = quote.get("change_pct", 0)

    # 一字板缺确认
    if open_ == close and close == high and low < high:
        traps.append("一字板|缺确认")

    # 缩量拉升
    if len(hist) >= 5:
        vols = [r.get("volume", 0) for r in hist[-5:]]
        if all(v <= vols[0] * 0.8 for v in vols[1:]) and change_pct > 0:
            traps.append(f"缩量拉升({name})")

    # 高位加速末端
    if len(hist) >= 10:
        ret_10d = (close - hist[-11].get("close", close)) / hist[-11].get("close", 1) * 100
        if ret_10d > 20 and change_pct > 3:
            traps.append("高位加速末端")

    return traps

def compute_momentum(code, fetcher, idx_closes):
    """Compute full momentum analysis for one stock"""
    closes = fetcher.get_closes(code, 130)
    hist = fetcher.get_hist_data(code, days=130)
    quotes = fetcher.get_realtime_quotes([code])
    quote = quotes.get(code, {})

    if not closes or not hist:
        return None

    price = closes[-1]
    name = quote.get("name", "")
    change_pct = quote.get("change_pct", 0)

    # --- Trend analysis ---
    stage = trend_stage(closes)

    # MAs
    ma5 = sma(closes, 5)
    ma10 = sma(closes, 10)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)

    # Above MA
    above_ma60 = (price - ma60) / ma60 * 100 if ma60 and ma60 > 0 else 0
    above_ma20 = (price - ma20) / ma20 * 100 if ma20 and ma20 > 0 else 0

    # --- Relative strength ---
    rs_5d = relative_strength(closes, idx_closes, 5)
    rs_20d = relative_strength(closes, idx_closes, 20)
    rs_60d = relative_strength(closes, idx_closes, 60)

    # --- Return ---
    ret_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
    ret_20d = (closes[-1] - closes[-21]) / closes[-21] * 100 if len(closes) >= 21 else 0
    ret_60d = (closes[-1] - closes[-61]) / closes[-61] * 100 if len(closes) >= 61 else 0

    # --- RSI ---
    rsi_14 = calc_rsi(closes, 14)
    rsi_6 = calc_rsi(closes, 6)

    # --- MACD ---
    macd_line = None
    if len(closes) >= 26:
        e12 = ema(closes, 12)
        e26 = ema(closes, 26)
        if e12 and e26:
            macd_line = e12 - e26
            # signal line approximation
            macd_vals = []
            for i in range(26, len(closes)+1):
                seg = closes[:i]
                e12_i = ema(seg, 12)
                e26_i = ema(seg, 26)
                if e12_i and e26_i:
                    macd_vals.append(e12_i - e26_i)
            if len(macd_vals) >= 9:
                signal_line = sum(macd_vals[-9:]) / 9
                macd_hist = macd_line - signal_line
            else:
                signal_line = 0
                macd_hist = 0
        else:
            signal_line = 0
            macd_hist = 0
    else:
        signal_line = 0
        macd_hist = 0

    # --- Volume ---
    va = volume_analysis(hist)

    # --- Failure patterns ---
    failures = failure_patterns(hist)

    # --- Trap check ---
    traps = check_trap(hist, quote)

    # --- Trend structure or emotional pulse? ---
    # Trend structure: steady uptrend, pullbacks on low vol, breakouts on high vol
    # Emotional pulse: sudden spike, no trend continuity, accelerating without volume

    is_trend_improvement = True
    reasons_trend = []
    reasons_pulse = []

    # Trend structure signals
    if ma10 and ma20 and ma60:
        if ma10 > ma20 > ma60:
            reasons_trend.append("均线多头排列")
        if price > ma20 and ma20 > ma60:
            reasons_trend.append("价格站上中期均线")

    if above_ma60 > 0 and above_ma60 < 30 and ret_20d > 0:
        reasons_trend.append("温和站上MA60趋势健康")

    if ret_20d and ret_60d:
        if 0 < ret_20d < 30 and ret_60d > 0:
            reasons_trend.append("中期涨幅适中未极端")

    # Emotional pulse signals
    if rsi_14 and rsi_14 > 80:
        reasons_pulse.append(f"RSI超买({rsi_14:.0f})")

    if ret_5d and ret_20d:
        if ret_5d > 15:
            reasons_pulse.append(f"短期暴涨({ret_5d:.1f}%)")
        if ret_5d > ret_20d * 2 and ret_20d > 10:
            reasons_pulse.append("加速赶顶")

    if ma10 and ma20 and price:
        if price > ma10 * 1.08:
            reasons_pulse.append("偏离短期均线过大")

    if va.get("vol_ratio", 0) > 3:
        reasons_pulse.append(f"异常放量({va['vol_ratio']}x)")

    if "缩量上涨" in str(failures):
        reasons_pulse.append("价升量缩背离")

    # Verdict
    if len(reasons_pulse) > len(reasons_trend):
        verdict = "情绪脉冲"
        pulse_detail = "; ".join(reasons_pulse)
    elif len(reasons_pulse) == len(reasons_trend) and len(reasons_pulse) > 0:
        verdict = "趋势改善为主+情绪成分"
    else:
        if len(reasons_trend) >= 2:
            verdict = "趋势结构改善"
        else:
            verdict = "待观察(信号不足)"
        pulse_detail = "; ".join(reasons_pulse) if reasons_pulse else "无"

    # --- Stop-loss conditions ---
    stop_loss = None
    if ma20 and price:
        stop_loss_ma20 = round(ma20, 2)
        stop_loss_pct = round((price - ma20) / price * 100, 1)
        if price > ma20:
            stop_loss = {"level": f"MA20={stop_loss_ma20}", "pct_from_now": f"-{stop_loss_pct:.1f}%"}
            # Also consider ma60
            if ma60:
                stop_loss_ma60 = round(ma60, 2)
                stop_loss_ma60_pct = round((price - ma60) / price * 100, 1)
                if stop_loss_ma60_pct > stop_loss_pct:
                    stop_loss["secondary"] = f"MA60={stop_loss_ma60} (-{stop_loss_ma60_pct:.1f}%)"
        else:
            stop_loss = {"level": f"最近低点={round(min(closes[-10:]), 2)}", "pct_from_now": "关注"}

    return {
        "code": code,
        "name": name,
        "price": price,
        "change_pct": change_pct,
        "trend_stage": stage,
        "trend_verdict": verdict,
        "pulse_detail": pulse_detail,
        "reasons_trend": reasons_trend,
        "reasons_pulse": reasons_pulse,
        "ma": {"ma5": round(ma5, 2) if ma5 else None,
               "ma10": round(ma10, 2) if ma10 else None,
               "ma20": round(ma20, 2) if ma20 else None,
               "ma60": round(ma60, 2) if ma60 else None},
        "above_ma": {"ma20": round(above_ma20, 1), "ma60": round(above_ma60, 1)},
        "return": {"5d": round(ret_5d, 1), "20d": round(ret_20d, 1), "60d": round(ret_60d, 1)},
        "rsi": {"rsi14": round(rsi_14, 1) if rsi_14 else None, "rsi6": round(rsi_6, 1) if rsi_6 else None},
        "macd": {"hist": round(macd_hist, 4) if isinstance(macd_hist, (int, float)) else 0},
        "volume": va,
        "relative_strength": {"vs_idx_5d": rs_5d, "vs_idx_20d": rs_20d, "vs_idx_60d": rs_60d},
        "failure_patterns": failures,
        "traps": traps,
        "stop_loss": stop_loss,
    }

def print_card(d):
    """Print one issue card"""
    print(f"\n{'='*70}")
    print(f"【{d['code']} {d['name']}】 现价:{d['price']} ({d['change_pct']:+.2f}%)")
    print(f"{'='*70}")
    print(f"趋势阶段: {d['trend_stage']}")
    print(f"趋势判断: {d['trend_verdict']}")
    if d['pulse_detail'] and d['trend_verdict'] != '趋势结构改善':
        print(f"脉冲信号: {d['pulse_detail']}")
    print(f"相对强度: 5d={d['relative_strength']['vs_idx_5d']}%  20d={d['relative_strength']['vs_idx_20d']}%  60d={d['relative_strength']['vs_idx_60d']}%")
    print(f"均线: MA5={d['ma']['ma5']} MA10={d['ma']['ma10']} MA20={d['ma']['ma20']} MA60={d['ma']['ma60']}")
    print(f"偏离MA20: {d['above_ma']['ma20']}%  偏离MA60: {d['above_ma']['ma60']}%")
    print(f"涨跌幅: 5d={d['return']['5d']}%  20d={d['return']['20d']}%  60d={d['return']['60d']}%")
    print(f"RSI14: {d['rsi']['rsi14']}  RSI6: {d['rsi']['rsi6']}")
    print(f"量比: {d['volume'].get('vol_ratio','-')}  量趋势: {d['volume'].get('vol_trend_5d_vs_15d','-')}")
    print(f"失败形态: {d['failure_patterns'] if d['failure_patterns'] else '无'}")
    print(f"误判检查: {d['traps'] if d['traps'] else '无明显陷阱'}")
    print(f"止损参考: {d['stop_loss']}")

# Main
f = HoundFetcher()
idx_closes = f.get_index_closes("000300", 130)
print(f"CSI300 closes: {len(idx_closes) if idx_closes else 0} days", file=sys.stderr)

results = []
for code in CODES:
    print(f"\n>>> 正在取数: {code}", file=sys.stderr)
    result = compute_momentum(code, f, idx_closes)
    if result:
        results.append(result)
    else:
        print(f"!!! 数据获取失败: {code}", file=sys.stderr)

# Summary
print("\n\n")
print("="*70)
print("【动量扫描汇总】")
print("="*70)
for r in results:
    emoji = "🟢" if r['trend_verdict'] == '趋势结构改善' else "🟡" if '趋势改善' in r['trend_verdict'] else "🔴" if r['trend_verdict'] == '情绪脉冲' else "⚪"
    print(f"{emoji} {r['code']} {r['name']:8s} | {r['trend_stage']:8s} | {r['trend_verdict']} | RS20d={r['relative_strength']['vs_idx_20d']}% | RSI14={r['rsi']['rsi14']}")

print(f"\n总计: {len(results)} 只")
trend_ok = sum(1 for r in results if '趋势结构改善' in r['trend_verdict'])
pulse = sum(1 for r in results if r['trend_verdict'] == '情绪脉冲')
mixed = sum(1 for r in results if '趋势改善' in r['trend_verdict'] and r['trend_verdict'] != '趋势结构改善')
print(f"趋势结构改善: {trend_ok}")
print(f"趋势改善+情绪成分: {mixed}")
print(f"情绪脉冲主导: {pulse}")
