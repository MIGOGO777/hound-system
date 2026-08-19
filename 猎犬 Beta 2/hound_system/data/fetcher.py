"""猎犬系统数据获取器

封装多个数据源，提供统一接口。
底层使用 stock_data.py 的 HTTP API（不封IP），替代已废弃的 akshare。
"""

from __future__ import annotations
from datetime import date, datetime
from dataclasses import dataclass, field
import logging
import os
import json

logger = logging.getLogger(__name__)


# ── 模拟数据 ──────────────────────────────────────────────────────────────────

_MOCK_STOCK_LIST: list[dict] = [
    {"code": "000001", "name": "平安银行"},
    {"code": "000002", "name": "万科A"},
    {"code": "600519", "name": "贵州茅台"},
    {"code": "000858", "name": "五粮液"},
    {"code": "601318", "name": "中国平安"},
]


# ── 数据获取器 ──────────────────────────────────────────────────────────────────


@dataclass
class HoundFetcher:
    """猎犬系统数据获取器

    提供统一的数据访问接口，支持实时数据和历史数据。
    底层使用 stock_data.py 的 HTTP API，无需 akshare。

    Usage::

        fetcher = HoundFetcher()
        stocks = fetcher.get_stock_list()
        quotes = fetcher.get_realtime_quotes(["000001", "600519"])
    """

    cache_dir: str = "data/cache"
    _sd: object | None = field(default=None, init=False, repr=False)
    _sd_available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        self._init_sources()

    def _init_sources(self):
        """延迟导入 stock_data，失败时静默降级"""
        try:
            from hound_system.data import stock_data as sd
            self._sd = sd
            self._sd_available = True
            logger.info("stock_data 数据源就绪")
        except ImportError:
            self._sd_available = False
            logger.warning("stock_data 未安装，使用模拟数据")

    # ── 股票列表 ────────────────────────────────────────────────────────────────

    def get_stock_list(self) -> list[dict]:
        """获取A股股票列表

        优先 mootdx 拉全市场真实列表（不封IP），失败降级模拟数据。

        Returns:
            [{"code": "000001", "name": "平安银行"}, ...]
        """
        if not self._sd_available:
            return list(_MOCK_STOCK_LIST)

        try:
            stocks = self._sd.get_stock_list()
            if stocks:
                return stocks
            logger.warning("全市场列表为空，降级模拟数据")
            return list(_MOCK_STOCK_LIST)
        except Exception as e:
            logger.warning("获取股票列表失败，降级模拟数据: %s", e)
            return list(_MOCK_STOCK_LIST)

    # ── 实时行情 ────────────────────────────────────────────────────────────────

    def get_realtime_quotes(self, tickers: list[str]) -> dict[str, dict]:
        """批量获取实时行情

        Args:
            tickers: 股票代码列表

        Returns:
            {ticker: {name, price, change_pct, ...}, ...}
        """
        if not self._sd_available:
            return {t: {
                "name": f"模拟-{t}",
                "price": 10.0,
                "change_pct": 0.5,
            } for t in tickers}

        try:
            return self._sd.tencent_quote(tickers)
        except Exception as e:
            logger.warning("获取实时行情失败: %s", e)
            return {}

    # ── 估值 ────────────────────────────────────────────────────────────────────

    def get_valuation(self, ticker: str) -> dict | None:
        """获取个股估值数据

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            {pe_ttm, pb, name, price, mcap_yi, ...} 或 None
        """
        if not self._sd_available:
            return None

        try:
            result = self._sd.tencent_quote([ticker])
            if ticker in result:
                q = result[ticker]
                return {
                    "pe_ttm": q.get("pe_ttm", 0),
                    "pb": q.get("pb", 0),
                    "name": q.get("name", ""),
                    "price": q.get("price", 0),
                    "mcap_yi": q.get("mcap_yi", 0),
                }
            return None
        except Exception as e:
            logger.warning("获取估值失败 [%s]: %s", ticker, e)
            return None

    # ── 收盘价序列 ──────────────────────────────────────────────────────────────

    def get_closes(self, ticker: str, days: int = 30) -> list[float] | None:
        """获取最近N天收盘价

        Args:
            ticker: 股票代码
            days: 最近N天

        Returns:
            收盘价列表（旧->新），失败返回 None
        """
        if not self._sd_available:
            return None

        try:
            # 优先用 mootdx（不封IP）
            df = self._sd.mootdx_kline(ticker, days=days)
            if not df.empty:
                return df["close"].tolist()

            # fallback 到百度
            data = self._sd.baidu_kline_with_ma(ticker)
            keys = data.get("keys", [])
            rows = data.get("rows", [])

            if not keys or not rows:
                return None

            # 找 close 列的索引
            close_idx = None
            for i, k in enumerate(keys):
                if k.lower() in ("close", "收盘"):
                    close_idx = i
                    break
            if close_idx is None:
                # 默认第4个字段是收盘价 (date,open,high,low,close,...)
                close_idx = 4

            closes = []
            for row in rows:
                if not row:
                    continue
                parts = row.split(",")
                if len(parts) > close_idx:
                    try:
                        closes.append(float(parts[close_idx]))
                    except (ValueError, IndexError):
                        continue

            if not closes:
                return None

            # 取最近 N 天
            return closes[-days:] if len(closes) >= days else closes
        except Exception as e:
            logger.warning("获取收盘价失败 [%s]: %s", ticker, e)
            return None

    # ── 指数收盘价序列（相对强度用）────────────────────────────────────────────────

    def get_index_closes(self, index_code: str = "000300", days: int = 60) -> list[float] | None:
        """获取指数最近N天收盘价（动量技能算相对强度用）

        Args:
            index_code: 指数代码，默认 000300 沪深300。
                        常用：399006创业板指 / 000001上证 / 000905中证500
            days: 最近N天

        Returns:
            收盘价列表（旧->新），失败返回 None
        """
        if not self._sd_available:
            return None

        try:
            df = self._sd.mootdx_index_kline(index_code, days=days)
            if df is not None and not df.empty:
                return df["close"].tolist()
            return None
        except Exception as e:
            logger.warning("获取指数收盘价失败 [%s]: %s", index_code, e)
            return None

    # ── 融资融券变化 ────────────────────────────────────────────────────────────

    def get_margin_change(self, ticker: str) -> float | None:
        """获取融资余额变化百分比

        计算最近两个交易日的融资余额变化率。

        Args:
            ticker: 股票代码

        Returns:
            变化百分比 (如 5.2 表示 +5.2%)，失败返回 None
        """
        if not self._sd_available:
            return None

        try:
            data = self._sd.margin_trading(ticker, page_size=5)
            if len(data) < 2:
                return None

            # 按日期升序排列（margin_trading 默认降序）
            data.sort(key=lambda x: x.get("date", ""))

            latest = data[-1].get("rzye", 0)
            prev = data[-2].get("rzye", 0)

            if prev and prev != 0:
                return round((latest - prev) / prev * 100, 2)
            return None
        except Exception as e:
            logger.warning("获取融资融券变化失败 [%s]: %s", ticker, e)
            return None

    # ── 个股主力资金流（已切换为代理证据包）─────────────────────────────────────

    def get_fund_flow(self, ticker: str, recent_days: int = 5) -> dict | None:
        """获取个股资金流（已切换为代理证据包）。

        ⚠️ 东财 push2his 资金流已废弃。本方法返回代理证据包包装，
        不再输出 main_net_yi/super_net_yi/recent_inflow_days 等伪字段。

        Args:
            ticker: 6位股票代码
            recent_days: 保留参数，未使用

        Returns:
            代理证据包装 dict 或 None
        """
        evidence = self.get_capital_evidence(ticker)
        if evidence is None:
            return None
        return {
            "source": "proxy_evidence",
            "data_quality": evidence["data_quality"],
            "legacy_note": "eastmoney push2his disabled; use get_capital_evidence instead",
            "capital_evidence": evidence,
        }

    # ── 资金行为代理证据包（替代已废弃的东财资金流）────────────────────────────────

    def get_capital_evidence(self, ticker: str, days: int = 60) -> dict | None:
        """获取资金行为代理证据包

        用价量/位置/融资/大宗/筹码/概念组成代理证据，替代已废弃的东财 push2his 资金流。

        Args:
            ticker: 6位股票代码
            days: K线取数天数（默认60，用于位置和量价计算）

        Returns:
            证据包 dict 或 None（数据源不可用）
        """
        if not self._sd_available:
            return None

        missing: list[str] = []
        result: dict = {
            "code": ticker,
            "source": "proxy_evidence",
        }

        # ── volume_price + position：共用 K线 ─────────────────────────
        volume_price = {
            "latest_close": None,
            "latest_volume": None,
            "avg_volume_20": None,
            "volume_ratio_20": None,
            "return_5d": None,
            "return_20d": None,
        }
        position = {
            "price_position_60d": None,
            "bucket": None,
        }

        kline = self.get_hist_data(ticker, days=days)
        if kline and len(kline) >= 2:
            latest = kline[-1]
            volume_price["latest_close"] = latest.get("close")
            volume_price["latest_volume"] = latest.get("volume")

            # 20日均量
            vols_20 = [r.get("volume", 0) for r in kline[-20:] if r.get("volume")]
            if vols_20:
                avg_v20 = sum(vols_20) / len(vols_20)
                volume_price["avg_volume_20"] = round(avg_v20, 0)
                if avg_v20 > 0 and volume_price["latest_volume"]:
                    volume_price["volume_ratio_20"] = round(
                        volume_price["latest_volume"] / avg_v20, 2
                    )

            # 收益率
            closes = [r.get("close") for r in kline if r.get("close")]
            if len(closes) >= 21:
                volume_price["return_5d"] = round(
                    (closes[-1] - closes[-6]) / closes[-6] * 100, 2
                )
                volume_price["return_20d"] = round(
                    (closes[-1] - closes[-21]) / closes[-21] * 100, 2
                )
            elif len(closes) >= 6:
                volume_price["return_5d"] = round(
                    (closes[-1] - closes[-6]) / closes[-6] * 100, 2
                )
            elif len(closes) >= 2:
                volume_price["return_5d"] = round(
                    (closes[-1] - closes[0]) / closes[0] * 100, 2
                )

            # 价格位置
            high_60 = max(r.get("high", 0) for r in kline if r.get("high"))
            low_60 = min(r.get("low", float("inf")) for r in kline if r.get("low"))
            if high_60 > low_60 and volume_price["latest_close"]:
                pos = (volume_price["latest_close"] - low_60) / (high_60 - low_60)
                pos = max(0.0, min(1.0, pos))
                position["price_position_60d"] = round(pos, 4)
                if pos < 0.33:
                    position["bucket"] = "low"
                elif pos < 0.67:
                    position["bucket"] = "mid"
                else:
                    position["bucket"] = "high"
        else:
            missing.append("hist_data")

        result["volume_price"] = volume_price
        result["position"] = position

        # ── 辅助信号 ──────────────────────────────────────────────────
        has_kline = kline is not None and len(kline) >= 2
        aux_count = 0

        # margin
        try:
            margin_val = self.get_margin_change(ticker)
            if margin_val is not None:
                result["margin"] = {"change_pct": margin_val}
                aux_count += 1
            else:
                missing.append("margin")
        except Exception as e:
            logger.warning("资金证据-margin失败 [%s]: %s", ticker, e)
            missing.append("margin")

        # block_trade
        try:
            bt_entry = {"score": 0, "latest_date": None,
                        "latest_premium_pct": None, "latest_buyer": None,
                        "latest_seller": None, "latest_amount_yi": None,
                        "age_days": None, "within_1y": None,
                        "is_stale": None, "staleness_reason": None,
                        "evidence_window_days": 365}
            bt_score = self.get_block_trade(ticker)
            if bt_score is not None:
                bt_entry["score"] = bt_score
            raw_trades = self._sd.block_trade(ticker, page_size=3)
            if raw_trades:
                t = raw_trades[0]
                bt_entry["latest_date"] = t.get("date")
                bt_entry["latest_premium_pct"] = t.get("premium_pct")
                bt_entry["latest_buyer"] = t.get("buyer")
                bt_entry["latest_seller"] = t.get("seller")
                amt = t.get("amount", 0)
                bt_entry["latest_amount_yi"] = round(amt / 1e8, 4) if amt else None
                # staleness metadata
                age = self._calc_age_days(bt_entry["latest_date"])
                if age is not None:
                    bt_entry["age_days"] = age
                    bt_entry["within_1y"] = age <= 365
                    bt_entry["is_stale"] = age > 365
                    bt_entry["staleness_reason"] = "latest block trade older than 365 days" if age > 365 else None
                else:
                    bt_entry["staleness_reason"] = "date_parse_error"
            else:
                bt_entry["staleness_reason"] = "no block trade data"
            result["block_trade"] = bt_entry
            aux_count += 1
        except Exception as e:
            logger.warning("资金证据-block_trade失败 [%s]: %s", ticker, e)
            missing.append("block_trade")

        # holder
        try:
            holder_data = self.get_holder_change(ticker)
            if holder_data and len(holder_data) >= 1:
                sorted_data = sorted(holder_data, key=lambda x: x.get("date", ""), reverse=True)
                latest_h = sorted_data[0]
                result["holder"] = {
                    "latest_date": latest_h.get("date"),
                    "latest_holder_num": latest_h.get("holder_num"),
                    "latest_change_ratio": latest_h.get("change_ratio"),
                    "latest_change_num": latest_h.get("change_num"),
                    "report_period": latest_h.get("date"),
                }
                aux_count += 1
            else:
                missing.append("holder")
        except Exception as e:
            logger.warning("资金证据-holder失败 [%s]: %s", ticker, e)
            missing.append("holder")

        # concept
        try:
            concept_data = self.get_concept_blocks(ticker)
            if concept_data and concept_data.get("concept_tags"):
                result["concept"] = {
                    "concept_tags": concept_data["concept_tags"][:10]
                }
                aux_count += 1
            else:
                missing.append("concept")
        except Exception as e:
            logger.warning("资金证据-concept失败 [%s]: %s", ticker, e)
            missing.append("concept")

        # market_context
        try:
            market_data = self.get_market_north_sentiment()
            if market_data is not None:
                market_data["scope"] = "market_only_not_individual"
                result["market_context"] = market_data
            else:
                missing.append("market_context")
        except Exception as e:
            logger.warning("资金证据-market_context失败 [%s]: %s", ticker, e)
            missing.append("market_context")

        # ── data_quality ──────────────────────────────────────────────
        if not has_kline:
            result["data_quality"] = "NO_DATA"
        elif aux_count >= 2:
            result["data_quality"] = "MEDIUM"
        else:
            result["data_quality"] = "LOW"

        result["missing"] = missing
        return result

    # ── 大盘北向情绪（背景，非个股）──────────────────────────────────────────────

    def get_market_north_sentiment(self) -> dict | None:
        """获取大盘北向资金情绪（沪股通+深股通整体当日净流入）。

        ⚠️ 这是**大盘整体**北向，不是个股北向（个股每日北向已于
        2024-08 起停止实时披露）。仅作市场情绪背景，**不可当个股信号**。

        Returns:
            {hgt_yi, sgt_yi, total_yi} 整体净流入（亿元）或 None
        """
        if not self._sd_available:
            return None

        try:
            df = self._sd.hsgt_realtime()
            if df.empty:
                return None
            latest = df.iloc[-1]
            hgt = latest.get("hgt_yi")
            sgt = latest.get("sgt_yi")
            hgt = float(hgt) if hgt is not None and hgt == hgt else 0.0
            sgt = float(sgt) if sgt is not None and sgt == sgt else 0.0
            return {
                "hgt_yi": round(hgt, 2),
                "sgt_yi": round(sgt, 2),
                "total_yi": round(hgt + sgt, 2),
            }
        except Exception as e:
            logger.warning("获取大盘北向情绪失败: %s", e)
            return None

    # ── 大宗交易 ────────────────────────────────────────────────────────────────

    def get_block_trade(self, ticker: str) -> float | None:
        """获取大宗交易活跃度评分

        根据最近大宗交易的溢价率和交易量计算评分。

        Args:
            ticker: 股票代码

        Returns:
            评分 (0-100)，失败返回 None
        """
        if not self._sd_available:
            return None

        try:
            trades = self._sd.block_trade(ticker, page_size=10)
            if not trades:
                return 0.0

            # 评分逻辑：有交易=基础分，溢价率高加分，量大加分
            score = 0.0
            for t in trades:
                score += 5  # 每笔交易基础5分
                premium = abs(t.get("premium_pct", 0))
                if premium > 5:
                    score += 10
                elif premium > 2:
                    score += 5

            return min(score, 100.0)
        except Exception as e:
            logger.warning("获取大宗交易失败 [%s]: %s", ticker, e)
            return None

    @staticmethod
    def _calc_age_days(date_str: str) -> int | None:
        """计算给定日期字符串距今多少天。

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)

        Returns:
            天数或 None（解析失败）
        """
        try:
            d = date.fromisoformat(date_str)
            return (date.today() - d).days
        except (ValueError, TypeError):
            return None

    # ── 历史K线 ────────────────────────────────────────────────────────────────

    def get_hist_data(
        self, ticker: str, period: str = "daily", days: int = 60
    ) -> list[dict] | None:
        """获取历史K线数据

        Args:
            ticker: 股票代码
            period: 周期 (daily / weekly / monthly)
            days: 最近N个交易日

        Returns:
            K线数据列表 [{date, open, high, low, close, volume}, ...]，失败返回 None
        """
        if not self._sd_available:
            return None

        try:
            # 优先用 mootdx（不封IP）
            df = self._sd.mootdx_kline(ticker, days=days)
            if not df.empty:
                result = []
                for _, row in df.iterrows():
                    result.append({
                        "date": str(row["datetime"])[:10],
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["vol"],
                    })
                return result

            # fallback 到百度
            data = self._sd.baidu_kline_with_ma(ticker)
            keys = data.get("keys", [])
            rows = data.get("rows", [])

            if not keys or not rows:
                return None

            result = []
            for row in rows:
                if not row:
                    continue
                parts = row.split(",")
                if len(parts) < len(keys):
                    continue
                record = {}
                for i, k in enumerate(keys):
                    val = parts[i]
                    try:
                        record[k] = float(val) if val else 0
                    except ValueError:
                        record[k] = val
                result.append(record)

            if not result:
                return None

            return result[-days:] if len(result) >= days else result
        except Exception as e:
            logger.warning("获取历史K线失败 [%s]: %s", ticker, e)
            return None

    # ── 板块归属 ──────────────────────────────────────────────────────────────

    def get_concept_blocks(self, ticker: str) -> dict | None:
        """获取个股板块归属

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            {total, boards: [...], concept_tags: [...]} 或 None
        """
        if not self._sd_available:
            return None

        try:
            return self._sd.eastmoney_concept_blocks(ticker)
        except Exception as e:
            logger.warning("获取板块归属失败 [%s]: %s", ticker, e)
            return None

    # ── 个股基本信息 ─────────────────────────────────────────────────────────

    def get_stock_info(self, ticker: str) -> dict | None:
        """获取个股基本信息

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            {code, name, industry, total_shares, float_shares, mcap, float_mcap, list_date, price}
            或 None
        """
        if not self._sd_available:
            return None

        try:
            return self._sd.eastmoney_stock_info(ticker)
        except Exception as e:
            logger.warning("获取个股信息失败 [%s]: %s", ticker, e)
            return None

    # ── 概念纯度分级 ─────────────────────────────────────────────────────────

    def classify_concept_purity(
        self,
        concept_tags: list[str],
        keywords: list[str],
        industry: str | None = None,
        negative_industries: list[str] | None = None,
        positive_industries: list[str] | None = None,
    ) -> dict:
        """概念纯度分级：判断个股概念标签与主题关键词的匹配纯度，新增行业辅助信号

        Args:
            concept_tags: 个股概念标签列表（如 get_concept_blocks 返回的 concept_tags）
            keywords: 方向核心关键词列表（如 ["机器人","机器视觉","传感器"]）
            industry: 个股所属行业，None 时不启动行业辅助
            negative_industries: 负向行业列表，默认钢铁/水务/化工等
            positive_industries: 正向行业列表，默认通用设备/自动化/机器人等

        Returns:
            {"purity", "matched_keywords", "negative_tags", "industry",
             "industry_signal", "purity_reason"}
        """
        if negative_industries is None:
            negative_industries = ["钢铁", "水务", "化工", "房地产", "汽车经销",
                                   "港口", "环保", "煤炭", "石油", "建材",
                                   "房屋建设"]
        if positive_industries is None:
            positive_industries = ["通用设备", "自动化设备", "机器人", "计算机设备",
                                   "软件开发", "半导体", "电子元件", "电机",
                                   "通信设备", "汽车零部件"]

        matched = [kw for kw in keywords if any(kw in tag for tag in concept_tags)]
        negative_sectors = ["钢铁", "化工", "制药", "水务", "房屋建设", "港口",
                           "汽车经销", "环保", "煤炭", "石油", "建材",
                           "房地产", "房地产开发"]
        negative = [tag for tag in concept_tags if any(neg in tag for neg in negative_sectors)]

        # ── 行业信号判定 ────────────────────────────────────────────────────
        industry_signal = "unknown"
        if industry:
            pos_match = any(pos in industry for pos in positive_industries)
            neg_match = any(neg in industry for neg in negative_industries)
            if pos_match and neg_match:
                industry_signal = "neutral"
            elif pos_match:
                industry_signal = "positive"
            elif neg_match:
                industry_signal = "negative"
            else:
                industry_signal = "neutral"

        # ── 基础纯度（保持旧逻辑） ───────────────────────────────────────────
        if matched and not negative:
            purity = "high"
            reason = f"命中{len(matched)}个核心关键词，无噪声标签"
        elif matched and negative:
            purity = "medium"
            reason = f"命中{len(matched)}个核心关键词，含{len(negative)}个噪声标签"
        elif not matched and not negative:
            purity = "medium"
            reason = "无核心关键词也无噪声标签（泛科技/设备类）"
        else:
            purity = "low"
            reason = f"无核心关键词，噪声标签：{negative}"

        # ── 行业信号调整（辅助降噪，不做正向提升） ───────────────────────────
        if industry_signal == "negative":
            if purity == "high":
                purity = "medium"
                reason += "；因行业负向信号降为medium"
            elif purity == "medium" and not matched and not negative:
                purity = "low"
                reason += "；因无核心词+行业负向信号降为low"

        if industry is not None:
            reason += f" [行业={industry}, 信号={industry_signal}]"

        return {
            "purity": purity,
            "matched_keywords": matched,
            "negative_tags": negative,
            "industry": industry,
            "industry_signal": industry_signal,
            "purity_reason": reason,
        }

    # ── 股东户数变化 ────────────────────────────────────────────────────────

    def get_holder_change(self, ticker: str) -> list[dict] | None:
        """获取股东户数变化

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            [{date, holder_num, change_num, change_ratio, avg_shares}] 或 None
        """
        if not self._sd_available:
            return None

        try:
            return self._sd.holder_num_change(ticker)
        except Exception as e:
            logger.warning("获取股东户数变化失败 [%s]: %s", ticker, e)
            return None

    # ── 研报列表 ────────────────────────────────────────────────────────────

    def get_reports(self, ticker: str) -> list[dict] | None:
        """获取研报列表

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            [{title, publishDate, orgSName, ...}] 或 None
        """
        if not self._sd_available:
            return None

        try:
            return self._sd.eastmoney_reports(ticker)
        except Exception as e:
            logger.warning("获取研报列表失败 [%s]: %s", ticker, e)
            return None

    # ── 财务质量 ────────────────────────────────────────────────────────────

    def get_financials(self, ticker: str) -> dict | None:
        """获取财务质量数据（ROE/现金流/毛利率/分红）

        走东财财报（限流），财报季度更新。

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            {report_date, roe, gross_margin, op_cashflow_ps, dividend_ratio, ...} 或 None
        """
        if not self._sd_available:
            return None

        try:
            result = self._sd.get_financials(ticker)
            return result if result else None
        except Exception as e:
            logger.warning("获取财务质量失败 [%s]: %s", ticker, e)
            return None

    # ── 个股新闻 ────────────────────────────────────────────────────────────

    def get_stock_news(self, ticker: str) -> list[dict] | None:
        """获取个股新闻

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            [{title, content, time, source, url}] 或 None
        """
        if not self._sd_available:
            return None

        try:
            return self._sd.eastmoney_stock_news(ticker)
        except Exception as e:
            logger.warning("获取个股新闻失败 [%s]: %s", ticker, e)
            return None

    # ── 业绩预期（分析师一致预期EPS，催化预期差用）──────────────────────────────

    def get_eps_forecast(self, ticker: str) -> list[dict] | None:
        """获取分析师一致预期EPS（同花顺）

        注意：这是分析师预测，不是公司发布的业绩预告公告。
        用于催化技能判断"市场预期"这一面，算预期差。

        Args:
            ticker: 股票代码 (6位纯数字)

        Returns:
            [{年度, 预测机构数, 最小值, 均值, 最大值, 行业平均数}] 或 None
        """
        if not self._sd_available:
            return None

        try:
            df = self._sd.ths_eps_forecast(ticker)
            if df is not None and not df.empty:
                return df.to_dict("records")
            return None
        except Exception as e:
            logger.warning("获取业绩预期失败 [%s]: %s", ticker, e)
            return None

    # ── 套利：可转债 / 机构调研 / AH溢价 ──────────────────────────────────────

    def get_convertible_bonds(self) -> list[dict] | None:
        """获取集思录全市场可转债（含转股溢价率）。

        ⚠️ 与其他方法不同：集思录 cookie 缺失/失效会抛 JisiluCookieError，
        **原样向上抛，不降级 None**——让套利 agent 能通知 sui 去登录。

        Returns:
            转债列表，数据源不可用返回 None

        Raises:
            stock_data.JisiluCookieError: 集思录未登录或 cookie 失效
        """
        if not self._sd_available:
            return None
        # 注意：JisiluCookieError 故意不 catch，原样抛给 agent（Builder #12）
        return self._sd.get_convertible_bonds()

    def get_institution_research(
        self, ticker: str = "", page_size: int = 50
    ) -> list[dict] | None:
        """获取机构调研记录（传 code 查单只，空查全市场最新）。

        Returns:
            [{code, name, survey_date, org_num, receive_way, investigators}] 或 None
        """
        if not self._sd_available:
            return None

        try:
            return self._sd.get_institution_research(ticker, page_size=page_size)
        except Exception as e:
            logger.warning("获取机构调研失败 [%s]: %s", ticker, e)
            return None

    def get_ah_premium(self) -> list[dict] | None:
        """获取全市场 AH 股溢价率（溢价率为负=A股相对H股折价）。

        Returns:
            [{a_code, h_code, name, premium_rt, a_price, h_price}] 或 None
        """
        if not self._sd_available:
            return None

        try:
            return self._sd.get_ah_premium()
        except Exception as e:
            logger.warning("获取AH溢价失败: %s", e)
            return None

    # ── 健康检查 ────────────────────────────────────────────────────────────────

    # ── 全球行情 ────────────────────────────────────────────────────────────────

    def get_global_listing_quote(self, company_name: str,
                                   country_hint: str | None = None,
                                   ticker: str | None = None) -> dict:
        """获取海外公司的上市映射与行情

        只做客观数据补全，不判断游丝，不判断投资价值。

        Args:
            company_name: 公司名（中/英/日/韩文均可）
            country_hint: 国籍提示（如 "日本"、"美国"），帮助推断市场
            ticker: 已知 ticker 时跳过搜索直接查行情

        Returns:
            见 resolve_global_listing 的返回字段结构
        """
        try:
            from hound_system.data.global_market_data import resolve_global_listing, get_us_hk_quote

            if ticker:
                # 已知 ticker：跳过搜索直接取行情
                market = None
                if ticker.isdigit() and len(ticker) == 5:
                    market = "HK"
                elif ticker.isalpha():
                    market = "US"
                if market in ("US", "HK"):
                    quote = get_us_hk_quote(ticker, market)
                    return quote
                # 非 US/HK 用 resolve 走 fallback
                return resolve_global_listing(company_name, country_hint)

            return resolve_global_listing(company_name, country_hint)
        except ImportError:
            logger.warning("global_market_data 未安装")
            return {"coverage_status": "module_missing", "company": company_name}
        except Exception as e:
            logger.warning("获取全球行情失败 [%s]: %s", company_name, e)
            return {"coverage_status": "error", "company": company_name, "error": str(e)}

    def health_check(self) -> dict[str, bool]:
        """检查各数据源可用性

        Returns:
            {"stock_data": True/False, "tencent_quote": True/False, ...}
        """
        status: dict[str, bool] = {"stock_data": self._sd_available}
        if self._sd_available:
            try:
                result = self._sd.tencent_quote(["000001"])
                status["tencent_quote"] = bool(result)
            except Exception:
                status["tencent_quote"] = False
        return status


# ── 报告输出 ──────────────────────────────────────────────────────────────────

@dataclass
class ReportConfig:
    """猎犬报告输出配置

    Usage::

        config = ReportConfig()  # 默认路径由 $HOUND_REPORT_DIR 指定（未设置则为 ./reports）
        config.save(cards, recipe="资金+价值")
    """

    base_dir: str = os.environ.get("HOUND_REPORT_DIR", "./reports")

    def today_dir(self) -> str:
        """返回当天日期子目录路径，如 <报告根目录>/2026-06-30/"""
        return os.path.join(self.base_dir, datetime.now().strftime("%Y-%m-%d"))

    def save(self, cards: list[dict], recipe: str = "单技能") -> str:
        """保存议题卡为 markdown 报告

        Args:
            cards: 议题卡列表，每张含 {标的, 来源技能, 核心机会, 入选理由, ...}
            recipe: 配方名/扫描类型，用于文件名

        Returns:
            写入的文件路径
        """
        report_dir = self.today_dir()
        os.makedirs(report_dir, exist_ok=True)

        ts = datetime.now().strftime("%H%M%S")
        filename = f"{recipe}_{ts}.md"
        filepath = os.path.join(report_dir, filename)

        lines = [
            f"# 猎犬扫描报告 · {recipe}",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> 标的数量：{len(cards)}",
            "",
        ]

        for i, card in enumerate(cards, 1):
            lines.append(f"## {i}. {card.get('标的/方向', card.get('code', '?'))}")
            lines.append("")
            for key in ["来源技能", "核心机会", "入选理由", "证据链",
                        "信号强度", "置信度", "共振线索",
                        "需要 M2 验证的问题", "主要风险", "证伪条件",
                        "建议优先级"]:
                val = card.get(key, "")
                if val:
                    lines.append(f"- **{key}**：{val}")
            lines.append("")
            lines.append("---")
            lines.append("")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info("报告已保存: %s (%d张卡)", filepath, len(cards))
        return filepath
