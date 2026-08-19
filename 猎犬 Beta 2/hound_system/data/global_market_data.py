"""全球市场行情轻量 adapter。

参考 simonlin1212/global-stock-data 的 US/HK 数据路线（新浪/腾讯/东财 push2/Yahoo），
自研轻量 adapter。不直接依赖或引入 global-stock-data 项目代码。

覆盖范围：
- 美股/港股：新浪财经 + 腾讯财经 + 东财 push2 行情
- 其他市场（JP/KR/DE/TW）：Yahoo chart v8 fallback，不保证覆盖
- 未上市/退市：如实标注，不编造

约束：
- 零鉴权，仅用 requests
- 只做客观行情补全，不判断投资价值
- 本 adapter 可能使用东财 push2 作为行情 quote fallback；这不同于资金镜头已禁用的
  push2his/push2 资金流路径。行情 fallback 只做客观价格补全，失败可降级，
  不参与资金判断。
"""

import re
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# ── 英国富时指数 / 德国DAX / 法国CAC / 日本日经 / 韩国KOSPI / 台湾加权
# 通过Yahoo ticker后缀映射

# ── 市场常量 ──────────────────────────────────────────────────────────────────

MARKET_INFO: dict[str, dict] = {
    "US": {"currency": "USD", "country": "美国", "yahoo_suffix": ""},
    "HK": {"currency": "HKD", "country": "香港", "yahoo_suffix": ".HK"},
    "JP": {"currency": "JPY", "country": "日本", "yahoo_suffix": ".T"},
    "KR": {"currency": "KRW", "country": "韩国", "yahoo_suffix": ".KS"},
    "DE": {"currency": "EUR", "country": "德国", "yahoo_suffix": ".DE"},
    "TW": {"currency": "TWD", "country": "台湾", "yahoo_suffix": ".TW"},
    "UK": {"currency": "GBP", "country": "英国", "yahoo_suffix": ".L"},
    "FR": {"currency": "EUR", "country": "法国", "yahoo_suffix": ".PA"},
    "IT": {"currency": "EUR", "country": "意大利", "yahoo_suffix": ".MI"},
    "CA": {"currency": "CAD", "country": "加拿大", "yahoo_suffix": ".TO"},
    "AU": {"currency": "AUD", "country": "澳大利亚", "yahoo_suffix": ".AX"},
    "IN": {"currency": "INR", "country": "印度", "yahoo_suffix": ".NS"},
}

# 东财 MktNum → 市场名映射
EM_MKT_MAP: dict[int, str] = {105: "US", 106: "US", 107: "US", 116: "HK"}

# ── 辅助函数 ──────────────────────────────────────────────────────────────────


def _now_str() -> str:
    """返回当前时间字符串（用于 as_of 字段）"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_quote(symbol: str, market: str) -> dict:
    """返回一个空的行情 dict（所有字段为 None）"""
    m = MARKET_INFO.get(market, {"currency": "?", "country": "?"})
    return {
        "company": None, "ticker": symbol, "market": market,
        "country": m["country"], "currency": m["currency"],
        "price": None, "change_pct": None,
        "market_cap": None, "pe": None, "pb": None,
        "source": None, "as_of": None,
        "coverage_status": "data_gap",
        "missing": [],
    }


# ── 搜索 ──────────────────────────────────────────────────────────────────────


def search_global_stock(query: str, count: int = 10) -> list[dict]:
    """搜索全球股票（中英文名均可）

    优先走东财 search（参考 global-stock-data 的搜股路线，自研 adapter），失败走 SearXNG fallback。

    返回:
        [{company, ticker, market, country, source}, ...]
    """
    results = _search_eastmoney(query, count)
    if results:
        return results

    # SearXNG fallback
    try:
        results = _search_searxng(query)
    except Exception as e:
        logger.warning("SearXNG 搜索失败 [%s]: %s", query, e)

    return results or []


def _search_eastmoney(query: str, count: int = 10) -> list[dict]:
    """东财股票搜索"""
    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {
        "input": query, "type": 14,
        "token": "D43BF722C8E33BDC906FB84D85E326E8",
        "count": count,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        d = r.json()
        suggestions = d.get("QuotationCodeTable", {}).get("Data") or []
    except Exception as e:
        logger.warning("东财搜索异常: %s", e)
        return []

    results = []
    for s in suggestions:
        mkt = s.get("MktNum", "")
        market = EM_MKT_MAP.get(int(mkt)) if mkt else None
        if not market:
            continue
        mint_code = s.get("Code", "")
        results.append({
            "company": s.get("Name", ""),
            "ticker": mint_code,
            "market": market,
            "country": MARKET_INFO.get(market, {}).get("country", ""),
            "source": "eastmoney_search",
        })
    return results


def _search_searxng(query: str) -> list[dict]:
    """SearXNG fallback 搜索 — 尝试通过关键词搜到 ticker"""
    import urllib.parse
    q = urllib.parse.quote(f"{query} stock ticker")
    url = f"http://localhost:4000/search?q={q}&format=json&language=zh-CN"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    results_raw = data.get("results", [])
    if not results_raw:
        return []
    # SearXNG 只能返回文本结果，无法直接提取结构化 ticker 信息。
    # 返回一个示意结果，让调用方知道搜到了内容但无法直接解析。
    return [{
        "company": query,
        "ticker": None,
        "market": None,
        "country": None,
        "source": "searxng_search",
        "note": f"found {len(results_raw)} search results, ticker not parsed automatically",
    }]


# ── 美股/港股行情 ──────────────────────────────────────────────────────────────


def get_us_hk_quote(symbol: str, market: Optional[str] = None) -> dict:
    """获取美股/港股实时/延时行情

    Args:
        symbol: 美股纯字母 ticker（如 AAPL/TSLA）或港股5位数字代码（如 00700）
        market: "US" | "HK"，不传则自动推断

    返回:
        {company, ticker, market, country, currency, price, change_pct,
         market_cap, pe, pb, source, as_of, coverage_status, missing}
    """
    # ── 市场推断 ─────────────────────────────────────────────────────
    if market is None:
        market = "HK" if symbol.isdigit() and len(symbol) == 5 else "US"
    if market not in ("US", "HK"):
        return _empty_quote(symbol, market)

    base = _empty_quote(symbol, market)
    missing: list[str] = []
    result = None
    source = None

    if market == "US":
        # 美股优先走新浪（含 PE/market_cap）
        try:
            q = _us_quote_sina(symbol)
            if q and q.get("price") is not None:
                result = q
                source = "sina"
        except Exception as e:
            missing.append(f"sina:{e}")
            logger.debug("新浪美股行情失败 [%s]: %s", symbol, e)

        # 备选腾讯（字段更全，含 PB）
        if not result or result.get("price") is None:
            try:
                q = _us_quote_tencent(symbol)
                if q and q.get("price") is not None:
                    result = q
                    source = "tencent"
            except Exception as e:
                missing.append(f"tencent:{e}")
                logger.debug("腾讯美股行情失败 [%s]: %s", symbol, e)

        # 最后东财 push2
        if not result or result.get("price") is None:
            try:
                # 尝试 105(NASDAQ), 106(NYSE) 两种前缀
                for prefix in (105, 106, 107):
                    q = _em_push2_quote(symbol, prefix)
                    if q and q.get("price") is not None:
                        result = q
                        source = "eastmoney_push2"
                        break
            except Exception as e:
                missing.append(f"eastmoney:{e}")
                logger.debug("东财美股行情失败 [%s]: %s", symbol, e)

    else:  # HK
        # 港股优先走腾讯（字段最全 78 字段）
        try:
            q = _hk_quote_tencent(symbol)
            if q and q.get("price") is not None:
                result = q
                source = "tencent"
        except Exception as e:
            missing.append(f"tencent:{e}")
            logger.debug("腾讯港股行情失败 [%s]: %s", symbol, e)

        # 备选新浪
        if not result or result.get("price") is None:
            try:
                q = _hk_quote_sina(symbol)
                if q and q.get("price") is not None:
                    result = q
                    source = "sina"
            except Exception as e:
                missing.append(f"sina:{e}")
                logger.debug("新浪港股行情失败 [%s]: %s", symbol, e)

        # 最后东财 push2
        if not result or result.get("price") is None:
            try:
                q = _em_push2_quote(symbol, 116)
                if q and q.get("price") is not None:
                    result = q
                    source = "eastmoney_push2"
            except Exception as e:
                missing.append(f"eastmoney:{e}")
                logger.debug("东财港股行情失败 [%s]: %s", symbol, e)

    if not result or result.get("price") is None:
        base["missing"] = missing if missing else ["all_sources_failed"]
        return base

    m = MARKET_INFO[market]
    merged = {
        "company": result.get("name") or result.get("name_en") or symbol,
        "ticker": symbol,
        "market": market,
        "country": m["country"],
        "currency": m["currency"],
        "price": result.get("price"),
        "change_pct": result.get("change_pct"),
        "market_cap": result.get("market_cap"),
        "pe": result.get("pe"),
        "pb": result.get("pb"),
        "source": source,
        "as_of": result.get("timestamp") or _now_str(),
        "coverage_status": "covered",
        "missing": missing if missing else [],
    }
    return merged


def _us_quote_sina(ticker: str) -> dict | None:
    """新浪美股行情"""
    url = f"https://hq.sinajs.cn/list=gb_{ticker.lower()}"
    r = requests.get(url, headers={"Referer": "https://finance.sina.com.cn/",
                                    "User-Agent": UA}, timeout=10)
    r.encoding = "gbk"
    m = re.search(r'"(.+)"', r.text)
    if not m:
        return None
    fields = m.group(1).split(",")
    if len(fields) < 30:
        return None
    return {
        "name": fields[0],
        "price": float(fields[1]) if fields[1] else None,
        "change_pct": float(fields[2]) if fields[2] else None,
        "timestamp": fields[3],
        "high_52w": float(fields[8]) if fields[8] else 0,
        "low_52w": float(fields[9]) if fields[9] else 0,
        "market_cap": float(fields[12]) if fields[12] else None,
        "eps": float(fields[13]) if fields[13] else None,
        "pe": float(fields[14]) if fields[14] else None,
    }


def _us_quote_tencent(ticker: str) -> dict | None:
    """腾讯美股行情 — 71字段"""
    url = f"https://qt.gtimg.cn/q=us{ticker.upper()}"
    r = requests.get(url, timeout=10)
    r.encoding = "gbk"
    m = re.search(r'"(.+)"', r.text)
    if not m:
        return None
    fields = m.group(1).split("~")
    if len(fields) < 50:
        return None
    return {
        "name": fields[1],
        "name_en": fields[27],
        "price": float(fields[3]) if fields[3] else None,
        "change_pct": float(fields[32]) if fields[32] else None,
        "market_cap": float(fields[44]) if fields[44] else None,  # 亿美元
        "pe": float(fields[53]) if fields[53] else None,
        "pb": float(fields[56]) if fields[56] else None,
        "timestamp": fields[30],
    }


def _hk_quote_tencent(code: str) -> dict | None:
    """腾讯港股行情 — 78字段"""
    url = f"https://qt.gtimg.cn/q=r_hk{code}"
    r = requests.get(url, timeout=10)
    r.encoding = "gbk"
    m = re.search(r'"(.+)"', r.text)
    if not m:
        return None
    fields = m.group(1).split("~")
    if len(fields) < 50:
        return None
    return {
        "name": fields[1],
        "name_en": fields[2],
        "price": float(fields[3]) if fields[3] else None,
        "change_pct": float(fields[32]) if fields[32] else None,
        "pe": float(fields[39]) if fields[39] else None,
        "pb": float(fields[56]) if fields[56] else None,
        "market_cap": float(fields[44]) if fields[44] else None,  # 亿港元
        "timestamp": fields[30],
    }


def _hk_quote_sina(code: str) -> dict | None:
    """新浪港股行情 — 25字段"""
    url = f"https://hq.sinajs.cn/list=rt_hk{code}"
    r = requests.get(url, headers={"Referer": "https://finance.sina.com.cn/",
                                    "User-Agent": UA}, timeout=10)
    r.encoding = "gbk"
    m = re.search(r'"(.+)"', r.text)
    if not m:
        return None
    fields = m.group(1).split(",")
    if len(fields) < 15:
        return None
    return {
        "name": fields[1],
        "name_en": fields[0],
        "price": float(fields[6]) if fields[6] else None,
        "change_pct": float(fields[8]) if fields[8] else None,
        "timestamp": _now_str(),
    }


def _em_push2_quote(ticker_or_code: str, secid_prefix: int) -> dict | None:
    """东财 push2 实时行情 — 美股+港股统一"""
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"{secid_prefix}.{ticker_or_code}",
        "fields": "f43,f44,f45,f46,f47,f48,f55,f57,f58,f59,f60,f170",
    }
    r = requests.get(url, params=params, timeout=10)
    d = r.json().get("data")
    if not d:
        return None
    dec = d.get("f59", 3)
    divisor = 10 ** dec

    def _p(key):
        v = d.get(key)
        if v is None or v == "-":
            return None
        return round(v / divisor, dec)

    return {
        "name": d.get("f58"),
        "price": _p("f43"),
        "change_pct": round(d["f170"] / 100, 2) if d.get("f170") is not None else None,
        "prev_close": _p("f60"),
        "timestamp": _now_str(),
    }


# ── Yahoo fallback（其他市场） ──────────────────────────────────────────────


def _yahoo_chart_quote(symbol: str) -> dict | None:
    """通过 Yahoo chart v8（零 crumb）获取最新价"""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "1d"}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=15)
        r.raise_for_status()
        d = r.json()
        result = d.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})
        quotes = result.get("indicators", {}).get("quote", [{}])[0]
        if not quotes or not quotes.get("close") or not quotes["close"][0]:
            return None
        price = float(quotes["close"][0])
        prev_close = meta.get("chartPreviousClose")
        change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else None
        return {
            "price": price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "timestamp": _now_str(),
        }
    except Exception as e:
        logger.debug("Yahoo chart 失败 [%s]: %s", symbol, e)
        return None


# ── 全球上市映射解析 ──────────────────────────────────────────────────────────


def resolve_global_listing(company_name: str,
                            country_hint: Optional[str] = None) -> dict:
    """解析公司的全球上市映射

    流程:
        1. 如果是中/英/日/韩文公司名 → 先搜全球 → 找到股票就取行情
        2. 搜不到 → coverage_status="not_covered"，不做映射硬凑

    返回:
        {company, country, listing_status, ticker, market, currency, price,
         change_pct, market_cap, pe, pb, source, as_of, coverage_status, missing,
         mapping_type}
    """
    base: dict = {
        "company": company_name,
        "country": country_hint,
        "listing_status": "unknown",
        "ticker": None,
        "market": None,
        "currency": None,
        "price": None,
        "change_pct": None,
        "market_cap": None,
        "pe": None,
        "pb": None,
        "source": None,
        "as_of": None,
        "coverage_status": "not_covered",
        "missing": [],
        "mapping_type": "no_mapping",
    }

    # Step 1: 搜索
    search_results = search_global_stock(company_name)
    if not search_results:
        base["coverage_status"] = "not_covered"
        base["listing_status"] = "unknown"
        return base

    # 只要第一个有效结果
    hit = search_results[0]
    ticker = hit.get("ticker")
    market = hit.get("market")

    if not ticker or not market:
        base["coverage_status"] = "not_covered"
        base["listing_status"] = "unknown"
        return base

    # Step 2: 取行情
    if market in ("US", "HK"):
        quote = get_us_hk_quote(ticker, market)
    else:
        # 其他市场走 Yahoo fallback
        yahoo_sym = f"{ticker}{MARKET_INFO.get(market, {}).get('yahoo_suffix', '')}"
        q = _yahoo_chart_quote(yahoo_sym) if yahoo_sym else None
        if q:
            m = MARKET_INFO.get(market, {"currency": "?", "country": "?"})
            quote = {
                "company": hit.get("company", company_name),
                "ticker": yahoo_sym,
                "market": market,
                "country": m["country"],
                "currency": m["currency"],
                "price": q["price"],
                "change_pct": q["change_pct"],
                "market_cap": None,
                "pe": None,
                "pb": None,
                "source": "yahoo_chart",
                "as_of": q["timestamp"],
                "coverage_status": "covered",
                "missing": ["market_cap", "pe", "pb"],
            }
        else:
            quote = _empty_quote(ticker, market)
            quote["coverage_status"] = "data_gap"
            quote["missing"] = ["quote_failed"]

    if quote.get("coverage_status") == "covered":
        base["listing_status"] = "listed"
    else:
        base["listing_status"] = "listed" if ticker else "unknown"

    base.update(quote)
    if base.get("company") is None or base["company"] == ticker:
        base["company"] = company_name
    base["mapping_type"] = "direct"
    base["country"] = country_hint or base.get("country")
    return base
