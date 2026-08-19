"""标的池管理

黑名单：ST股、次新股、低流动性
白名单：用户自定义关注标的
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class UniverseScreener:
    """标的池筛选器"""

    blacklist: set[str] = field(default_factory=set)
    whitelist: set[str] = field(default_factory=set)
    min_listing_days: int = 60        # 最小上市天数（甲方案下暂不过滤次新，留待P3）
    min_daily_volume: float = 5000    # 最小日成交额（万元），低于此视为低流动性

    def filter_static(self, stocks: list[dict]) -> list[dict]:
        """静态客观过滤（无网络）：剔 ST/退市 + 黑名单。

        Args:
            stocks: [{"code", "name"}, ...]

        Returns:
            通过的 [{"code", "name"}, ...]
        """
        result = []
        for s in stocks:
            code = s.get("code", "")
            name = s.get("name", "")
            if self._is_st(name):
                logger.debug("ST/退市过滤: %s %s", code, name)
                continue
            if code in self.blacklist:
                logger.debug("黑名单过滤: %s", code)
                continue
            result.append(s)
        return result

    def filter_liquidity(self, codes: list[str], fetcher) -> list[str]:
        """流动性客观过滤（腾讯批量行情，不封IP）：剔停牌 + 剔低成交额。

        仅在拿到真实成交额时过滤；字段缺失（如mock）时跳过该股的流动性判断，
        避免误杀。停牌（price=0）始终剔除。

        Args:
            codes: 股票代码列表
            fetcher: HoundFetcher 实例

        Returns:
            通过流动性筛选的代码列表
        """
        if not codes:
            return []
        passed = []
        batch_size = 50
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            try:
                quotes = fetcher.get_realtime_quotes(batch)
            except Exception as e:
                logger.warning("流动性批次行情失败，该批保留: %s", e)
                passed.extend(batch)
                continue
            for code in batch:
                q = quotes.get(code)
                if not q:
                    # 拿不到行情，保守保留，交给下游再判
                    passed.append(code)
                    continue
                price = q.get("price", 0)
                if price == 0:
                    logger.debug("停牌过滤: %s", code)
                    continue
                amount = q.get("amount_wan")
                if amount is not None and amount < self.min_daily_volume:
                    logger.debug("低流动性过滤: %s 成交额%.0f万", code, amount)
                    continue
                passed.append(code)
        return passed

    def _is_st(self, name: str) -> bool:
        """按名称判断 ST / 退市股（ST标记在名称里，不在代码里）"""
        if not name:
            return False
        return "ST" in name or "退" in name

    def add_to_blacklist(self, ticker: str):
        """添加到黑名单"""
        self.blacklist.add(ticker)
        logger.info(f"添加到黑名单: {ticker}")

    def add_to_whitelist(self, ticker: str):
        """添加到白名单"""
        self.whitelist.add(ticker)
        logger.info(f"添加到白名单: {ticker}")

    def get_universe(self, fetcher=None) -> list[str]:
        """获取完整标的池（客观质检后的代码列表）

        流程：拉全市场列表 → 静态过滤(ST/黑名单) → 流动性过滤(停牌/低成交额)。
        只做客观质检，不碰任何策略判断。

        Args:
            fetcher: HoundFetcher 实例；无则退化为白名单

        Returns:
            通过质检的股票代码列表
        """
        if fetcher and hasattr(fetcher, "get_stock_list"):
            stocks = fetcher.get_stock_list()
        else:
            stocks = [{"code": c, "name": ""} for c in self.whitelist]

        # 第1步：静态过滤（ST/退市/黑名单），保留名称
        stocks = self.filter_static(stocks)
        codes = [s.get("code", "") for s in stocks if s.get("code")]
        logger.info("静态过滤后: %d 只", len(codes))

        # 第2步：流动性过滤（停牌/低成交额）
        if fetcher and hasattr(fetcher, "get_realtime_quotes"):
            codes = self.filter_liquidity(codes, fetcher)
            logger.info("流动性过滤后: %d 只", len(codes))

        return codes
