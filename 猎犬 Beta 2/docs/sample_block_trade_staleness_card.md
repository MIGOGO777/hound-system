# 大宗交易时效性 Mini-Fix 样板卡
> 日期：2026-06-29
> 目的：证明 age_days/within_1y/is_stale 能区分当前大宗与历史大宗

## 执行摘要

| 标的 | latest_date | age_days | within_1y | is_stale | 风险变化 |
|------|------------|----------|-----------|----------|---------|
| 300308 中际旭创 | 2026-06-29 | ~0 | True | False | 当前大宗，可作为资金证据 |
| 600288 大恒科技 | 2022-12-30 | ~1277 | False | True | 修复前 score=100 误导为当前吸筹 |
| 600215 派斯林 | 2023-10-23 | ~980 | False | True | 同上 |

## ① 字段说明

| 字段 | 类型 | 含义 |
|------|------|------|
| `age_days` | int/None | 最新大宗交易距今天数 |
| `within_1y` | bool/None | age_days <= 365 |
| `is_stale` | bool/None | age_days > 365 |
| `staleness_reason` | str | 原因描述：超期/无数据/日期解析错误 |
| `evidence_window_days` | int | 证据窗口固定值 365（硬编码常量） |

## ② 三只样例对比

### 300308 中际旭创（近期大宗，正常）
- `latest_date = 2026-06-29`，`age_days ~ 0`
- `is_stale = False`，`within_1y = True`
- 子agent 可用作"近期溢价接盘"证据（如 premium_pct > 0）

### 600288 大恒科技（历史大宗，修复前风险最大）
- `latest_date = 2022-12-30`，`age_days ~ 1277`
- `is_stale = True`，`within_1y = False`
- 修复前 `block_trade.score = 100`（多笔溢价旧交易堆分），子agent 看到 score=100 容易误判"机构大宗活跃吸筹"
- 修复后 `is_stale=True` 强制子agent 只能写"历史大宗背景"，不得当主证据

### 600215 派斯林（历史大宗，同上）
- `latest_date = 2023-10-23`，`age_days ~ 980`
- `is_stale = True`，`within_1y = False`
- 同样，score 来自近 3 年前的旧交易，须标注 stale

## ③ 修复前后风险变化

| 方面 | 修复前 | 修复后 |
|------|--------|--------|
| 大恒科技 block_trade | score=100 无时效信息，子agent 易误读为"当前吸筹" | is_stale=True，子agent 标注"历史大宗背景" |
| 中际旭创 | 无问题，但缺乏确认手段 | within_1y=True 确认可用 |
| 子agent 判断负担 | 需自行猜大宗新旧 | 直接读 age_days/is_stale，减少幻觉空间 |

## §0 合规检查

- 数据层仅输出 `age_days/within_1y/is_stale/staleness_reason/evidence_window_days`，是客观时间标签。
- 未输出"吸筹/减持/接盘"等主观判断。
- 判断仍由资金子agent 读 `技能包/💰资金 > 流向/SKILL.md` 完成。
- `get_block_trade(code)` 旧接口仍返回 float/None，未破坏兼容性。

## 已知局限

- `evidence_window_days = 365` 是固定值，若未来需要变长/变短需改源码硬编码。
- `age_days` 基于 `latest_date`（最新一笔大宗日期），非加权平均。若最新一笔大宗金额极小，可能低估整个大宗窗口的有效性。ponytail: 按当前用例够用，若需加权可提 issue。
