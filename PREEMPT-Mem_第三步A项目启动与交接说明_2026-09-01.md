# PREEMPT-Mem 第三步 A 项目启动与交接说明

> 日期：2026-09-01  
> 目标会议：ICLR 2027  
> 当前准入判决：`GO_3A_WITH_REQUIRED_REVISIONS`  
> 本文件用途：供全新 Codex 窗口直接接管项目，不重新选题、不重复已经完成的宽泛调研。

## 1. 项目目标

PREEMPT-Mem 研究容量受限的显式外部 Agent memory：当系统准备淘汰一条 memory 时，不只依据 recency、frequency、similarity 或一般 importance score，而是在真实 future trigger 尚未出现前，为该候选生成可执行的 Future Decision Witness，并通过同一环境快照下的 Full/Evicted 配对执行估计删除损失；Restore 只用于恢复一致性检查。验证信号最终服务于 memory budget 与 counterfactual-testing budget 双重约束下的 retention。

当前唯一安全的核心表述是：

> 在真实 trigger 尚未出现时，针对每个候选 external memory item 生成候选特异、可执行且可证伪的 Future Decision Witness；随后在相同 future-task checkpoint 上实施可审计的 item-level effective eviction，以 Full–Evicted 配对估计主要 deletion effect，并仅用 Restore 作为 recovery/symmetry control；以需要该 memory 的未来任务为条件测量 severe loss，最终在 memory budget 与 witness/testing budget 的双重约束下决定 retention。

FMEA 不是核心 novelty，只能作为可选 Prospective Risk Triage 的设计来源；不使用传统 `RPN = Severity × Occurrence × Detection`。

## 2. 当前所处阶段

项目已完成：

1. 研究方向和对象选择；
2. 第一轮文献与概念调查；
3. 数据、源码与现象验证方案审计；
4. 独立复核与交叉复核；
5. 第三步 A 准入判断。

尚未完成：

1. AppWorld 真实安装、数据结构与 checkpoint/evaluator 集成验证；
2. 外部 memory store 的 item-level effective eviction/restore；
3. workflow、gotcha、constraint/permission 三个 Smoke cases；
4. 任何可以写入论文的现象或方法实验结果。

因此当前处于：

> **第三步 A——AppWorld 数据结构与 Full/Evicted/Restore 三分支机制 Smoke 的实现与验证阶段。**

本阶段不是完整 Pilot，更不是正式主实验。

## 3. 新窗口必须读取的文件

### 3.1 最高优先级：本轮事实来源

按以下顺序完整阅读：

1. `PREEMPT-Mem_第三步A项目启动与交接说明_2026-09-01.md`
2. `research/PREEMPT-Mem_第二步_数据源码与现象验证审计.md`
3. `research/PREEMPT-Mem_已完成内容独立复核报告.md`
4. `research/PREEMPT-Mem_第二步交叉复核与第三步A准入意见.md`

如果这些文件当前位于项目根目录而不是 `research/`，先定位真实路径，不要因为路径不同重新开始工作。

发生冲突时，优先级为：

1. 本启动说明中限定的本轮任务范围；
2. 交叉复核与第三步 A 准入意见；
3. 独立复核报告；
4. 第二步数据源码审计；
5. 更早的可行性、Story 和构思文件。

### 3.2 建议一并提供，但不是本轮重新审查对象

- `research/PREEMPT-Mem_第一步_文献调查与概念梳理.md`
- `preempt可行性报告_v1.1.md`
- `论文完整story_v1.1.md`
- `ICLR2027-PREEMPT-Mem_新项目续研指令_v1.2.md`
- `PREEMPT-Mem_ICLR论文结构与内容规划.md`
- 仓库中的 `AGENTS.md`、`PROJECT_GUIDE.md`、`README.md`、环境配置和当前状态文件（若存在）

早期文件只提供背景，不得覆盖后续复核已经冻结的边界。

## 4. 启动 3A 前必须吸收的 required revisions

不要修改两份原始审计报告；新建修订附录或协议冻结文件完成以下内容：

1. 补入并冻结七项强近邻矩阵：OSL-MR、CMI、MEMAUDIT package-oracle、Proactive Memory Agent、PREPING、ASSAY、When Retrieval Fails Before It Begins；
2. 将未取得一手证据的 `What Eviction Destroys` 标为 unverified lead，不用于核心 novelty；
3. 冻结八项组合限定：unseen trigger、candidate-specific、executable witness、item-level effective eviction、Full–Evicted 主效应、Restore recovery control、conditional severe loss、memory/testing dual budgets；
4. 明确研究对象为 external addressable episodic/semantic memory；active context 只是暴露层；
5. 将 AppWorld 3A 标为 adapted + constructed/semi-synthetic mechanism smoke，禁止声称 natural cross-task lifecycle；
6. 冻结三个 case 的 source memory、target dependency、Need、evaluator、共享/隔离状态与构造类型；
7. 冻结 generator/evaluator 防火墙；witness generator 不得看到 hidden target、gold state、Need/criticality 和 evaluator 私有信息；
8. 冻结 effective-eviction manifest；
9. 保持 FMEA 为可选 triage schema，Pilot 时补入 generic risk triage 基线。

## 5. 本轮需要完成的具体任务

### 5.1 仓库与环境检查

1. 阅读仓库级指令文件；
2. 检查 `git status`，保留用户已有修改，不覆盖无关文件；
3. 定位 AppWorld 版本、安装方式、数据 bundle、task/schema/evaluator 入口；
4. 核查 task、scenario、variation、user、database state 的真实关系；
5. 用源码确认 task-specific DB、initialization、`save_state/load_state` 或等价 reset/replay 接口；
6. 记录 Python、AppWorld、Agent/model、依赖版本与运行命令。

### 5.2 最小外部 memory 干预层

实现最小但可审计的 memory record 和控制接口，至少包含：

- 稳定 `memory_id`；
- 内容与类型；
- provenance/source episode；
- agent-visible metadata 与 evaluator-only metadata 分离；
- insert/get/search/evict/restore；
- production store 与 agent 不可访问的 immutable audit archive 分离；
- 重建或清除 embedding/keyword/graph index；
- 清除 retrieval cache、tool cache、summary、active context 和所有派生记录。

不需要训练模型，不需要构建通用 memory platform，只实现支持三个案例的最小闭环。

### 5.3 三个 Smoke cases

只构造并运行：

1. workflow；
2. gotcha；
3. constraint/permission。

每个 case 必须标记为 `natural`、`adapted` 或 `constructed`；按当前 AppWorld 边界，预计主要是 adapted/constructed，不要为了追求“自然”而阻塞机制验证。

每个 case 从同一 future-task checkpoint 运行：

- **Full**：候选 memory 在正常 store/index 中可用；
- **Evicted**：候选 memory 及其所有 agent-reachable 派生信息均不可达；
- **Restore**：仅恢复同一 item、ID、原文、metadata 和索引配置。

唯一主要处理效应是 `Full−Evicted`。Restore 只检验恢复一致性，不作为第三个方法优势。

### 5.4 证据与日志

每个案例至少保存：

- memory provenance 与 source episode；
- source→future-task relationship；
- case 类型；
- 环境 snapshot/checkpoint 标识；
- prompt 与 prompt hash；
- retrieval result/trace；
- tool calls；
- database state diff；
- evaluator test vector；
- seed、模型、环境和依赖版本；
- 三分支执行顺序；
- leakage manifest；
- stdout/stderr 与运行命令；
- infrastructure failure 与 task failure 的区分。

## 6. 第三步 A 验收标准

3A 通过需要同时满足：

1. 至少 2/3 案例中 Full 与 Restore 结果一致；
2. Evicted 相对 Full 出现可解释的任务失败、约束违反或严重状态差异；
3. effective eviction 泄漏为 0；
4. evaluator 能从相同 snapshot 稳定复现；
5. Full、Evicted、Restore 除目标 memory 可达性外不存在其他有意 treatment difference；
6. 所有案例的构造类型与因果限制被如实报告。

若 Full 没有检索到 memory，不要把零效应直接解释为 memory 不关键。可增加一个仅用于诊断、不进入主效应的 forced-exposure 运行，以区分 retention、retrieval 和 utilization failure。

## 7. 本轮必须生成的产物

1. `research/PREEMPT-Mem_第二步结论修订附录.md`
2. `research/PREEMPT-Mem_第三步A_AppWorld结构与三分支Smoke审计.md`
3. 三个最小案例的数据/配置；
4. 外部 memory 干预与 AppWorld 三分支 harness；
5. 可复现命令、原始日志、state diff、evaluator 和 leakage manifest；
6. 必要的最小测试；
7. 更新项目状态文件（若仓库已有该机制）。

完成后停止，等待独立复核。不得自动扩展到完整 40-memory Pilot。

## 8. 自主推进与加速授权

在不越过任务范围、安全边界和数据权限的前提下，Codex被授权：

- 自主阅读项目与依赖源码；
- 使用官方文档、论文和仓库定位兼容性问题；
- 安装或修复本轮必要依赖；
- 编写最小实现、测试、配置和日志工具；
- 对失败案例进行根因定位并作可逆修复；
- 在不改变科学问题的情况下调整 case 细节、接口和工程实现；
- 主动选择最小可行方案，连续推进，不为普通技术选择逐项请求确认。

遇到问题时按以下顺序处理：

1. 复现并保存最小错误；
2. 检查本地源码、版本、官方文档和已知 issue；
3. 判断是环境、数据、memory adapter、retrieval、evaluator 还是 Agent 行为问题；
4. 实施最小、可逆、带测试的修复；
5. 重跑受影响案例并记录前后差异；
6. 只有形成真实阻塞时才停下报告。

以下情况必须暂停并向用户请求决定：

- 缺少必须的账号、API key、受保护 AppWorld bundle 或数据授权；
- 需要破坏性删除、覆盖用户文件或修改不可恢复资产；
- 需要从 AppWorld 切换到其他主环境；
- 需要改变核心研究问题、数据口径或准入标准；
- 需要启动完整 Pilot、训练或大规模付费实验；
- 发现完整核心论文碰撞或三分支存在无法修复的因果错误。

“案例不够自然”“协议还可以更完美”“可能存在一般性风险”不是暂停 3-case Smoke 的充分理由；应如实标记限制并继续完成最小机制验证。

## 9. 本轮禁止事项

- 不重新选题；
- 不把 FMEA 写成核心 novelty；
- 不声称单项 counterfactual、future utility、proactive memory 或 rare-important 为首次提出；
- 不修改或覆盖两份原始审计报告；
- 不启动 40-memory Pilot、训练或大规模 GPU 实验；
- 不使用平衡数据估计 prevalence；
- 不让 witness generator 接触 hidden target/evaluator 私有信息；
- 不将 Restore 当作第三个主要效应；
- 不将 constructed AppWorld case 表述为自然企业 memory lifecycle；
- 不以空泛风险讨论替代源码检查、最小实现和实际运行。

## 10. 完成后的汇报格式

最终仅汇报：

1. 完成了什么；
2. 具体修改文件；
3. 三个案例的 Full/Evicted/Restore 结果；
4. leakage、Restore consistency 和 evaluator stability；
5. 实际运行命令与日志位置；
6. 3A 是否通过；
7. 若未通过，阻塞属于环境、实现、数据还是核心假设；
8. 是否建议进入独立复核。

不要用计划代替结果，不要在本轮完成后自动进入下一阶段。

## 11. 新 Codex 窗口首条指令

```text
请完整阅读项目中的《PREEMPT-Mem_第三步A项目启动与交接说明_2026-09-01.md》，并按其中的文件优先级继续 PREEMPT-Mem。不要重新选题，不要重复已完成的宽泛文献调查，也不要用早期文件覆盖交叉复核结论。

当前判决为 GO_3A_WITH_REQUIRED_REVISIONS。先吸收 required revisions 并建立第二步结论修订附录，然后直接执行第三步 A：核查 AppWorld 真实源码/数据结构，建立最小 external addressable memory 干预层，构造并运行 workflow、gotcha、constraint/permission 三个 Full/Evicted/Restore Smoke cases，保存可复现配置、日志、retrieval trace、tool calls、database state diff、evaluator test vector 和 effective-eviction leakage manifest。

本轮目标是尽快获得真实运行证据。你可以自主查源码、阅读官方文档、安装必要依赖、修复兼容性、编写最小代码和测试、调整可逆的工程实现，并主动定位和解决普通技术问题，不必为每个小问题等待确认。只有缺少凭证/受保护数据、需要破坏性操作、需要更换 AppWorld 主轨、改变核心协议，或准备扩展到完整 Pilot/训练/大规模付费实验时才暂停询问。

AppWorld 案例允许 adapted/constructed；不要因为缺少完美自然生命周期而阻塞 Smoke。必须保持：Full−Evicted 是主要效应，Restore 只作 recovery/symmetry control；effective eviction 清除索引、缓存、summary、active context 和派生信息；witness generator 与 hidden target/Need/gold evaluator 严格隔离。

完成规定产物后停止，不启动完整 40-memory Pilot，等待独立复核。开始时先用不超过 12 行报告：已读取文件、仓库状态、当前阶段、执行顺序和第一个实际动作，然后立即推进。
```
