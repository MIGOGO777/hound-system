# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 所有子 agent 自动继承本文件。保持精简。

## 定位

独立选股引擎 — 7个技能镜头扫描市场，输出「议题卡」给 M2 决策层。**Beta 2 是 agent 驱动系统，不是 Python 脚本**：主agent 读调度协议派子agent，子agent 读技能包 SKILL 做认知判断，回主agent审核。

## 架构心智模型（读多个文件才懂的大局，先建立这个）

五层，判断与取数严格分离：

```
① Python数据层(猎犬 Beta 2/hound_system/data)  只取数,绝不算分
② Python初筛器(.../universe/screener.py)        只剔ST/停牌/低流动性,客观质检
③ 7个技能 SKILL(技能包/)                         单镜头认知框架,子agent读它做判断
④ 调度协议 SKILL(模式/🧭调度协议 > 猎犬/SKILL.md) 主agent操作手册+配方库
⑤ 主agent审核汇总 → 议题卡(11字段)
```

**§0 铁律（最高优先级，违反=错）**：判断永远在子agent读SKILL时发生。主agent只编排「取数+派发+合流」，**绝不自己写阈值**（不写 PE<15、super_net>0、动量前30% 这类机械筛选）。"什么叫低估/强势/流入"由子agent判断。这正是 Beta 1 的病（判断被写死成Python阈值算分），Beta 2 为治此病而生。

**两类镜头，两条数据路线**：
- 个股级（价值/动量/资金/催化/套利）→ 走 `HoundFetcher`（fetcher，结构化数据）
- 主题级（光谱/游丝）→ 走 SearXNG（`http://localhost:4000/search`，搜索）。⚠️ 默认不加 `time_range`（会把无日期中文页一刀切光），首轮空三轮重试。

**组合配方 = 三机制**（§7 配方库，按机制分章）：
- ①取交集型：A、B各自独扫取同code交集（如 资金+价值）
- ②时序触发型：一先一后看时间错位，**禁止机械取交集**（如 催化→动量，机械取交集会漏最佳买点）
- ③映射串联型：主题级→个股级跨类，经映射环落地（如 光谱→个股 选股主干道）

## 路径

| 路径 | 说明 |
|------|------|
| `技能包/` | 7个技能 SKILL.md（外层共享，Beta1/Beta2 共用，认知层） |
| `模式/🧭调度协议 > 猎犬/SKILL.md` | 主agent调度协议（§0角色/§1意图路由/§7配方库/§8降级，完整） |
| `猎犬 Beta 2/hound_system/` | Python 数据层(data/) + 初筛器(universe/) |
| `猎犬 Beta 2/docs/` | 实战样板卡(sample_*_card.md) |
| `_archive/猎犬 Beta 1/` | 旧Python工程，**冻结存档**，可回溯对照，不改不删 |
| `Save.md` | 项目存档点（多coco跨会话交接板，苏醒先读） |

## 常用命令（在 `猎犬 Beta 2/` 目录下跑）

```bash
# 数据层健康检查（确认底座活着）
python3 -c "from hound_system.data.fetcher import HoundFetcher; print(HoundFetcher().health_check())"
# 跑初筛得候选池(~4000只,约15s,不封IP)
python3 -c "from hound_system.data.fetcher import HoundFetcher; from hound_system.universe.screener import UniverseScreener; print(len(UniverseScreener().get_universe(HoundFetcher())))"
# SearXNG 搜索(光谱/游丝用)
curl -s "http://localhost:4000/search?q=关键词&format=json&language=zh-CN"
```

**关键约束**：复制/移动数据层必须保留 `hound_system` 包名（fetcher.py 硬编码 `from hound_system.data import stock_data`）。集思录cookie只在sui本机有效（套利配方依赖）。

## 多coco协作 + 并发

三个 coco 形态分工协作，各司其职：

| coco | 形态 | 职责 | 在猎犬项目里干什么 |
|------|------|------|------------------|
| 🔴 **red** | Architect 决策 | 收敛、定方向、审查 | 出架构决策、定配方机制、审查子agent回执、诚实标瑕疵 |
| 🟢 **green** | Explorer 发散 | 挑战假设、扩可能性、找隐藏路径 | 体检配方同构性、挖出"缺8个跨类组合"盲区、提替代组织思路 |
| 🟣 **purple** | Builder 执行 | SDD 派子agent实战、产出验证 | 按plan跑配方验证、出样板卡、4项合规审查 |

**典型协作链**：red定方向 → green发散挑战 → red收敛定稿 → 写plan → purple(SDD)执行 → red审查回执。交接经 `Save.md` 顶部交接段 + 末尾回执段闭环，每次换形态/换会话都靠它续接。

**🟣 purple 模型映射（执行验证时）**：
- 主模型：Opus → 映射 **DeepSeek V4 Pro**（主agent，负责编排/派发/审查/对话，**本身不并发**，单线）
- 子agent模型：Sonnet → 映射 **DeepSeek V4 Flash**（被派出去读SKILL做判断的侦察兵，**并发在这一层实现**）

- **并发模型**：主agent(V4 Pro)不并发，它负责把多个子agent(V4 Flash)派出去；**并发由 Flash 子agent 层实现**（2026-06-29 实测：主agent一轮派3个Flash子agent，启动差<5s全部并发完成）。早期"不支持并发"结论已推翻。
- 🔑 **并发用法**：互不依赖的子agent 在同一轮用多个 Agent tool call 同时派出（不串行等），墙钟=最慢那个而非累加；依赖前置输出的（如三段串联配方）仍分步。
- **当前opus不支持真并发**：派多个子agent（如全市场扫描、配方实战验证）必须换 sonnet，否则超时。

## 12 条 Builder 规则（浓缩版）

### 基础编码
1. **先想再写**：不确定就问，暴露权衡，不靠猜
2. **简洁优先**：最少代码解决问题，不写投机功能，不做单次使用抽象
3. **外科手术**：只碰必须改的，匹配现有风格，不顺手重构
4. **目标驱动**：定义成功标准，循环迭代直到验证通过

### AI 代理协作
5. **确定性逻辑写代码**：重试/路由/阈值 = 显式代码，不是模型判断
6. **硬 Token 预算**：代码修复 ≤3轮/30min，超出即停汇报
7. **暴露冲突**：发现矛盾模式时标记出来等决策，不自行选择
8. **先读再写**：检查是否已有相同功能，不造轮子
9. **测试有意义**：验证行为属性（值/结构/副作用），不只为"不报错"
10. **检查点**：>3步或>3文件，每步汇报进度；失败回滚
11. **惯例优先**：遵循现有命名/架构，不引入第二种模式
12. **失败显性化**：错误必须抛出/上报，不确定就说"不确定"，严禁默认成功

## 语言

中文回复。代码注释可用中文。
