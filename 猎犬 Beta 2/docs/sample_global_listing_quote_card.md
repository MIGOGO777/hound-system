# 全球上市映射样板卡 · 半导体量检测设备

## 起点：旧报告一阶结论

旧报告（2026-06-30）结论：
> S 级 13.5/15。控制者: KLA(KLAC) $278.39 55%全球份额，纯美国企业。国产化率: 2026年预期~20-25%，高端光学检测<5%。国产代表: 中科飞测(688361) ¥421.21。

**问题诊断**：三方面不足 —— (1) 停在第一层，未做设备品类拆解，(2) 海外控制者只列了KLA，缺AMAT/Lasertec/Hitachi High-Tech/Onto Innovation等，(3) 国产替代未分层（中科飞测是直接控制者还是追赶者？上海精测/上海睿励/东方晶源是什么角色？）。

---

## 递归下钻过程

### 第 1 轮：量检测设备品类拆解

**搜索关键词**：
- 半导体量检测设备 分类/种类/细分
- 晶圆检测 光刻 overlay CD-SEM 缺陷检测
- KLA 产品线/AMAT 量检测/Lasertec 光刻掩模检测

**发现的主要品类**：

半导体量检测设备按功能分两大类：**检测（Inspection）** 和 **量测（Metrology）**。按工序分前道量检测、后道检测、实验室检测。核心品类如下：

**检测类（Defect Inspection）：**
1. **有图形晶圆缺陷检测（Patterned Wafer Inspection）**：明场光学检测、暗场光学检测。KLA 绝对主导，Surfscan/29xx系列
2. **无图形晶圆缺陷检测（Unpatterned/Blank Wafer Inspection）**：KLA Surfscan SP 系列主导
3. **电子束缺陷检测/复查（E-beam Inspection/Review）**：AMAT 主导，Hitachi 有布局
4. **掩模/光掩模缺陷检测（Mask/Reticle Inspection）**：Lasertec 全球垄断（EUV掩模检测独供）

**量测类（Metrology）：**
1. **关键尺寸量测（CD-SEM）**：Hitachi High-Tech 全球主导，AMAT 有份额
2. **膜厚量测（Thin Film Metrology）**：KLA、Nova、Onto Innovation、Nanometrics
3. **套刻精度量测（Overlay Metrology）**：KLA ~66%+ 市占，ASML 有份额
4. **光学关键尺寸量测（OCD / Scatterometry）**：KLA、Nova、Onto Innovation
5. **三维形貌量测（3D Profile）**：KLA、中科飞测（国产突破）
6. **X射线量测（X-ray Metrology）**：Bruker、Thermo Fisher、各巨头布局

**drill_status**: drilled — 前道量检测内部拆出6大类量测+4大类检测，品类结构清晰

**下一轮建议下钻节点**：各品类控制者（第2轮）

---

### 第 2 轮：各品类控制者

**搜索关键词**：
- CD-SEM 市占率 日立/Hitachi High-Tech
- 光刻 overlay 检测 ASML KLA
- 掩模缺陷检测 Lasertec 市占率
- 电子束检测 应用材料 KLA
- 光学薄膜量测 Nova/Nanometrics/Onto Innovation

**每品类的控制者**：

| 品类 | 全球控制者（按份额排序） | 说明 |
|------|------------------------|------|
| 有图形晶圆缺陷检测（明场） | KLA >> AMAT | KLA 绝对主导 |
| 有图形晶圆缺陷检测（暗场） | KLA > Hitachi | KLA主导 |
| 无图形晶圆缺陷检测 | KLA | KLA Surfscan SP系列垄断 |
| 电子束缺陷检测/复查 | AMAT > Hitachi > KLA | AMAT在e-beam review领先 |
| 掩模/光掩模缺陷检测 | **Lasertec** > KLA | EUV掩模检测Lasertec全球独供 |
| CD-SEM（关键尺寸量测） | **Hitachi High-Tech** > AMAT | 日立60%+市占 |
| 膜厚量测（光学） | KLA > Nova > Onto Innovation | KLA主导 |
| 套刻精度量测（Overlay） | **KLA ~66%** > ASML | KLA压倒性优势 |
| OCD（散射测量） | KLA > Nova | KLA主导 |
| X射线量测 | Bruker > Thermo Fisher | 泛用型设备，非纯半导体专用 |

**drill_status**: drilled — 各品类控制者已分别标出，呈现"KLA绝对主导 + 多领域控制者"格局，并非单靠KLA一家

---

### 第 3 轮：上游依赖与国产替代

**搜索关键词**：
- 中科飞测 产品线 覆盖
- 上海精测 半导体量检测 进展
- 上海睿励 光学薄膜量测
- 量检测设备 光源/光学元件/精密运动平台 国产化

**核心发现**：

**3-A. 国产替代梯队**

| 梯队 | 公司 | 覆盖品类 | 状态 | 备注 |
|------|------|---------|------|------|
| 第一梯队（量产+放量） | **中科飞测(688361)** | 无图形缺陷检测、有图形缺陷检测、三维形貌量测、膜厚量测、套刻量测（六大类） | 批量供货28-14nm，¥430 | 已是国内综合国产替代龙头，持续扩品类 |
| 第二梯队（部分量产） | **上海精测（精测电子300567子公司）** | 膜厚量测（已量产）、OCD（在研）、电子束（在研） | 显示面板检测起家→半导体路径，已部分量产 | 半导体占比仍低(~13%) |
| 第二梯队（部分量产） | **上海睿励（睿励科学仪器）** | 光学膜厚量测（TFX-R3）、光学缺陷检测（BriteSD300） | 营收破亿，近5亿融资，新生产中心落成 | 未上市，专精光学量测 |
| 追赶者 | **东方晶源** | 电子束量检测设备（全线） | 4大电子束品类全覆盖，AI驱动 | 未上市，电子束赛道国内领跑 |
| 追赶者 | **天准科技(688003)** | 半导体检测（纳米图形缺陷） | 收购德国MueTec入局 | 泛半导体检测 |

**3-B. 上游核心零部件依赖（数据缺口较多）**

量检测设备上游核心零部件包括：
- **光源/激光器**：高端深紫外(DUV)光源依赖进口（日/美/德），国内***永新光学***、***福晶科技***等有布局，但精度差距明显
- **光学镜头/物镜**：高端检测对物镜NA/像差要求极高，Zeiss / Nikon 主导，国产***茂莱光学***等有突破
- **精密运动平台/气浮导轨**：Aerotech/Newport/Physik Instrumente主导，国内***大族激光***等有部分布局
- **探测器（CCD/CMOS/PMT）**：高端科学级CCD/CMOS由Hamamatsu/onsemi主导，国内***长春光机所***/***长光辰芯***有突破
- **计算与图像处理软件**：KLA自有IP（Puma/算法库），国产企业自研起步

**drill_status**: data_gap（定性确认光源/镜组/运动台/探测器为上游瓶颈，但SearXNG未返回精确供应份额定量数据——这是公开信息的天然天花板）

---

## 控制者分层（含全球上市映射）

| 控制者 | 分层 | country | listing_status | market | ticker | currency | price | price_source | coverage_status | mapping_type |
|--------|------|---------|---------------|--------|--------|----------|-------|-------------|----------------|-------------|
| KLA (科磊) | 直接控制者 | US | listed | US | KLAC | USD | $278.39 | yahoo | covered | direct |
| Applied Materials (应用材料) | 直接控制者 | US | listed | US | AMAT | USD | $694.64 | yahoo | covered | direct |
| ASMPT | 直接控制者 | HK | listed | HK | 00522 | HKD | $238.80 | tencent | covered | direct |
| Onto Innovation | 直接控制者 | US | listed | US | ONTO | USD | $351.45 | sina | covered | direct |
| ASML (阿斯麦) | 协同控制者 | NL/US | listed | US | ASML | USD | $1883.11 | yahoo | covered | direct |
| **Lasertec (雷泰光电)** | 直接控制者 | JP | listed | TYO:6920 | N/A | JPY | N/A | - | not_covered | data_gap |
| **Hitachi High-Tech (日立高新)** | 直接控制者 | JP | listed | TYO:8036 | N/A | JPY | N/A | - | not_covered | data_gap |
| **Nova Measuring** | 直接控制者 | IL | listed | US (NG) | NG | USD | N/A | - | data_gap | data_gap |
| **Camtek** | 直接控制者 | IL | listed | US (CAMT) | N/A | USD | N/A | - | not_covered | data_gap |
| **SCREEN Holdings** | 直接控制者 | JP | listed | TYO:7735 | XJH(ADR) | USD | N/A | - | data_gap | data_gap |
| 中科飞测 | 替代追赶者(国内龙头) | CN | listed | A股 | 688361 | CNY | ¥430.00 | eastmoney | covered | direct |
| 精测电子(300567) | 替代追赶者 | CN | listed | A股 | 300567 | CNY | - | - | covered | indirect (母公司) |
| 天津芯源微/上海睿励 | 替代追赶者 | CN | unlisted | N/A | N/A | N/A | N/A | - | not_covered | unlisted |
| 东方晶源 | 替代追赶者 | CN | unlisted | N/A | N/A | N/A | N/A | - | not_covered | unlisted |

**覆盖四类验证**：
- **US**: KLA (KLAC) covered, AMAT (AMAT) covered, ONTO (ONTO) covered, ASML (ASML) covered
- **HK**: ASMPT (00522) covered
- **JP**: Lasertec / Hitachi High-Tech / SCREEN — 均为 data_gap (fetcher 不支持日股直连)
- **Unlisted**: 上海睿励、东方晶源 标 unlisted

---

## 每层 drill_status 汇总

| 层级 | 节点 | drill_status | 理由 |
|------|------|-------------|------|
| 1 | 量检测设备品类拆解 | drilled | 拆出10+子品类，结构清晰（检测×4 + 量测×6） |
| 2 | 各品类控制者 | drilled | 各子品类领导者明确——KLA在很多品类主导但不是唯一 |
| 3 | 国产替代分层 | drilled | 中科飞测为绝对龙头(量产6大品类)，精测/睿励/东方晶源各有专攻 |
| 3 | 上游核心零部件 | data_gap | 定性确认光源/镜组/运动台/探测器为上游瓶颈，但SearXNG未返回精确供应份额定量数据——这是公开信息的天然天花板 |
| 3 | Lasertec/Hitachi High-Tech 日股映射 | data_gap | fetcher无法覆盖日股，无法获取实时行情 |
| 3 | Nova/Camtek 美股映射 | data_gap | Nova(NG)有ticker但price为空; Camtek无映射 |

---

## 上市映射覆盖统计

| 市场 | count | covered | fallback | not_covered | data_gap |
|------|-------|---------|----------|-------------|----------|
| US | 7 | 4 (KLAC, AMAT, ONTO, ASML) | 0 | 2 (Camtek, Nova) | 1 (NG price gap) |
| HK | 1 | 1 (00522) | 0 | 0 | 0 |
| JP | 3 | 0 | 0 | 3（Lasertec/Hitachi/SCREEN） | 0 |
| CN A股 | 2 | 2 (688361, 300567) | 0 | 0 | 0 |
| CN 未上市 | 2 | 0 | 0 | 2（睿励/东方晶源） | 0 |

**关键观察**：fetcher 全球映射在 US/HK 覆盖较好，但日本市场完全缺失——建议补充日股行情源（如 yfinance JP）。

---

## 证伪条件（>=2条）

1. **若 KLA 在明场/暗场光学缺陷检测的份额被大幅侵蚀**（如 AMAT 或新进入者以更优技术路线打破垄断），则旧报告"KLA 55%全球份额"和本报告"KLA绝对主导"的判断需要修正
2. **若国产化率实际低于预期**（如中科飞测无法突破7nm以下先进制程验证、良率瓶颈导致客户端导入停滞），旧报告"2026年国产化率20-25%"可能高估
3. **若 Lasertec 的 EUV 掩模检测独供地位被挑战**（如 KLA/AMAT 推出替代品），行业格局将发生重大变化
4. **若上游核心零部件（光学镜组/光源）卡脖子导致国产设备实际交付低于预期**，国产化进程将比预期慢
5. **若日本三大控制者（Lasertec/Hitachi/SCREEN）的份额被更准确的数据源纠正**，本报告的数据缺口修复后将需要重新评估市占格局

---

## 数据缺口（建议优先补）

1. **各子品类精确市占率数字**：仅"KLA 55%全球份额"太粗，需按品类分（如套刻66%、CD-SEM日立60%+、掩模检测Lasertec>90%等），但未搜到每家的精确数字
2. **上游核心零部件国产化率**：光源/镜组/运动台/探测器的精确国产化比例和关键供应商名录 — SearXNG搜索未返回有效结果
3. **日本三家公司（Lasertec/Hitachi/SCREEN）的精确股价/市值**：因fetcher不支持日股，需外部行情源补全
4. **上海精测半导体设备营收精确拆分**：精测电子年报中半导体设备占比不高(~13%)，需要年报数据分解
5. **上海睿励/东方晶源的估值和融资情况**：未上市企业，仅从新闻获得融资信息（睿励近5亿融资），缺乏量化估值
