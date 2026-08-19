# 猎犬 Beta 2

agent驱动选股引擎。主agent读「模式/🧭调度协议」派子agent，子agent读「技能包/」7个lens做判断。

## 运行

1. 数据层：cd 本目录 python3 调 HoundFetcher（见调度协议§2）
2. SearXNG：本机 localhost:4000
3. 入口：对话里告诉主agent要扫什么，主agent按调度协议路由

## 与 Beta1 区别

Beta1=Python算分死逻辑(冻结存档)；Beta2=判断在子agent读SKILL。

## 文档

| 链接 | 说明 |
|------|------|
| `模式/🧭调度协议 > 猎犬/SKILL.md` | 主agent调度协议（§0-§8 完整，含组合配方库） |
| `docs/sample_chain_card.md` | 光谱→游丝串联样板 |
| `../技能包/` | 7个lens技能（光谱/游丝/价值/动量/资金/套利/催化） |
