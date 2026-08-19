# 行业→象限映射表 维护指南

> 映射表文件: `/mnt/redbox/正方形系统/v2.3/src/rules/national_strategy.py`
> 最后更新: 2026-05-26

## 何时需要更新

| 信号 | 示例 | 紧急度 |
|------|------|:------:|
| 中央经济工作会议/政治局会议定调新方向 | "低空经济"首次写入政府工作报告 | 🔴 高 |
| 五年规划中期调整 | 重点产业方向变化 | 🔴 高 |
| 某个行业从支持→过剩/限制 | 教培2021被双减 | 🔴 高 |
| 产能过剩恶化/缓解 | 光伏组件利润率持续下行 | 🟡 中 |
| 新赛道出现（尚未在映射表中） | 人形机器人、量子计算 | 🟡 中 |
| 某稳定象限行业PE长期脱离合理区间 | 白酒龙头PE持续>30 | 🟢 低 |

## 更新流程

### 1. 定位映射表

`src/rules/national_strategy.py` 中有三个字典：

```python
# 🟢 要支持的
STRATEGIC_KEYWORDS = { "行业关键词": ("象限", "子类"), ... }

# 🟡 要稳定的  
STABLE_KEYWORDS = { "行业关键词": ("象限", "子类"), ... }

# 🔴 要退出的
EXIT_KEYWORDS = { "行业关键词": ("象限", "子类"), ... }
```

### 2. 添加新行业

```python
# 例：新增"低空经济"到支持象限
STRATEGIC_KEYWORDS["低空经济"] = ("战略新兴", "新兴")
```

### 3. 调整紧迫度

`URGENCY_BONUS` 字典控制政策紧迫度奖励：

```python
URGENCY_BONUS = {
    "先进制程": 20,     # 卡脖子最急
    "前沿": 15,
    "产能过剩": -35,    # 方向对但已过剩
    ...
}
```

**子类不存在时才需要加新key**。通常改的是**已有子类的紧迫度数值**。

### 4. 验证

```bash
cd /mnt/redbox/正方形系统/v2.3
python3 -c "
from src.rules.registry import RuleRegistry
from src.rules import national_strategy, value, industry, emotion, trend, macro, risk
from src.core.signal import EvalContext

reg = RuleRegistry()
value.register_all(reg)
industry.register_all(reg)
emotion.register_all(reg)
trend.register_all(reg)
macro.register_all(reg)
risk.register_all(reg)
national_strategy.register_all(reg)

# 测试新增行业
sd = {'symbol': '000001', 'name': '测试', 'industry': '<新行业名>', 'valuation': {'pe_ttm': 30}}
ctx = EvalContext(stock_data=sd, market_data={}, history_data={})
for j in reg.evaluate_dimension('industry', ctx):
    if j.rule_id == 'sui_01':
        print(f'分数: {j.score}, 方向: {j.direction}')
        print(f'象限: {j.metadata[\"quadrant\"]}, 子类: {j.metadata[\"subcategory\"]}')
"
```

### 5. 写入缺陷文档

更新 `/mnt/redbox/正方形系统/v2.3/已知缺陷&维修记录-2026-05-25.md` 中 #13 的"已知局限"说明。

## 匹配逻辑说明

`_match_industry()` 使用**优先级匹配**：

1. 遍历 `STRATEGIC_KEYWORDS` — 优先匹配（卡脖子/战略方向）
2. 遍历 `EXIT_KEYWORDS` — 其次匹配（退出/收缩方向） 
3. 遍历 `STABLE_KEYWORDS` — 最后匹配（稳定象限）
4. 全不匹配 → 返回 `None` → 默认50分中性

**注意**：匹配是 `kw in industry` 子串匹配。`industry` 是交易所分类名（如"半导体及元器件"），如果交易所改分类名可能导致匹配失败。

## 混合行业公司的处理

"比亚迪"的交易所分类可能是"汽车"，不包含"电池"或"半导体"。这是一个已知局限——在V1版本中，如果行业名无法匹配，只能默认中性。解决方向：

- **短期**：按交易所分类名中最合适的标签匹配
- **长期**：在 `enrich_stock()` 中增加 `concept_tags`（题材/概念标签）作为第二key
