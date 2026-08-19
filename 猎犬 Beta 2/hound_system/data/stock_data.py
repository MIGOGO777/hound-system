"""猎犬系统数据层 -- 基于 a-stock-data

从 a-stock-data SKILL.md 提取的 HTTP API 数据接口。
数据源优先级: mootdx/腾讯(不封IP) > 新浪/巨潮/同花顺 > 东财(需限流)。

所有东财接口统一走 em_get() 做串行限流+会话复用，避免被封 IP。
"""

from __future__ import annotations

import json
import logging
import math
import random
import re
import time
import urllib.request
from dataclasses import dataclass

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ── 全局常量 ──────────────────────────────────────────────────────────────────

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
REPORT_API = "https://reportapi.eastmoney.com/report/list"
HSGT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "Chrome/117.0.0.0 Safari/537.36"
    ),
    "Host": "data.hexin.cn",
    "Referer": "https://data.hexin.cn/",
}

# ── 东财防封: 全局节流 + 会话复用 ────────────────────────────────────────────
# 东财系 HTTP 接口有风控: 每秒>5次/单IP并发>=10/1分钟>=200次 -> 临时封 IP。
# 所有 eastmoney.com 请求一律走 em_get(): 串行限流 + 复用 Keep-Alive 会话。
EM_SESSION = requests.Session()
EM_SESSION.headers.update({"User-Agent": UA})
EM_MIN_INTERVAL = 1.0  # 两次东财请求最小间隔(秒); 批量筛选建议调大到 1.5~2
_em_last_call = [0.0]  # 模块级上次请求时间戳


# ── 市场前缀 ──────────────────────────────────────────────────────────────────

def get_prefix(code: str) -> str:
    """6位代码 -> 市场前缀 (sh/sz/bj)

    Args:
        code: 6位纯数字股票代码

    Returns:
        'sh' / 'sz' / 'bj'
    """
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    else:
        return "sz"


def _normalize_code(code: str) -> str:
    """归一化股票代码为纯6位数字

    支持格式: 688017 / SH688017 / sh688017 / 688017.SH / 688017.sh
    """
    code = code.strip()
    # 去掉前缀 SH/SZ/BJ/sh/sz/bj
    if len(code) > 6 and code[:2].upper() in ("SH", "SZ", "BJ"):
        code = code[2:]
    # 去掉后缀 .SH/.SZ/.BJ/.sh/.sz/.bj
    if len(code) > 6 and code[6:7] == ".":
        code = code[:6]
    return code[:6]


# ── 东财统一请求入口 ──────────────────────────────────────────────────────────

def em_get(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
    **kwargs,
) -> requests.Response:
    """东财统一请求入口: 自动节流 + 复用 session + 默认 UA。

    所有 eastmoney.com 接口都应通过它请求，避免高频被封 IP。
    """
    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return EM_SESSION.get(
            url, params=params, headers=headers, timeout=timeout, **kwargs
        )
    finally:
        _em_last_call[0] = time.time()


# ── 东财数据中心统一查询 ──────────────────────────────────────────────────────

def eastmoney_datacenter(
    report_name: str,
    columns: str = "ALL",
    filter_str: str = "",
    page_size: int = 50,
    sort_columns: str = "",
    sort_types: str = "-1",
) -> list[dict]:
    """东财数据中心统一查询 -- 龙虎榜/解禁/融资融券/大宗交易/股东户数/分红共用。

    Args:
        report_name: 报表名称 (如 RPTA_WEB_RZRQ_GGMX)
        columns: 查询字段, 默认 ALL
        filter_str: 筛选条件
        page_size: 每页条数
        sort_columns: 排序字段
        sort_types: 排序方向, '-1' 降序 '1' 升序

    Returns:
        数据记录列表, 失败返回空列表
    """
    params = {
        "reportName": report_name,
        "columns": columns,
        "filter": filter_str,
        "pageNumber": "1",
        "pageSize": str(page_size),
        "sortColumns": sort_columns,
        "sortTypes": sort_types,
        "source": "WEB",
        "client": "WEB",
    }
    try:
        r = em_get(DATACENTER_URL, params=params, timeout=15)
        d = r.json()
        if d.get("result") and d["result"].get("data"):
            return d["result"]["data"]
    except Exception as e:
        logger.warning("东财 datacenter 请求失败 [%s]: %s", report_name, e)
    return []


# ── 腾讯实时行情 ──────────────────────────────────────────────────────────────

def _f(s: str) -> float:
    """快速 float 解析，空字符串返回 0"""
    return float(s) if s else 0


def tencent_quote(codes: list[str]) -> dict[str, dict]:
    """批量拉取腾讯财经实时行情 (不封IP)。

    Args:
        codes: 股票代码列表, 如 ["688017", "300476", "002463"]
               也支持指数: ["000001", "000300", "399006"]
               也支持ETF: ["510050", "510300"]

    Returns:
        {code: {name, price, pe_ttm, pb, mcap_yi, ...}, ...}
    """
    try:
        prefixed = []
        for c in codes:
            c = _normalize_code(c)
            prefixed.append(f"{get_prefix(c)}{c}")

        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode("gbk")

        result = {}
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            result[code] = {
                "name": vals[1],
                "price": _f(vals[3]),
                "last_close": _f(vals[4]),
                "open": _f(vals[5]),
                "change_amt": _f(vals[31]),
                "change_pct": _f(vals[32]),
                "high": _f(vals[33]),
                "low": _f(vals[34]),
                "amount_wan": _f(vals[37]),
                "turnover_pct": _f(vals[38]),
                "pe_ttm": _f(vals[39]),
                "amplitude_pct": _f(vals[43]),
                "mcap_yi": _f(vals[44]),
                "float_mcap_yi": _f(vals[45]),
                "pb": _f(vals[46]),
                "limit_up": _f(vals[47]),
                "limit_down": _f(vals[48]),
                "vol_ratio": _f(vals[49]),
                "pe_static": _f(vals[52]),
            }
        return result
    except Exception as e:
        logger.warning("腾讯行情请求失败: %s", e)
        return {}


# ── mootdx K线（通达信，不封IP）────────────────────────────────────────────────

def mootdx_index_kline(code: str, days: int = 120) -> pd.DataFrame:
    """通过 mootdx（通达信）获取指数日线 K 线。

    用于动量技能算相对强度（个股 vs 指数）。不封 IP。
    常用指数：000300沪深300 / 399006创业板指 / 000001上证 / 000905中证500

    Args:
        code: 6位指数代码
        days: 获取最近 N 个交易日

    Returns:
        DataFrame, 列: open, close, high, low, vol, amount, datetime；失败空表
    """
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market="std")
        df = client.index_bars(symbol=code, category=9, offset=days)
        if df is None or df.empty:
            return pd.DataFrame()
        cols = [c for c in ["open", "close", "high", "low", "vol", "amount", "datetime"] if c in df.columns]
        return df[cols]
    except Exception as e:
        logger.warning("mootdx 指数K线请求失败 [%s]: %s", code, e)
        return pd.DataFrame()


def mootdx_kline(code: str, days: int = 120) -> pd.DataFrame:
    """通过 mootdx（通达信）获取日线 K 线数据。

    优先使用，不封 IP。

    Args:
        code: 6位股票代码
        days: 获取最近 N 个交易日

    Returns:
        DataFrame, 列: open, close, high, low, vol, amount, datetime
    """
    try:
        code = _normalize_code(code)
        from mootdx.quotes import Quotes
        client = Quotes.factory(market="std")
        df = client.bars(symbol=code, category=4, offset=days)
        if df is None or df.empty:
            return pd.DataFrame()
        return df[["open", "close", "high", "low", "vol", "amount", "datetime"]]
    except Exception as e:
        logger.warning("mootdx K线请求失败 [%s]: %s", code, e)
        return pd.DataFrame()


# ── 百度股市通 K线 (带MA) ────────────────────────────────────────────────────

def baidu_kline_with_ma(code: str, start_time: str = "") -> dict:
    """百度股市通K线 -- 独有能力: 返回时自带 ma5/ma10/ma20 均价。

    Args:
        code: 6位股票代码
        start_time: 起始时间, 格式 YYYY-MM-DD

    Returns:
        {"keys": [...], "rows": [...]}
    """
    try:
        code = _normalize_code(code)
        url = "https://finance.pae.baidu.com/selfselect/getstockquotation"
        params = {
            "all": "1",
            "isIndex": "false",
            "isBk": "false",
            "isBlock": "false",
            "isFutures": "false",
            "isStock": "true",
            "newFormat": "1",
            "group": "quotation_kline_ab",
            "finClientType": "pc",
            "code": code,
            "start_time": start_time,
            "ktype": "1",
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.finance-web.v1+json",
            "Origin": "https://gushitong.baidu.com",
            "Referer": "https://gushitong.baidu.com/",
        }
        r = requests.get(url, params=params, headers=headers, timeout=10)
        d = r.json()
        result = d.get("Result", {})
        if not isinstance(result, dict):
            logger.warning("百度K线 API 返回非预期格式 [%s]: ResultCode=%s", code, d.get("ResultCode"))
            return {"keys": [], "rows": []}
        md = result.get("newMarketData", {})
        keys = md.get("keys", [])
        rows = md.get("marketData", "").split(";")
        return {"keys": keys, "rows": rows}
    except Exception as e:
        logger.warning("百度K线请求失败 [%s]: %s", code, e)
        return {"keys": [], "rows": []}


# ── 个股资金流向 (分钟级) ─────────────────────────────────────────────────────

def eastmoney_fund_flow_minute(code: str) -> list[dict]:
    """个股资金流向 (分钟级, 当日盘中)。

    Args:
        code: 6位股票代码

    Returns:
        [{time, main_net, small_net, mid_net, large_net, super_net}, ...]
        单位: 元
    """
    try:
        code = _normalize_code(code)
        secid = f"1.{code}" if code.startswith("6") else f"0.{code}"
        url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        params = {
            "secid": secid,
            "klt": 1,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
        }
        headers = {
            "User-Agent": UA,
            "Referer": "https://quote.eastmoney.com/",
            "Origin": "https://quote.eastmoney.com",
        }
        r = em_get(url, params=params, headers=headers, timeout=10)
        d = r.json()

        rows = []
        for line in d.get("data", {}).get("klines", []):
            parts = line.split(",")
            if len(parts) >= 6:
                rows.append({
                    "time": parts[0],
                    "main_net": float(parts[1]),
                    "small_net": float(parts[2]),
                    "mid_net": float(parts[3]),
                    "large_net": float(parts[4]),
                    "super_net": float(parts[5]),
                })
        return rows
    except Exception as e:
        logger.warning("push2 资金流请求失败 [%s]: %s", code, e)
        return []


# ── 个股资金流 (120日, 日级) ──────────────────────────────────────────────────

def stock_fund_flow_120d(code: str) -> list[dict]:
    """个股资金流 (日级, 最近120个交易日)。

    Args:
        code: 6位股票代码

    Returns:
        [{date, main_net, small_net, mid_net, large_net, super_net}, ...]
        单位: 元
    """
    try:
        code = _normalize_code(code)
        market_code = 1 if code.startswith("6") else 0
        url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        params = {
            "secid": f"{market_code}.{code}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "lmt": "120",
        }
        headers = {
            "User-Agent": UA,
            "Referer": "https://quote.eastmoney.com/",
            "Origin": "https://quote.eastmoney.com",
        }
        r = em_get(url, params=params, headers=headers, timeout=15)
        d = r.json()
        klines = d.get("data", {}).get("klines", [])

        rows = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 7:
                rows.append({
                    "date": parts[0],
                    "main_net": float(parts[1]) if parts[1] != "-" else 0,
                    "small_net": float(parts[2]) if parts[2] != "-" else 0,
                    "mid_net": float(parts[3]) if parts[3] != "-" else 0,
                    "large_net": float(parts[4]) if parts[4] != "-" else 0,
                    "super_net": float(parts[5]) if parts[5] != "-" else 0,
                })
        return rows
    except Exception as e:
        logger.warning("push2his 资金流请求失败 [%s]: %s", code, e)
        return []


# ── 融资融券 ──────────────────────────────────────────────────────────────────

def margin_trading(code: str, page_size: int = 30) -> list[dict]:
    """融资融券明细 (日级)。

    Args:
        code: 6位股票代码
        page_size: 返回条数

    Returns:
        [{date, rzye(融资余额), rzmre(融资买入), rqye(融券余额), ...}, ...]
    """
    try:
        code = _normalize_code(code)
        data = eastmoney_datacenter(
            "RPTA_WEB_RZRQ_GGMX",
            filter_str=f'(SCODE="{code}")',
            page_size=page_size,
            sort_columns="DATE",
            sort_types="-1",
        )
        rows = []
        for row in data:
            rows.append({
                "date": str(row.get("DATE", ""))[:10],
                "rzye": row.get("RZYE", 0),         # 融资余额(元)
                "rzmre": row.get("RZMRE", 0),       # 融资买入额
                "rzche": row.get("RZCHE", 0),       # 融资偿还额
                "rqye": row.get("RQYE", 0),         # 融券余额(元)
                "rqmcl": row.get("RQMCL", 0),       # 融券卖出量
                "rqchl": row.get("RQCHL", 0),       # 融券偿还量
                "rzrqye": row.get("RZRQYE", 0),     # 融资融券余额合计
            })
        return rows
    except Exception as e:
        logger.warning("融资融券请求失败 [%s]: %s", code, e)
        return []


# ── 大宗交易 ──────────────────────────────────────────────────────────────────

def block_trade(code: str, page_size: int = 20) -> list[dict]:
    """大宗交易记录。

    Args:
        code: 6位股票代码
        page_size: 返回条数

    Returns:
        [{date, price, vol, amount, buyer, seller, premium_pct}, ...]
    """
    try:
        code = _normalize_code(code)
        data = eastmoney_datacenter(
            "RPT_DATA_BLOCKTRADE",
            filter_str=f'(SECURITY_CODE="{code}")',
            page_size=page_size,
            sort_columns="TRADE_DATE",
            sort_types="-1",
        )
        rows = []
        for row in data:
            close = row.get("CLOSE_PRICE") or 0
            deal_price = row.get("DEAL_PRICE") or 0
            premium = ((deal_price / close - 1) * 100) if close else 0
            rows.append({
                "date": str(row.get("TRADE_DATE", ""))[:10],
                "price": deal_price,
                "close": close,
                "premium_pct": round(premium, 2),
                "vol": row.get("DEAL_VOLUME", 0),
                "amount": row.get("DEAL_AMT", 0),
                "buyer": row.get("BUYER_NAME", ""),
                "seller": row.get("SELLER_NAME", ""),
            })
        return rows
    except Exception as e:
        logger.warning("大宗交易请求失败 [%s]: %s", code, e)
        return []


# ── 北向资金实时 ──────────────────────────────────────────────────────────────

def hsgt_realtime() -> pd.DataFrame:
    """沪深股通当日实时分钟流向 (含集合竞价 09:10-15:00)。

    Returns:
        DataFrame, 字段: time, hgt_yi(沪股通累计净买入/亿), sgt_yi(深股通累计净买入/亿)
    """
    try:
        url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
        r = requests.get(url, headers=HSGT_HEADERS, timeout=10)
        d = r.json()
        times = d.get("time", [])
        hgt = d.get("hgt", [])
        sgt = d.get("sgt", [])

        n = len(times)
        return pd.DataFrame({
            "time": times,
            "hgt_yi": hgt[:n] + [None] * (n - len(hgt)),
            "sgt_yi": sgt[:n] + [None] * (n - len(sgt)),
        })
    except Exception as e:
        logger.warning("北向资金请求失败: %s", e)
        return pd.DataFrame(columns=["time", "hgt_yi", "sgt_yi"])


# ── 东财个股基本面 ────────────────────────────────────────────────────────────

def eastmoney_stock_info(code: str) -> dict:
    """东财个股基本面信息。

    Args:
        code: 6位股票代码

    Returns:
        {code, name, industry, total_shares, float_shares, mcap, float_mcap, list_date, price}
    """
    try:
        code = _normalize_code(code)
        market_code = 1 if code.startswith("6") else 0
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "fltt": "2",
            "invt": "2",
            "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
            "secid": f"{market_code}.{code}",
        }
        headers = {"User-Agent": UA}
        r = em_get(url, params=params, headers=headers, timeout=10)
        d = r.json().get("data", {})
        return {
            "code": d.get("f57", ""),
            "name": d.get("f58", ""),
            "industry": d.get("f127", ""),
            "total_shares": d.get("f84", 0),       # 总股本(股)
            "float_shares": d.get("f85", 0),       # 流通股(股)
            "mcap": d.get("f116", 0),              # 总市值(元)
            "float_mcap": d.get("f117", 0),        # 流通市值(元)
            "list_date": str(d.get("f189", "")),   # 上市日期 YYYYMMDD
            "price": d.get("f43", 0),
        }
    except Exception as e:
        logger.warning("东财个股信息请求失败 [%s]: %s", code, e)
        return {}


# ── 完整估值 ──────────────────────────────────────────────────────────────────

def full_valuation(code: str) -> dict:
    """单票完整估值分析 (腾讯行情 + 估值指标)。

    Args:
        code: 6位股票代码

    Returns:
        {name, price, mcap_yi, pe_ttm, pb, pe_fwd, cagr_pct, peg, digest_years, ...}
    """
    try:
        code = _normalize_code(code)

        # 1. 腾讯实时行情
        prefix = get_prefix(code)
        url = f"https://qt.gtimg.cn/q={prefix}{code}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode("gbk")
        vals = data.split('"')[1].split("~")
        price = float(vals[3]) if vals[3] else 0
        mcap = float(vals[44]) if vals[44] else 0
        pe_ttm = float(vals[39]) if vals[39] else 0
        pb = float(vals[46]) if vals[46] else 0

        # 2. 尝试获取同花顺一致预期 (可选)
        eps_cur = eps_next = None
        analyst_count = 0
        try:
            df = ths_eps_forecast(code)
            if not df.empty and len(df.columns) >= 3:
                for i, row in df.iterrows():
                    if i == 0:
                        eps_cur = float(row.iloc[2]) if pd.notna(row.iloc[2]) else None
                        analyst_count = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0
                    elif i == 1:
                        eps_next = float(row.iloc[2]) if pd.notna(row.iloc[2]) else None
        except Exception as e:
            logger.debug("同花顺一致预期获取失败 [%s]: %s", code, e)

        # 3. 估值指标
        pe_fwd = price / eps_cur if eps_cur else float("inf")
        cagr = (eps_next / eps_cur - 1) if (eps_cur and eps_next) else 0
        peg = pe_fwd / (cagr * 100) if cagr > 0 else float("inf")
        digest = (
            math.log(pe_fwd / 30) / math.log(1 + cagr)
            if pe_fwd > 30 and cagr > 0 else 0
        )

        return {
            "name": vals[1] if len(vals) > 1 else "",
            "price": price,
            "mcap_yi": mcap,
            "pe_ttm": pe_ttm,
            "pb": pb,
            "eps_cur": eps_cur,
            "eps_next": eps_next,
            "pe_fwd": round(pe_fwd, 1) if eps_cur else None,
            "cagr_pct": round(cagr * 100, 0) if cagr else None,
            "peg": round(peg, 2) if peg != float("inf") else None,
            "digest_years": round(digest, 1),
            "analyst_count": analyst_count,
        }
    except Exception as e:
        logger.warning("完整估值请求失败 [%s]: %s", code, e)
        return {}


# ── 辅助: 同花顺一致预期EPS ──────────────────────────────────────────────────

def ths_eps_forecast(code: str) -> pd.DataFrame:
    """同花顺机构一致预期EPS (直连 basic.10jqka.com.cn)。

    Args:
        code: 6位股票代码

    Returns:
        DataFrame: 年度, 预测机构数, 最小值, 均值, 最大值
    """
    try:
        from io import StringIO

        code = _normalize_code(code)
        url = f"https://basic.10jqka.com.cn/new/{code}/worth.html"
        headers = {
            "User-Agent": UA,
            "Referer": "https://basic.10jqka.com.cn/",
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = "gbk"
        dfs = pd.read_html(StringIO(r.text))
        for df in dfs:
            cols = [str(c) for c in df.columns]
            if any("每股收益" in c or "均值" in c for c in cols):
                return df
        return dfs[0] if dfs else pd.DataFrame()
    except Exception as e:
        logger.debug("同花顺一致预期请求失败 [%s]: %s", code, e)
        return pd.DataFrame()


# ── 个股板块归属 ──────────────────────────────────────────────────────────────

def eastmoney_concept_blocks(code: str) -> dict:
    """个股所属板块/概念归属 (东财 slist, 一次请求拿全)。

    Args:
        code: 6位股票代码

    Returns:
        {total, boards: [{name, code, change_pct, lead_stock}], concept_tags: [板块名...]}
    """
    try:
        code = _normalize_code(code)
        market_code = 1 if code.startswith("6") else 0
        params = {
            "fltt": "2", "invt": "2",
            "secid": f"{market_code}.{code}",
            "spt": "3", "pi": "0", "pz": "200", "po": "1",
            "fields": "f12,f14,f3,f128",
        }
        headers = {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}
        r = em_get("https://push2.eastmoney.com/api/qt/slist/get",
                   params=params, headers=headers, timeout=15)
        d = r.json()

        diff = (d.get("data") or {}).get("diff") or {}
        items = diff.values() if isinstance(diff, dict) else diff
        boards = []
        for it in items:
            boards.append({
                "name": it.get("f14", ""),
                "code": it.get("f12", ""),
                "change_pct": it.get("f3", ""),
                "lead_stock": it.get("f128", ""),
            })
        return {
            "total": len(boards),
            "boards": boards,
            "concept_tags": [b["name"] for b in boards],
        }
    except Exception as e:
        logger.warning("东财板块归属请求失败 [%s]: %s", code, e)
        return {"total": 0, "boards": [], "concept_tags": []}


# ── 股东户数变化 ──────────────────────────────────────────────────────────────

def holder_num_change(code: str, page_size: int = 10) -> list[dict]:
    """股东户数变化 (季度级)。

    Args:
        code: 6位股票代码
        page_size: 返回条数

    Returns:
        [{date, holder_num, change_num, change_ratio, avg_shares}]
    """
    try:
        code = _normalize_code(code)
        data = eastmoney_datacenter(
            "RPT_HOLDERNUMLATEST",
            filter_str=f'(SECURITY_CODE="{code}")',
            page_size=page_size,
            sort_columns="END_DATE", sort_types="-1",
        )
        rows = []
        for row in data:
            rows.append({
                "date": str(row.get("END_DATE", ""))[:10],
                "holder_num": row.get("HOLDER_NUM", 0),
                "change_num": row.get("HOLDER_NUM_CHANGE", 0),
                "change_ratio": row.get("HOLDER_NUM_RATIO", 0),
                "avg_shares": row.get("AVG_FREE_SHARES", 0),
            })
        return rows
    except Exception as e:
        logger.warning("股东户数请求失败 [%s]: %s", code, e)
        return []


# ── 研报列表 ──────────────────────────────────────────────────────────────────

def eastmoney_reports(code: str, max_pages: int = 5) -> list[dict]:
    """拉取指定股票的研报列表。

    Args:
        code: 6位股票代码
        max_pages: 最大翻页数

    Returns:
        [{title, publishDate, orgSName, emRatingName, ...}]
    """
    try:
        code = _normalize_code(code)
        all_records = []
        for page in range(1, max_pages + 1):
            params = {
                "industryCode": "*", "pageSize": "100", "industry": "*",
                "rating": "*", "ratingChange": "*",
                "beginTime": "2000-01-01", "endTime": "2030-01-01",
                "pageNo": str(page), "fields": "", "qType": "0",
                "orgCode": "", "code": code, "rcode": "",
                "p": str(page), "pageNum": str(page), "pageNumber": str(page),
            }
            r = em_get(REPORT_API, params=params,
                       headers={"Referer": "https://data.eastmoney.com/"}, timeout=30)
            d = r.json()
            rows = d.get("data") or []
            if not rows:
                break
            all_records.extend(rows)
            if page >= (d.get("TotalPage", 1) or 1):
                break
        return all_records
    except Exception as e:
        logger.warning("研报列表请求失败 [%s]: %s", code, e)
        return []


# ── 个股新闻 ──────────────────────────────────────────────────────────────────

def eastmoney_stock_news(code: str, page_size: int = 20) -> list[dict]:
    """东财个股新闻 (JSONP 接口)。

    Args:
        code: 6位股票代码
        page_size: 返回条数

    Returns:
        [{title, content, time, source, url}]
    """
    try:
        code = _normalize_code(code)
        cb = "jQuery_news"
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        inner_params = json.dumps({
            "uid": "",
            "keyword": code,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default",
                      "pageIndex": 1, "pageSize": page_size, "preTag": "", "postTag": ""}},
        }, separators=(',', ':'))
        params = {"cb": cb, "param": inner_params}
        headers = {"User-Agent": UA, "Referer": "https://so.eastmoney.com/"}
        r = em_get(url, params=params, headers=headers, timeout=15)

        text = r.text
        json_str = text[text.index("(") + 1 : text.rindex(")")]
        d = json.loads(json_str)

        rows = []
        articles = d.get("result", {}).get("cmsArticleWebOld", []) or []
        for a in articles:
            rows.append({
                "title": re.sub(r'<[^>]+>', '', a.get("title", "")),
                "content": re.sub(r'<[^>]+>', '', a.get("content", ""))[:200],
                "time": a.get("date", ""),
                "source": a.get("mediaName", ""),
                "url": a.get("url", ""),
            })
        return rows
    except Exception as e:
        logger.warning("个股新闻请求失败 [%s]: %s", code, e)
        return []


# ── 全市场股票列表（通达信，不封IP）──────────────────────────────────────────────

# A股个股代码前缀（按通达信市场码区分）：1=沪市 0=深市
_A_STOCK_PREFIX = {
    1: ("600", "601", "603", "605", "688"),       # 沪：主板 + 科创
    0: ("000", "001", "002", "003", "300", "301"),  # 深：主板 + 创业
}


def get_stock_list() -> list[dict]:
    """通过 mootdx（通达信）获取全 A 股个股列表。

    不封 IP。原始返回混入指数/债券/基金，按个股代码前缀过滤。
    北交所(8/4开头)不纳入。

    Returns:
        [{"code": "600000", "name": "浦发银行"}, ...]，失败返回 []
    """
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market="std")
        result: list[dict] = []
        for market, prefixes in _A_STOCK_PREFIX.items():
            df = client.stocks(market=market)
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                code = str(row["code"])
                if code[:3] in prefixes:
                    # mootdx 名称尾部可能带 \x00 填充，需清理
                    name = str(row["name"]).replace("\x00", "").strip()
                    result.append({"code": code, "name": name})
        return result
    except Exception as e:
        logger.warning("全市场股票列表请求失败: %s", e)
        return []


# ── 财务质量数据（东财财报，需限流；季度更新可缓存）──────────────────────────────

def get_financials(code: str) -> dict:
    """获取个股财务质量数据（东财财报）。

    走 em_get 限流。财报季度更新，调用方建议缓存。
    覆盖价值技能核心需求：ROE / 现金流 / 毛利率 / 分红。

    Args:
        code: 6位股票代码

    Returns:
        {report_date, roe, gross_margin, eps, bps, op_cashflow_ps,
         revenue, net_profit, revenue_yoy, profit_yoy,
         dividend_ratio, dividend_date} 或 {}（失败/无数据）
    """
    try:
        code = _normalize_code(code)
        result: dict = {}

        # 1. 业绩主表：ROE/毛利率/现金流/营收净利
        perf = eastmoney_datacenter(
            "RPT_LICO_FN_CPD",
            filter_str=f'(SECURITY_CODE="{code}")',
            page_size=1,
            sort_columns="REPORTDATE",
            sort_types="-1",
        )
        if perf:
            d = perf[0]
            result.update({
                "report_date": str(d.get("REPORTDATE", ""))[:10],
                "roe": d.get("WEIGHTAVG_ROE"),
                "gross_margin": d.get("XSMLL"),
                "eps": d.get("BASIC_EPS"),
                "bps": d.get("BPS"),
                "op_cashflow_ps": d.get("MGJYXJJE"),
                "revenue": d.get("TOTAL_OPERATE_INCOME"),
                "net_profit": d.get("PARENT_NETPROFIT"),
                "revenue_yoy": d.get("YSTZ"),
                "profit_yoy": d.get("SJLTZ"),
            })

        # 2. 分红表：最新股息率
        bonus = eastmoney_datacenter(
            "RPT_SHAREBONUS_DET",
            filter_str=f'(SECURITY_CODE="{code}")',
            page_size=8,
            sort_columns="REPORT_DATE",
            sort_types="-1",
        )
        for b in bonus:
            if b.get("DIVIDENT_RATIO") is not None:
                result["dividend_ratio"] = b.get("DIVIDENT_RATIO")
                result["dividend_date"] = str(b.get("REPORT_DATE", ""))[:10]
                break

        return result
    except Exception as e:
        logger.warning("财务质量数据请求失败 [%s]: %s", code, e)
        return {}


# ── 套利技能数据源 ────────────────────────────────────────────────────────────
# 三类硬数据：集思录可转债(需登录cookie) / 东财机构调研 / 东财AH溢价。


class JisiluCookieError(RuntimeError):
    """集思录未登录或 cookie 已失效。

    与其他取数失败不同：这个异常**必须向上传播**，让 agent 通知 sui
    去本地 Chrome 登录 jisilu.cn，而不是静默降级（Builder #12 失败显性化）。
    """


# ── Chrome cookie 解密（Linux，零第三方数据依赖）────────────────────────────────
# 抄 browser_cookie3 的 Linux Chrome v10/v11 解密逻辑，自带实现不引入该库。
# 依赖 secretstorage(读 keyring) + pycryptodome(AES)，均为系统级库非数据 wrapper。

_CHROME_COOKIE_PATHS = [
    "~/.config/google-chrome/Default/Cookies",
    "~/.config/google-chrome/Default/Network/Cookies",
]


def _get_chrome_safe_storage_key() -> bytes:
    """从系统 keyring 取 Chrome Safe Storage 密钥，派生 AES key。

    Chrome v11 cookie 用 keyring 里的 "Chrome Safe Storage" 口令，
    经 PBKDF2(SHA1, 1 iter, salt=b'saltysalt') 派生 16 字节 AES key。
    取不到 keyring 时回退到 Chrome 默认口令 'peanuts'(v10)。
    """
    from hashlib import pbkdf2_hmac

    password = b"peanuts"  # v10 默认；v11 会被下面的 keyring 覆盖
    try:
        import secretstorage

        conn = secretstorage.dbus_init()
        collection = secretstorage.get_default_collection(conn)
        for item in collection.get_all_items():
            if item.get_label() == "Chrome Safe Storage":
                password = item.get_secret()
                break
    except Exception as e:
        logger.warning("读取 keyring 失败，回退默认口令: %s", e)

    return pbkdf2_hmac("sha1", password, b"saltysalt", 1, dklen=16)


def _decrypt_chrome_value(encrypted: bytes, key: bytes) -> str:
    """解密单个 Chrome cookie 值（v10/v11 = AES-128-CBC）。"""
    from Crypto.Cipher import AES

    if not encrypted or encrypted[:3] not in (b"v10", b"v11"):
        # 未加密（旧格式）或空值，直接当明文
        return encrypted.decode("utf-8", "ignore") if encrypted else ""

    iv = b" " * 16
    payload = encrypted[3:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(payload)
    # 去 PKCS7 padding
    pad = decrypted[-1]
    if 1 <= pad <= 16:
        decrypted = decrypted[:-pad]
    # Chrome v10+ 在明文前加了 32 字节 SHA256 域名哈希，跳过
    return decrypted[32:].decode("utf-8", "ignore")


def load_chrome_cookie(domain: str = "jisilu.cn") -> dict[str, str]:
    """读取本地 Chrome 中指定域名的已登录 cookie（明文 dict）。

    依赖用户已在本地 Chrome 登录该站点。Chrome 运行时会锁库，
    故复制到临时文件再读。读不到返回空 dict，由上层决定如何通知。

    Args:
        domain: cookie 域名关键字，如 'jisilu.cn'

    Returns:
        {cookie名: cookie值}，失败返回 {}
    """
    import os
    import shutil
    import sqlite3
    import tempfile

    src = None
    for p in _CHROME_COOKIE_PATHS:
        ep = os.path.expanduser(p)
        if os.path.exists(ep):
            src = ep
            break
    if not src:
        logger.warning("未找到 Chrome Cookies 文件")
        return {}

    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False).name
    try:
        shutil.copy2(src, tmp)
        key = _get_chrome_safe_storage_key()
        conn = sqlite3.connect(tmp)
        try:
            rows = conn.execute(
                "SELECT name, encrypted_value, value FROM cookies "
                "WHERE host_key LIKE ?",
                (f"%{domain}%",),
            ).fetchall()
        finally:
            conn.close()

        result: dict[str, str] = {}
        for name, enc, plain in rows:
            if plain:
                result[name] = plain
            elif enc:
                try:
                    result[name] = _decrypt_chrome_value(enc, key)
                except Exception as e:
                    logger.warning("解密 cookie [%s] 失败: %s", name, e)
        return result
    except Exception as e:
        logger.warning("读取 Chrome cookie 失败: %s", e)
        return {}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── 集思录可转债（需登录 cookie）──────────────────────────────────────────────

JISILU_CB_URL = "https://www.jisilu.cn/data/cbnew/cb_list_new/"


def get_convertible_bonds() -> list[dict]:
    """获取集思录全市场可转债列表（含转股溢价率）。

    需本地 Chrome 已登录 jisilu.cn：未登录最多 30 条，登录后约 300+ 全量。
    cookie 缺失或失效时**抛 JisiluCookieError**（不静默降级），
    让 agent 通知 sui 去登录（Builder #12）。

    Returns:
        [{bond_code, bond_name, stock_code, stock_name, price,
          premium_rt, convert_value, convert_price, pb, dblow, ...}]

    Raises:
        JisiluCookieError: 未登录 / cookie 失效（拿到 <=30 条）
    """
    cookies = load_chrome_cookie("jisilu.cn")
    if not cookies or "kbzw__user_login" not in cookies:
        raise JisiluCookieError(
            "集思录未登录：请在本地 Chrome 打开 jisilu.cn 登录后重试"
        )

    headers = {
        "User-Agent": UA,
        "Referer": "https://www.jisilu.cn/data/cbnew/",
        "X-Requested-With": "XMLHttpRequest",
    }
    url = f"{JISILU_CB_URL}?___jsl=LST___t={int(time.time() * 1000)}"
    try:
        r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        rows = r.json().get("rows", [])
    except Exception as e:
        raise JisiluCookieError(f"集思录请求失败（可能 cookie 失效）：{e}") from e

    if len(rows) <= 30:
        raise JisiluCookieError(
            f"集思录 cookie 已失效（只拿到 {len(rows)} 条，应有 300+）："
            "请在本地 Chrome 重新登录 jisilu.cn"
        )

    result: list[dict] = []
    for row in rows:
        c = row.get("cell", {})
        result.append({
            "bond_code": c.get("bond_id"),
            "bond_name": c.get("bond_nm"),
            "stock_code": c.get("stock_id"),
            "stock_name": c.get("stock_nm"),
            "price": c.get("price"),                # 转债价格
            "premium_rt": c.get("premium_rt"),      # 转股溢价率%
            "convert_value": c.get("convert_value"),  # 转股价值
            "convert_price": c.get("convert_price"),  # 转股价
            "pb": c.get("pb"),                      # 正股市净率
            "dblow": c.get("dblow"),                # 双低值(价格+溢价率)
            "ytm_rt": c.get("ytm_rt"),              # 到期收益率
            "rating": c.get("rating_cd"),           # 评级
        })
    return result


# ── 东财机构调研 ──────────────────────────────────────────────────────────────

def get_institution_research(code: str = "", page_size: int = 50) -> list[dict]:
    """获取机构调研记录（东财 RPT_ORG_SURVEYNEW）。

    传 code 查单只；不传查全市场最近调研（按调研日期降序）。
    调研热度=注意力早期信号，配合股价未动可识别认知错配。

    Args:
        code: 6位股票代码，空则查全市场最新
        page_size: 返回条数

    Returns:
        [{code, name, survey_date, org_num, receive_way, investigators}]
    """
    code = _normalize_code(code) if code else ""
    filter_str = f'(SECURITY_CODE="{code}")' if code else ""
    data = eastmoney_datacenter(
        "RPT_ORG_SURVEYNEW",
        filter_str=filter_str,
        page_size=page_size,
        sort_columns="RECEIVE_START_DATE",
        sort_types="-1",
    )
    result: list[dict] = []
    for d in data:
        result.append({
            "code": d.get("SECURITY_CODE"),
            "name": d.get("SECURITY_NAME_ABBR"),
            "survey_date": str(d.get("RECEIVE_START_DATE", ""))[:10],
            "org_num": d.get("NUM"),               # 参与调研机构家数
            "receive_way": d.get("RECEIVE_WAY_EXPLAIN"),
            "investigators": d.get("INVESTIGATORS"),
        })
    return result


# ── 东财 AH 溢价 ──────────────────────────────────────────────────────────────

AH_PUSH2_URL = "https://push2.eastmoney.com/api/qt/clist/get"


def get_ah_premium(page_size: int = 200) -> list[dict]:
    """获取全市场 AH 股溢价率（东财 push2 行情接口，不需登录）。

    溢价率 f3 = A股价/(H股价*汇率) - 1，正=A股贵于H股。
    用于跨市场定价差套利：A 股相对 H 股折价（溢价率为负）时可能错配。

    Args:
        page_size: 返回条数（AH股总数约150只）

    Returns:
        [{a_code, h_code, name, premium_rt, a_price, h_price}]
    """
    params = {
        "pn": "1", "pz": str(page_size), "po": "1", "np": "1",
        "fltt": "2", "invt": "2",
        "fid": "f193",
        "fs": "b:DLMK0101",  # AH股板块
        "fields": "f12,f14,f3,f186,f187,f188,f191,f193",
    }
    try:
        r = em_get(AH_PUSH2_URL, params=params, timeout=15)
        diff = r.json().get("data", {}).get("diff", [])
    except Exception as e:
        logger.warning("AH 溢价请求失败: %s", e)
        return []

    result: list[dict] = []
    for d in diff:
        result.append({
            "h_code": d.get("f12"),       # H股代码
            "h_name": d.get("f14"),       # H股名
            "premium_rt": d.get("f3"),    # AH溢价率%
            "a_code": d.get("f191"),      # A股代码
            "name": d.get("f193"),        # A股名
            "a_price": d.get("f186"),     # A股价
            "h_price": d.get("f188"),     # H股价(港元)
        })
    return result
