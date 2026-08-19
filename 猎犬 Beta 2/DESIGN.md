# 猎犬 Beta 2 · 设计框架

> 版本：2026-06-30 | 架构定稿人：red-coco → redkaka | 执行：purple-coco
> 定位：agent 驱动选股引擎——主agent 读调度协议派子agent，子agent 读技能包 SKILL 做认知判断

---

## 一、五层架构

```
┌─────────────────────────────────────────────────┐
│  ⑤ 主agent 审核汇总 → 议题卡(11字段)             │
├─────────────────────────────────────────────────┤
│  ④ 调度协议 SKILL                                │
│     主agent操作手册：§0角色/§1路由/§7配方库/§8降级  │
├─────────────────────────────────────────────────┤
│  ③ 7个技能 SKILL (技能包/)                        │
│     子agent读它做认知判断（单镜头认知框架）         │
├─────────────────────────────────────────────────┤
│  ② Python 初筛器 (universe/screener.py)          │
│     只做客观质检：剔ST/停牌/低流动性，不碰策略判断   │
├─────────────────────────────────────────────────┤
│  ① Python 数据层 (hound_system/data/)            │
│     fetcher.py 21个方法，只取数，绝不算分           │
└─────────────────────────────────────────────────┘
```

**§0 铁律**：判断永远在子agent读 SKILL 时发生。主agent只编排「取数+派发+合流」，绝不自己写阈值。这正是 Beta 1 的病（判断被写死成 Python 阈值算分），Beta 2 为治此病而生。

---

## 二、两条数据路线

| 路线 | 适用镜头 | 入口 | 方式 |
|------|---------|------|------|
| **Fetcher 路线** | 价值/动量/资金/催化/套利（个股级） | `HoundFetcher`（21个方法） | 结构化数据，对话中跑 Python |
| **SearXNG 路线** | 光谱/游丝（主题级） | `curl localhost:4000/search` | 搜索，默认不加 time_range，首轮空三轮重试 |

---

## 三、7个技能镜头

| 镜头 | 类别 | 签名第一问 | 数据入口 |
|------|------|-----------|---------|
| 🏛️ 光谱 | 主题级 | 政策在支持什么方向？ | SearXNG |
| 🔗 游丝 | 主题级 | 产业链约束卡在哪个节点？ | SearXNG（递进式下钻） |
| 📊 价值 | 个股级 | 便宜但没坏，还是便宜因为变坏？ | HoundFetcher（**6把尺**） |
| 📈 动量 | 个股级 | 趋势结构改善，还是一次性脉冲？ | HoundFetcher |
| 💰 资金 | 个股级 | 主动建仓，还是短线扰动/对倒？ | HoundFetcher（**方案C证据包**） |
| 📰 催化 | 个股级 | 事件改变了市场预期吗？ | HoundFetcher |
| 🎭 套利 | 个股级 | 市场定价错误可被套利吗？ | HoundFetcher（集思录cookie） |

每个镜头 SKILL.md 含：签名第一问、心智模型（5-6把尺）、误判过滤器、独立入池规则、数据入口协议（3段：数据源映射/并发编排/子agent提示词7要素骨架）。

---

## 四、三机制组合配方库（§7）

> green-coco 体检发现：原"共振9配方"混了三种逻辑。强套一个母版 = 把缺陷复制9份。

### 机制① 取交集型（真双维印证）
A、B 各自独扫 → 取同 code 交集，空集是正常结果。
适用：两池同类可比（个股级）、两维度独立。

| 配方 | 状态 |
|------|------|
| 资金+价值=底部反转 | ✅ 金标准 |
| 价值+催化=确定性反转 | ✅ |
| 价值+动量=价值发现启动 | ✅ |
| 资金+催化=事件爆发 | ✅ |

### 机制② 时序触发型（看时间错位）
A 先发 → B 后起。**禁止机械取交集**（会漏最佳买点）。

| 配方 | 先发→后发 | 状态 |
|------|----------|------|
| 催化→动量=加速段 | 催化先发→动量后起 | ✅（双agent共识已补） |
| 资金潜伏→催化引爆 | 资金先吸筹→催化后触发 | ✅ |

### 机制③ 映射串联型（主题→个股跨类落地）
上游（光谱/游丝，SearXNG）→ **映射环** → 下游（价值/资金/动量/催化，fetcher）。

| 配方 | 上游→下游 | 状态 |
|------|----------|------|
| **光谱→个股** ⭐ | 光谱出方向→个股镜头选票 | ✅ 选股主干道（最高频） |
| 光谱→游丝 | 光谱出方向→游丝挖产业链 | ✅ 产业链研究 |
| 催化→游丝 | 催化出事件→游丝深挖约束 | ✅ |
| 动量→游丝 | 动量出板块→游丝验证约束 | ✅ |

**游丝→个股 深核子型**（不走映射环）：游丝产出已是个股（3-8个控制者），直接逐个深判。

| 配方 | 状态 |
|------|------|
| 游丝→价值 = 被低估的隐形冠军 | ✅ |
| 游丝→资金 = 约束被市场定价 | ✅ |

---

## 五、数据层（HoundFetcher, 21个方法）

### 行情与K线
| 方法 | 返回 |
|------|------|
| `get_stock_list()` | 全市场 ~5200只 |
| `get_realtime_quotes(codes)` | 实时行情 dict |
| `get_closes(code, days)` | 收盘价序列 |
| `get_hist_data(code, days)` | OHLCV K线 |
| `get_index_closes(code, days)` | 指数收盘价 |

### 估值与财务
| 方法 | 返回 |
|------|------|
| `get_valuation(code)` | PE/PB/市值 |
| `get_financials(code)` | ROE/毛利率/现金流/股息率 |

### 资金证据包（方案C）
| 方法 | 返回 |
|------|------|
| `get_capital_evidence(code)` ⭐ | **资金主入口**：量价/位置/融资/大宗/筹码/市场背景/data_quality/missing |
| `get_margin_change(code)` | 融资余额变化% |
| `get_block_trade(code)` | 大宗评分（float） |
| `get_market_north_sentiment()` | 大盘北向情绪 |

### 筹码与概念
| 方法 | 返回 |
|------|------|
| `get_holder_change(code)` | 股东户数变化 |
| `get_concept_blocks(code)` | 概念板块标签 |
| `classify_concept_purity(tags, keywords, industry?)` | 纯度分级 high/medium/low |
| `get_stock_info(code)` | 个股基本信息（含行业） |

### 新闻与研报
| 方法 | 返回 |
|------|------|
| `get_stock_news(code)` | 个股新闻 |
| `get_reports(code)` | 研报列表 |
| `get_eps_forecast(code)` | 分析师一致预期EPS |

### 套利
| 方法 | 返回 |
|------|------|
| `get_convertible_bonds()` | 全市场可转债（需集思录cookie） |
| `get_ah_premium()` | AH溢价率 |
| `get_institution_research(code)` | 机构调研记录 |

### 兼容
| 方法 | 状态 |
|------|------|
| `get_fund_flow(code)` | 已降级为 proxy_evidence 包装，不再调 push2his |

---

## 六、子agent派发规约（§5）

**提示词 = 7要素骨架**（主agent现场填②⑤⑦）：

| 要素 | 来源 | 说明 |
|------|------|------|
| ①角色+签名第一问 | SKILL 固定 | 子agent的身份锚 |
| ②本批任务+预取数据 | 主agent填 | 这批扫什么、数据在哪 |
| ③心智模型（5-6把尺） | SKILL 固定 | 逐把尺子过 |
| ④误判过滤器 | SKILL 固定 | 必须主动排除的模式 |
| ⑤输出契约 | 主agent填 | 议题卡11字段格式 |
| ⑥质量门槛 | SKILL 固定 | 必答问题 |
| ⑦反投机 | Builder#12 | 禁止编造、缺口如实标注 |

**并发模型**：主agent(V4 Pro)不并发，负责编排派发。并发在子agent(V4 Flash)层实现——互不依赖的子agent同一轮同时派出，墙钟=最慢那个。

---

## 七、议题卡（11字段）

输出给 M2 决策层的标准格式：

```
- 标的/方向
- 来源技能
- 核心机会
- 入选理由
- 证据链
- 信号强度：EXTREME / STRONG / MODERATE / WEAK
- 置信度：0.00-1.00
- 共振线索
- 需要 M2 验证的问题
- 主要风险
- 证伪条件
- 建议优先级：观察 / 入池 / 高优先级入池
```

---

## 八、实战样板卡清单（22张）

### 单镜头
- `sample_value_card.md` — 价值扫描样板
- `sample_capital_proxy_evidence_card.md` — 资金方案C样板

### 机制① 取交集
- `sample_resonance_card.md` — 资金+价值（金标准）
- `sample_value_momentum_card.md` — 价值+动量
- `sample_value_catalyst_card.md` — 价值+催化
- `sample_capital_catalyst_card.md` — 资金+催化

### 机制② 时序触发
- `sample_catalyst_momentum_card.md` — 催化→动量原始卡
- `sample_catalyst_momentum_review_card.md` — 动量子agent复核卡
- `sample_catalyst_momentum_dual_review_card.md` — 双agent共识演示卡
- `sample_capital_catalyst_timing_card.md` — 资金潜伏→催化

### 机制③ 映射串联
- `sample_chain_card.md` — 光谱→游丝（A级）
- `sample_spectrum_stock_card.md` — 光谱→个股（主干道）
- `sample_spectrum_capital_card.md` — 光谱→资金（旧 push2his）
- `sample_spectrum_capital_schemeC_card.md` — 光谱→资金（方案C）
- `sample_spectrum_capital_schemeC_purity_card.md` — 光谱→资金（纯度过滤）
- `sample_catalyst_yousi_card.md` — 催化→游丝
- `sample_momentum_yousi_card.md` — 动量→游丝

### 游丝深核子型
- `sample_yousi_value_card.md` — 游丝→价值
- `sample_yousi_capital_card.md` — 游丝→资金（旧）
- `sample_yousi_capital_schemeC_card.md` — 游丝→资金（方案C）

### 增强验证
- `sample_block_trade_staleness_card.md` — 大宗时效性
- `sample_purity_industry_assist_card.md` — 纯度行业辅助
- `sample_value_scarcity_premium_card.md` — 价值稀缺性溢价

---

## 九、关键设计决策

| 决策 | 内容 |
|------|------|
| Beta1 → Beta2 | 判断从"Python阈值算分" → "子agent读SKILL认知判断" |
| 资金数据源 | push2his/push2 废弃 → 方案C 多源代理证据包（量价/位置/融资/大宗/筹码） |
| 东财解绑 | `get_fund_flow` 不再调 `stock_fund_flow_120d`，`main_net_yi/super_net_yi` 字段禁出 |
| 配方组织 | 2母版 → 3机制母版（取交集/时序触发/映射串联） |
| 跨类组合 | 补全"光谱→个股"选股主干道 + 游丝深核子型 |
| 映射环 | 方向名→get_concept_blocks→个股池→纯度过滤(high/medium/low)→行业辅助降噪 |
| 数据质量 | 所有资金证据带 `data_quality` + `missing`，LOW/NO_DATA 不给高优先级 |
| 失败显性化 | Builder#12：缺口如实标注，不编造，不假装成功 |
| 并发 | 主agent不并发，子agent(V4 Flash)并发 |
| 存档 | 旧卡不覆盖，新版另存（_schemeC / _purity / _review 后缀） |
