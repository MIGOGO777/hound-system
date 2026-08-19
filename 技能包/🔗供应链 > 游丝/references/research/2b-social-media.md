# 2b. Serenity (@aleabitoreddit) 社交媒体输出分析

> 调研日期: 2026-06-17
> 数据源: yan-labs GitHub 存档 (5,857 条推文), SignalSnitch 调用记录 (691 条已解析), Twitter/X 线程, UnrollNow 收录线程, Substack "Inside the Mind" 深度分析, 中文媒体报道

---

## 一、核心赛道分析

### 1.1 主要覆盖领域

Serenity 的推文宇宙（5,857 条推文中提及 678 个不同 $ticker 代码）呈现高度聚焦的赛道分布：

| 赛道 | 关注度 | 代表公司 | 核心理念 |
|------|--------|----------|----------|
| **光通信/CPO/Photonics** | 🔥🔥🔥🔥🔥 | LITE(509次), AAOI(424), COHR(280), SIVE(573), AXTI(541), IQE(169), SOI(175) | 光互连将取代铜线作为AI规模扩展的瓶颈 |
| **半导体制造/衬底/材料** | 🔥🔥🔥🔥🔥 | AXTI, IQE, TSEM(152), SOI, MTSI(88), GFS(44) | InP衬底→外延片→激光器的垂直供应链 |
| **内存/HBM/NAND** | 🔥🔥🔥🔥 | MU(185), SNDK(164), EWY(101), Samsung, SK Hynix | 内存超级周期中的定价权错配 |
| **Neocloud/AI基础设施** | 🔥🔥🔥🔥 | NBIS(691次最多), IREN(444), CIFR(210), CRWV(202), WULF(115) | 融资质量决定胜负，NBIS是"下一个AWS" |
| **电力/电网/AI能源** | 🔥🔥🔥 | XLU(53), VRT, CEG, VST, Delta(2308) | 800V DC提前部署，AI电力需求的结构性增长 |
| **半导体设备/测试** | 🔥🔥🔥 | AEHR(127), AMKR(42), FN(50) | 光学测试瓶颈，良率控制是隐形成本 |
| **国防/太空** | 🔥🔥 | RKLB(179), AVAV(47), SPCX(新IPO), LPK(51) | 太空+国防供应链中的瓶颈 |
| **机器人/Physical AI** | 🔥🔥 | 稀土/磁材(MP, UUUU), 结构材料(ATI, CRS) | 美国正在输掉机器人竞赛，关键材料受制于中国 |

### 1.2 高频提及股票 Top 20

| 排名 | 代码 | 提及次数 | 赛道 | 核心论点 |
|------|------|---------|------|---------|
| 1 | NBIS | 691 | Neocloud | $17B MSFT合同锁定，NVDA融资背书，Nasdaq 100背书 |
| 2 | SIVE | 573 | CPO/Photonics | #2最佳论点，+1900%, CPO激光瓶颈，~$3B MC |
| 3 | AXTI | 541 | InP衬底 | "AI行业瓶颈"，+1057%, 4个瓶颈垂直整合 |
| 4 | NVDA | 520 | AI芯片 | 800V DC提前，光学投资$6B(COHR+LITE+MRVL) |
| 5 | LITE | 509 | 光通信 | +174%验证，光学供应链核心 |
| 6 | IREN | 444 | Neocloud | 从多到空，$6B ATM稀释是转折点 |
| 7 | AAOI | 424 | 光模块 | +483%, "10倍收入增长" |
| 8 | GOOGL | 351 | 超大规模 | TPU供应链入口，800V DC领先 |
| 9 | MSFT | 338 | 超大规模 | NBIS合同背书关键 |
| 10 | META | 315 | 超大规模 | 光学需求驱动因素 |

### 1.3 叙事偏好

1. **"不要买铁锹卖家"** — 不追NVDA，而是逆向追踪供应链到最上游、最小市值、最致命瓶颈
2. **"海峡类比"** — AXTI = "AI的霍尔木兹海峡"；WF6(六氟化钨)瓶颈类比石油海峡
3. **"机构滞后论"** — 提前4-6周发现瓶颈，等机构买入时是验证而非信号
4. **"第二/三阶效应"** — 不买表面赢家，想通供应链的连锁反应
5. **"X年窗口期"** — 2027-2028 CPO从可插拔过渡到共封装，是最大催化

---

## 二、典型论点结构

### 2.1 结构模板

Serenity 的推文 / 线程有以下标准模式：

**模式 A: 瓶颈发现线程**（最典型，通常是她的最高质量内容）

```
1/ 开篇定调句 —— "I genuinely think $X is very compelling at $XB MC"
   或 "Let me explain why $X is the biggest bottleneck in AI right now"
   
2/ 供应链地图 —— 从下游需求（超大规模capex）→ 中游（模块/组装）→ 上游（材料/衬底）
   标志性写法: "$AXTI (substrates) → $IQE (epiwafers) → $AAOI (lasers) / $LITE / $SIVE"
   
3/ 估值错配 —— 合同ARR vs 市值，未定价的供应约束
   典型句子: "If this layer stopped shipping, what breaks downstream?"
   
4/ 催化剂清单 —— 订单、产能公告、政策、地缘事件
   
5/ 风险框架 —— 稀释/单一客户/中国出口管制，然后指定仓位大小
   
6/ 总结/行动 —— "Not a buy now" / "Build conviction yourself" / "S-tier research"
```

**模式 B: 验证/胜利宣告**

```
- "Call validated" / "Aged super well" / "This is my #2 greatest thesis after $AXTI"
- 引用原始推文时间戳做对比
- "Institutions (JPM/Fidelity) only recently entering" → 还有上涨空间
```

**模式 C: 宏观冲击 → 买入机会**

```
- "Algorithmic risk-off" ≠ "fundamental re-rating"
- 区分系统性抛售 vs 基本面恶化
- "Best entry point of 2025" (NBIS在关税冲击时)
```

**模式 D: 驳斥/回应批评**

```
- 经常出现 "Majority of folks have 0 clue what they're talking about"
- 指出他人混淆供应链层级（substrate ≠ epiwafer ≠ feedstock）
- "TA is snake oil without fundamentals"
```

### 2.2 线程长度特征

- **短推文**（1-3条）: 快评、新闻反应、仓位截图
- **中等线程**（5-15条）: 标准的论点展开
- **长文章**（X Articles）: 每月1-2篇深度长文（SIVE CPO文章、Hidden Gold Rush方法论、机器人竞赛、Clarity Act政策分析）

### 2.3 示例分析：$SIVE 入场论点结构

```
Step 1: 发现 → 在供应链OSINT中注意到Ayar Labs从网站移除了LITE/MTSI，留下SIVE
Step 2: 验证 → 确认SIVE是CPO用CW/DFB激光器的关键供应商
Step 3: 估值 → ~$290M MC，对比~$15T+超大规模下游价值
Step 4: 催化剂 → 机构进场（JPM、Fidelity首次买入）
Step 5: 风险 → 高波动性，建议0.5%-1%仓位
Step 6: 结果 → +1900%在3个月内
```

---

## 三、选股模式

### 3.1 核心筛选标准（方法论15问检查表）

Serenity 的选股有明确的系统：

| 维度 | 条件 | 指标 |
|------|------|------|
| **瓶颈性** | 唯一/近乎唯一来源的瓶颈，无近期替代品，有真实定价权 | "if this stopped shipping, what breaks?" |
| **上游+低价** | 在上游，组件成本只占下游BOM的小百分比 | 光学 ~8-12% TPU BOM |
| **需求驱动** | TAM正因AI超大规模capex扩张 | "Jensen Huang's $3-4T annually by 2030" |
| **合同/对手方** | 已签多年合同，对手方AAA评级超大规模 | NBIS-$MSFT $17B, IQE-$MTSI-$TSEM |
| **真实利润率** | GAAP毛利润率（非调整后非GAAP） | 拒绝IREN的"92%毛利率" |
| **融资质量** | 无大额ATM+SBC悬置 | IREN $6B ATM ≈ 51%稀释 |
| **阶段** | 预量产斜坡（合格设计赢得），TTM收入低估 | SIVE, AEHR, LPK |
| **市值区间** | <~$3B 在喊单时 | SIVE ~$290M, AXTI ~$700M |
| **叙事阶段** | 机构覆盖仍滞后于供应链证据 | "4-6 weeks ahead" |

### 3.2 量化/定性倾向

- **重定性、轻量化**：她做的是供应链地图+逻辑推理，不是财务模型
- **"合同ARR vs 市值"是唯一关键数字**：签合同是最高置信度信号
- **厌恶纯技术分析**："TA is snake oil without fundamentals"
- **不追踪市场情绪**："IGNORE the sentiment since it's usually wrong"
- **自己做前瞻收益计算**：不依赖屏幕上的P/E倍数

### 3.3 行业偏好

> 光通信/Photonics >> 半导体材料 >> 内存 ≈ Neocloud > 能源/电网 > 国防/太空 > 软件

她明确表示不做纯软件/SaaS/AI应用投资——这些不涉及物理瓶颈。

---

## 四、术语体系

### 4.1 核心术语

| 术语 | 含义 | 使用语境 |
|------|------|----------|
| **Bottleneck / Chokepoint** | 供应链中不可替代的瓶颈点 | "Find the single point of failure" |
| **BOM** | 物料清单（Bill of Materials） | "Multi-hop BOM mapping" |
| **OSINT** | 开源情报（Open Source Intelligence） | 通过网页、LinkedIn、SEC文件发现供应链链接 |
| **InP** | 磷化铟（Indium Phosphide） | 光子学核心衬底材料 |
| **CPO** | 共封装光学（Co-Packaged Optics） | 2027-2028 最大主题 |
| **ELSFP** | 外部光源（External Light Source） | CPO 的关键组件 |
| **Hyperscaler** | 超大规模云厂商 | GOOGL/MSFT/META/AMZN |
| **Mag7** | 七巨头 | 客户集中度过滤器 |
| **ATM** | 按市价增发（At-The-Market offering） | 最重要的负面信号之一 |
| **SBC** | 股权激励（Stock-Based Compensation） | GAAP vs 非GAAP争议 |
| **GAAP margin war** | GAAP毛利率之战 | 用真实利润率排名 |
| **Neocloud** | 新一代云服务商 | NBIS, IREN, CIFR, CRWV |
| **OSAT** | 外包半导体封装测试 | 供应链中的一个环节 |
| **Take-or-pay** | 照付不议合同 | 收入可见性的最高背书 |
| **Qualification cycle** | 认证周期 | 在产品放量前进入，TTM收入无法反映真实价值 |
| **Institutional lag** | 机构滞后 | 零售先于大资金4-6周发现 |
| **Vega / IV mispricing** | 隐含波动率错配 | 用长期LEAP做凸性杠杆 |

### 4.2 信息源引用方式

| 信息来源 | 使用方式 | 示例 |
|----------|----------|------|
| **SEC EDGAR** | 查稀释条款、锁定条件 | IREN $6B ATM |
| **Conference slides** | OFC、GTC、JP Morgan 投资者会议 | SIVE的CPO确认 |
| **LinkedIn/网站** | 追踪合作伙伴变更 | Ayar Labs移除LITE/MTSI留下SIVE |
| **DigitalTimes/Bloomberg/Reuters** | 验证宏观趋势 | China InP 出口放松 |
| **Commercial Times** | 亚洲半导体供应链新闻 | 800V DC 提前的源 |
| **X搜索/引用** | 监控实时讨论 | 跟踪SIVE的机构买入 |
| **SEC进口记录** | 发现SpaceX供应商 | LPK的SpaceX联系 |
| **自己的AI模拟** | Gemini 验证逻辑链 | SIVE的收购可能性 |

---

## 五、表达能力特点

### 5.1 写作风格

1. **自信到傲慢的腔调**
   - "S tier research"、"This is S Tier"
   - "I just predicted this months ago"
   - "Majority of folks have 0 clue"
   - "Ur welcome with $IQE"
   - 经常用"I did say..."/"Remember I told you..."

2. **教育性/解释性**
   - 供应链链接用箭头清晰标注：$AXTI → $IQE → $AAOI/$LITE/$SIVE
   - "Let me explain why"
   - 经常教读者如何自己验证

3. **战斗性强**
   - 直接点名批评错误分析
   - "Most people chase 7.5% index returns, yet random bottlenecks spotted might be 21% in a day lol"
   - 对媒体/分析师嘲笑不屑
   - "If they cannot describe the full chain from memory, treat conviction as underbuilt"

4. **自省但不软弱**
   - "Not doing so well anymore"（承认回撤）
   - "Yeah, I underestimated Trump a bit on Iran"
   - 更新论点而非固执

5. **短句优先，偶尔长链**
   - 大多数推文是 1-3 句
   - 常用表情符号和缩写
   - 使用 "$" ticker 标注
   - 中国报道：她曾用一推文带起A股20CM涨停（绿的谐波、易事特）

### 5.2 视觉元素

| 元素 | 使用频率 | 说明 |
|------|----------|------|
| **仓位截图** | 高 | 展示YTD收益率（峰值4502.45%）、持仓截图作为信誉证明 |
| **供应链地图** | 中 | 自制的"Strait of $AXTI"图表，CPO价值地图 |
| **新闻截图** | 高 | 头条、分析报告、DigiTimes文章的截图 |
| **数据表格** | 中 | 用于对比合同ARR vs 市值 |
| **表情符号** | 中高 | ✅(验证), 🚀(上涨), 🔥(热), 💎(钻石手), lol/💀(调侃) |

### 5.3 互动模式

1. **回复批评者** - 挑衅式回复，"you have no idea what you are talking about"
2. **回复/问答** - 在评论区快速回复粉丝提问和质疑
3. **转发验证** - 当论点被验证时转发新闻/涨幅截图
4. **投票/心态检查** - 偶尔发投票了解市场情绪
5. **不暴露具体操作** - 说"heavily long"但很少给具体入场价和仓位

### 5.4 英文内容特征

- 所有内容在英文
- 英语流利但非母语感（作者可能是华裔或亚裔背景）
- 中文圈叫她"白毛股神"（White Hair Stock God），她接受这个称呼
- 中文社区搬运她的推文到A股引发异动；2026年6月她提到A股"绿的谐波"和"易事特"后引发20CM涨停

### 5.5 SignalSnitch 客观记录

| 指标 | 数据 |
|------|------|
| 已解析调用数 | 691 |
| 胜率 | 51-55%（379胜 / 312负 或 235胜 / 229负） |
| 排名 | #34-#45（随时间波动） |
| 注意 | 回溯性记录，非交易证明 |

---

## 六、思维节奏签名 🧠

### `[上游发现 → 多层BOM映射 → 合同/容量验证 → 市值错配 → 催化剂触发]`

Serenity 的思维节奏可以用以下"拍子"描述：

**第1拍 — 源头扫描（Research Pulse）**：不跟踪新闻或分析师报告。她扫描供应链的原材料/衬底层级（OSINT方法），寻找未被注意的寡头/垄断。这一拍是扩散的、连接性极强的——她会从一篇DigiTimes文章跳到SEC文件，再到LinkedIn职位变更。

**第2拍 — 地图绘制（Mapping Phase）**：一旦发现潜在瓶颈，她会绘制完整的供应链链路，从超大规模资本支出到模块到外延片到衬底到原料。这一拍是分析性的、系统级的——"hyperscaler capex (GOOGL/MSFT/META/AMZN) → ASICs/TPUs → optical transceivers (LITE/AAOI/COHR) → InP epiwafer (IQE) → InP substrate (AXTI/Sumitomo) → InP feedstock (indium, Vital Materials)"。

**第3拍 — 估值错配判断（Valuation Beat）**：她问的不是"这家公司值不值这个价"，而是"如果这个环节停了，下游会死多少？"然后与当前市值做对比。这一拍是价值判断的、反直觉的——$290M vs $15T downstream。

**第4拍 — 催化剂识别（Catalyst Trigger）**：识别具体时间和事件——合同签署、禁令出台、会议演示、机构首次买入。这一拍是时间线敏感的。

**第5拍 — 风险与仓位（Risk Closure）**：她会刻意加入风险讨论——稀释、单一客户暴露、中国出口管制——然后指定适当的仓位规模。"Calls are actually safer than shares on AXTI given China export risk"。

**节奏变化**：当论点被市场验证后，节奏从"发现"切换到"庆祝/再评价"——"Call validated"、"Aged super well"——但不一定卖，而是评估是否还有上升空间。

**核心签名短语：**
- "Remember I told you..."（回溯绑定信誉）
- "If [X] stops shipping, what breaks downstream?"（关键分析问题）
- "Most people chase 7.5% index returns... yet random bottlenecks might be 21% in a day"（风格自我描述）
- "Not a buy now"（避免FOMO的伦理锚点）
- "Build conviction yourself before entering"（风险转移）

**频率模式**：
- 高频推文（20-50条/天）爆发期，然后1-3天静默期
- 线程集中在周末/夜间（美股时间）
- 每周1-2个核心新论点多于买入建议的新闻评论
- 每月1-2篇X Articles作为深度锚点

---

## 附录

### 数据源说明

| 源 | 内容 | 数量 |
|----|------|------|
| yan-labs GitHub | 结构化推文存档（JSON+CSV） | 5,857条（2025-07-02 → 2026-06-08） |
| yan-labs SKILL.md | 方法论蒸馏、检查表、工作流 | ~13K字符 |
| yan-labs theses.md | 每个ticker的最新论点 | 按子行业分组的KB |
| yan-labs track-record.md | 有时间戳的调用记录 | 2025-2026年记录 |
| yan-labs methodology.md | 12个命名原则+15问清单 | ~19K字符 |
| SignalSnitch | 客观调用记录 | 691条已解析，~51-55%准确率 |
| Substack (Inside the Mind) | 第三方深度分析 | 覆盖背景、方法论、预测 |
| bearsavings.com | 传记性文章 | 背景、风格特征 |
| UnrollNow | 线程抓取 | 活跃线程收录 |

### 关于 Serenity 的关键定性判断

1. **信息优势来源不是内幕**，而是（1）比机构分析师更勤奋的OSINT供应链研究 +（2）愿意追踪极其冷门的微型股 +（3）在共识形成前公开发布
2. **最大风险**：幸存者偏差（展示赢家、淡化输家）、自我报告收益率不可验证、微型股流动性/稀释/中国风险
3. **在中文圈的独特定位**："白毛股神"已成为跨境信息传播的现象级符号，其推文被搬运回A股制造涨停
4. **对 AI/Semi 社区的深层影响**：她的方法已被封装成可安装的AI agent skill（npx skills add yan-labs/serenity-aleabitoreddit），成为可复用的分析透镜
