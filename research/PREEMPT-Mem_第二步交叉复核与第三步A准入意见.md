# PREEMPT-Mem 第二步交叉复核与第三步 A 准入意见

> 复核日期：2026-08-27  
> 复核对象：`research/PREEMPT-Mem_第二步_数据源码与现象验证审计.md`、`review/PREEMPT-Mem_已完成内容独立复核报告.md`  
> 审查性质：只读、独立交叉复核；未修改既有报告，未执行实验、未实现代码、未重新寻找研究 Idea。  
> 准入对象：第三步 A——AppWorld 3-case Smoke，而非 40-case Pilot 或正式主实验。

## 1. 结论摘要

第二步报告已经建立了可执行的三分支因果骨架：同一 checkpoint 下的 Full、Evicted、Restore，主要效应为 `Full−Evicted`，Restore 用于恢复/对称性检查，并且给出了较完整的 effective eviction 泄漏面、条件严重度、witness 与隐藏未来任务分离、80→40 的候选筛选流程和不使用传统 RPN 的 FMEA 边界。这些内容足以支持一个最小机制 smoke。

但第二步报告尚未完整满足无条件准入：七项强近邻没有进入其核心邻近工作表；AppWorld 的跨任务生命周期被描述得比官方基准原生支持的范围更强；安全 novelty 的完整组合没有在单一冻结表述中逐项写全；80/40 的 prevalence 口径仍可能被误读；generic risk triage 基线缺失。上述问题均可通过协议冻结和措辞修订解决，当前未发现完整核心碰撞、三分支不可执行，或无法修复的因果错误。

因此，本意见允许在完成第 10 节列出的 3A 前置修订后进行 3-case Smoke；它不授权直接进入 40-case Pilot，也不授权把 smoke 结果表述为 natural long-term lifecycle 或自然 prevalence 证据。

## 2. 一手核验范围与证据等级

本复核实际核验了下列一手来源：

- AppWorld 的 [ACL 2024 正式论文](https://aclanthology.org/2024.acl-long.850/)、[论文 PDF](https://aclanthology.org/2024.acl-long.850.pdf) 与[作者官方仓库](https://github.com/StonyBrookNLP/appworld)。
- 七项强近邻的 arXiv 正文/摘要页；存在作者代码链接时，进一步检查作者仓库或论文所列代码入口。
- `What Eviction Destroys` 所给 OpenReview 入口及公开网页精确题名检索。

证据分级如下：

- **P1**：论文正文/正式出版页/作者官方仓库/官方数据页面；可支撑事实与边界判断。
- **P2**：arXiv 摘要页或论文明确列出的但暂不可访问的代码入口；可支撑题名、作者、提交状态和摘要范围，不单独支撑细粒度实现结论。
- **U**：无法取得正文、作者和发表状态的线索；不得支撑核心 novelty。

## 3. 八项准入条件交叉核对

| 检查项 | 第二步报告现状 | 独立复核结论 | 准入处理 |
|---|---|---|---|
| 七项强近邻 | 核心邻近表未纳入 OSL-MR、CMI、MEMAUDIT package-oracle、Proactive Memory Agent、PREPING、ASSAY、When Retrieval Fails Before It Begins；其中现有的 “MemAudit” 是 contamination/poisoning 方向，不是 package-oracle 工作 | **未满足**。七项均为真实且相关的一手工作；ASSAY、PREPING 与 AppWorld 的重合尤其必须显式处理 | 3A 前冻结邻近矩阵与组合 novelty；不要求重选题 |
| `What Eviction Destroys` | 已标注未核实，但仍把它描述为最接近 Restore 的线索 | **未满足一手核验条件**。正文、作者、发表状态均未取得 | 从核心 novelty 证据链中剔除，仅保留为 `unverified lead` |
| 安全 novelty | 各组件散落在多节；末端安全表述没有逐项写全 candidate-specific、item-level、Restore-control 和双预算 | **部分满足**。组合仍有安全空间，但单项 novelty 已被多篇近邻占据 | 采用第 6 节唯一安全组合，不再主张单组件首创 |
| AppWorld 生命周期 | 正确核验了 reset/checkpoint/state test，但由此进一步推到跨任务长期记忆主轨 | **部分满足**。分支机制可做；原生 natural cross-task dependency 未被证明 | 3A 必须标为 adapted + constructed/semi-synthetic，不得标为 natural |
| rarity / criticality | 已给 Need 分母、40-task 阈值、条件严重度和 retrieval-proxy 限制；时间窗与候选抽样框仍不够锁定 | **部分满足**。总体框架非循环，但仍需冻结抽样分布、事件/时间范围和 generator/evaluator 防火墙 | 3A 不估 prevalence；Pilot 前补全第 8 节定义 |
| Full/Evicted/Restore | 明确 `Full−Evicted` 主效应、Restore 恢复控制、同 checkpoint/seed、泄漏审计 | **基本满足** | 3A 前将 effective eviction 转成逐项可审计 manifest |
| 80 与 40 | 先建 80，再按四象限平衡到 40；但指标清单仍单列 “rare-critical prevalence” 而未锁死来源 | **部分满足** | prevalence 只能来自预先定义抽样框中的未平衡 80；平衡 40 禁止估计自然 prevalence |
| FMEA | 明确可选、非 novelty、不用传统 RPN，并有 severity-only / random 等比较 | **基本满足但基线不全** | 增加 generic risk triage；3A smoke 不以 FMEA 优越性为目标 |

## 4. 七项强近邻的实际核验与碰撞判断

### 4.1 邻近矩阵

| 工作与一手来源 | 已核验的核心范围 | 与 PREEMPT-Mem 的重合 | 尚未覆盖的完整组合要素 | 碰撞结论 |
|---|---|---|---|---|
| [OSL-MR / Learning What to Remember](https://arxiv.org/abs/2606.10616)，Kang et al.，arXiv 2026 | 未知未来需求下的 long-horizon retention、硬预算、可观测性安全、延迟 miss/reacquisition/staleness 成本；LoCoMo/LongMemEval | unseen future、预算化 retention、长期代价 | candidate-specific executable witness、工具任务中的 item deletion、Restore、条件严重损失、测试预算 | 强近邻，不构成完整碰撞 |
| [Causal Memory Intervention](https://arxiv.org/abs/2605.17641)，Srivastava，arXiv 2026；[作者代码/数据仓库](https://github.com/Saksham4796/causal-memory-intervention) | 对当前请求下的候选 memory 做有/无/扰动干预，选择能改善回答的 memory；Causal-LoCoMo | item-level causal memory effect | trigger 未知时的 witness、跨任务执行、Restore recovery、rarity/criticality、双预算 | 强近邻；禁止把“对 memory 做因果干预”写成 novelty |
| [MEMAUDIT package-oracle](https://arxiv.org/abs/2605.02199)，Bhargava & Barrento，arXiv 2026 | 未知未来 query 前的预算化 memory writing；固定候选表示、成本、未来需求与 exact package optimum | future-unknown、memory budget、候选保留优化、可审计 denominator | executable decision witness、真实 agent task deletion effect、Restore、conditional severe loss、testing budget | 强近邻；禁止把“未知未来下预算写入”写成 novelty |
| [Proactive Memory Agent](https://arxiv.org/abs/2607.08716)，Wu et al.，arXiv 2026；[作者官方代码](https://github.com/yifannnwu/proactive-memory-agent) | 在长轨迹中维护结构化 memory bank，并决定何时注入 memory-grounded reminder；Terminal-Bench 2.0 / τ²-Bench | 决策相关记忆、主动触发/干预、执行型 agent | 跨独立任务 retention、item eviction CF、Restore、rarity 与双预算 | 强近邻；禁止把“主动让记忆影响决策”写成 novelty |
| [PREPING](https://arxiv.org/abs/2605.13880)，Choi et al.，arXiv preprint 2026 | 在目标任务出现前，用 proposer 生成 synthetic practice，solver 执行、validator 过滤，构建 procedural memory；评测含 AppWorld | pre-task generation、synthetic executable practice、AppWorld、memory construction | 针对每个候选 memory 的反事实 witness、effective deletion、Restore、条件严重损失、双预算 retention | 很强近邻；“目标任务前生成练习/测试”本身不再安全，只能保留 candidate-specific audit witness 的组合差异 |
| [ASSAY / Not All Skills Help](https://arxiv.org/abs/2606.15390)，Wang et al.，arXiv 2026 | 在小型 dev set 上随机 mask 技能、估计 per-skill causal attribution、离线修复库，并针对 test task 做 masking；AppWorld / τ-bench | AppWorld、item/skill-level masking、因果异质性、任务特异保留 | unseen-trigger witness、严格 Full–Evicted 配对与 Restore、rare conditional severe loss、memory/testing 双预算 | 当前最强实现邻近之一；不构成完整组合碰撞，但显著压缩单项 novelty。论文列出的代码 URL `https://github.com/aiming-lab/assay` 在复核日返回 404，故实现细节仅按正文核验 |
| [When Retrieval Fails Before It Begins](https://arxiv.org/abs/2608.20400)，Song，arXiv 2026；ICML 2026 FAGEN workshop non-archival；[复现仓库](https://github.com/smkgenesis/dsgc) | 固定 prompt budget 下，结构上必要但与 query 弱相关的 prerequisite 在 retrieval 前被错误淘汰；给出 DSGC 与确定性基准 | retention-stage eviction failure、预算、依赖项/组效应、相似度代理失真 | 真实工具执行下的 item-level三分支、Restore、主动 witness、条件严重度、测试预算 | 强支持“frequency/similarity 不是 rarity/价值真值”；不构成完整碰撞 |

### 4.2 对第二步结论的修正

第二步报告当前的“未发现直接完整碰撞”方向可以保留，但其证据不完整，不能在缺少上述七项的情况下视为冻结查新结论。补入七项后，仍未发现同时覆盖以下全部维度的工作：未知 trigger、候选特异 witness、有效删除、三分支配对、条件严重损失和双预算 retention。

因此，问题是 **novelty 边界未充分冻结**，不是已发现完整核心碰撞。尤其应取消以下单项首创暗示：

- 未知未来需求下的预算 retention；
- 对单个 memory/skill 做 causal masking 或 intervention；
- 在目标任务前生成 synthetic executable practice；
- 主动把 memory 注入 agent 决策；
- retrieval 前的 prerequisite eviction failure；
- 在 AppWorld 上做技能/记忆库筛选。

## 5. `What Eviction Destroys` 核验结论

截至复核日：

- 所给 [OpenReview forum](https://openreview.net/forum?id=8rOh73WoJh) 与 [PDF](https://openreview.net/pdf?id=8rOh73WoJh) 均只返回浏览器验证页；
- 精确题名公开检索未得到稳定的 arXiv、正式出版、作者主页或作者仓库记录；
- 因而未取得可核验的一手正文、作者名单或发表/投稿状态。

处理规则：将该项定为 **U（unverified lead）**。它不得用于证明 Restore、deletion effect 或 PREEMPT-Mem 的核心 novelty，也不得成为“无碰撞”的必要前提。后续即使取得材料，也必须重新与 ASSAY、CMI 及本项目的 Full/Evicted/Restore 角色逐项比较；本轮不据此阻断 3A。

## 6. 唯一安全的 novelty 冻结表述

当前可安全主张的对象不是任一单组件，而是以下完整组合：

> 在真实 trigger 尚未出现时，针对每个候选 memory item 生成候选特异、可执行且可证伪的 Future Decision Witness；随后在相同未来任务 checkpoint 上实施可审计的 item-level effective eviction，以 Full–Evicted 配对估计主要 deletion effect，并仅用 Restore 作为 recovery/symmetry control；以对 memory 必要的未来任务为条件测量 severe loss，最终在 memory budget 与 witness/testing budget 的双重约束下决定 retention。

该表述必须同时保留八个限定词：

1. `unseen trigger`；
2. `candidate-specific`；
3. `executable Future Decision Witness`；
4. `item-level effective eviction`；
5. `Full–Evicted paired primary effect`；
6. `Restore recovery control`；
7. `conditional severe loss`；
8. `memory/testing dual budgets`。

删去其中任何关键限定后，都可能落入 OSL-MR、CMI、MEMAUDIT、Proactive Memory Agent、PREPING、ASSAY 或 DSGC 已覆盖的范围。FMEA 不属于该 novelty。

## 7. AppWorld 生命周期与三分支可行性

### 7.1 官方能力事实

AppWorld 官方论文与仓库能够支持以下事实：

- 9 个日常应用、457 个 API、约 100 个虚构用户和 750 个任务；
- 任务结果可由数据库状态单元测试评估，并检查 collateral damage；
- `AppWorld(task_id=...)` 会把应用重置到该 `task_id` 特定的数据库和时间，并建立独立输出目录；
- 不同任务具有不同 DB；官方论文进一步说明每个任务由 Base DB 的 task-specific copy 与独立起始时间构成；
- 同一 `world` 内可通过 `save_state()` / `load_state()` 保存与回退数据库状态。

这些能力充分支持 **可重复分支执行和状态结果判定**，但不自动产生跨任务长期记忆依赖。

### 7.2 三类证据必须区分

| 类型 | 对 AppWorld 的结论 | 本项目允许的表述 |
|---|---|---|
| natural | AppWorld 的单任务场景和用户活动具有自然化设计；但官方 benchmark 没有冻结同一用户的有序独立任务流，也未保证任务 A 的历史 memory 是任务 B 的必要信息 | 不得把 3A 称为 natural cross-task lifecycle |
| adapted | 可以选择相同用户/应用域、重用环境规则或经过显式状态桥接，把多个 episode 组织成一个 lifecycle | 必须公开桥接规则、来源 episode、目标任务和持久化边界 |
| constructed / semi-synthetic | 3A 可人为构造 constraint、workflow、gotcha 三种 source→future dependency，并借助 AppWorld 工具执行与 state test 判定结果 | 这是 3A 的正确定位：机制 smoke，而非自然 prevalence 或生态有效性证据 |

### 7.3 3A 可行但有硬边界

三分支本身可行：外部 memory store 在同一 future-task checkpoint 上分别保留、有效删除、恢复候选 item；AppWorld 的 state checkpoint 和 state-based evaluator 可固定环境并判定结果。

跨任务 lifecycle 则必须由项目显式构造。仅依次加载两个官方 `task_id` 会各自重置到不同 task-specific DB，不能证明 memory 的自然连续性。每个 3A case 必须在协议中写出：

- source episode 产生了什么候选 item；
- target episode/task 为何在没有该 item 时仍可运行、但在正确决策上对其具有独立定义的必要关系；
- source 与 target 是否共享用户、时间、DB 状态或仅共享外部 memory；
- 这种连接属于 adapted 还是 constructed/semi-synthetic；
- target 的 Need/evaluator 如何在 witness 生成前独立冻结。

## 8. rarity、criticality 与非循环性

### 8.1 已经正确的部分

第二步报告已正确做到：

- 用独立的 `Need(m, τ)` 而不是 retrieval count 定义任务是否需要 memory；
- 用需要该 memory 的未来任务数除以冻结任务流大小定义 rarity；
- 将 retrieval frequency 降级为 proxy，并报告 false-negative / miss；
- 用条件于 `Need=1` 的任务损失定义 severity/criticality；
- witness generator 不看隐藏未来任务、gold label 或未来轨迹，最终成败由隐藏 target task 的环境 evaluator 判定。

### 8.2 仍须冻结的内容

在 40-case Pilot 前，rarity 定义必须补齐：

- **任务分布**：哪些 AppWorld task/scenario/user/constructed variation 有资格进入未来任务流；
- **分母**：所有 eligible future task opportunities，而非发生检索的次数；
- **阈值**：若继续使用 `N=40`，明确 rare `≤2/40`、frequent `≥6/40`，中间带如何处理；
- **时间范围**：明确起止 episode、task index 或 simulated time window，不只写“生命周期内”；
- **抽样性质**：若任务流经过人为挑选，它只能给出 constructed sampling-frame rarity，不能外推自然 AppWorld prevalence。

criticality 可继续采用 0–4 条件严重度，但 `Need`、severity rubric、target evaluator 与 witness generator 必须版本冻结。Restore 成功可用于验证 effect 的可恢复性，不应反过来由 witness generator 决定 critical label。

防止自证循环的最低要求：

1. witness generator 只读取候选 item、允许的历史和公开环境 schema；
2. target task、Need label、gold state test 与 severity rubric 在 witness 输出进入 retention 决策前冻结；
3. generator 不得修改 target 环境或 evaluator；
4. evaluator 不得以 witness 文本相似度或 generator 自评作为成功依据；
5. 记录 generator/evaluator 的 prompt、版本、输入哈希和数据可见性。

3A 只有三个设计 case，不能估计 rarity 或 prevalence；它只检查上述接口是否能保持独立。

## 9. 因果角色、数据池与 FMEA

### 9.1 Full / Evicted / Restore

因果角色在第二步报告中基本正确，应原样冻结：

- `Full−Evicted`：主要 deletion effect；
- `Restore`：recovery/symmetry control，用于检查把同一 item 放回后是否恢复，不是主要效应，也不是额外方法优势；
- 三分支必须从同一 future-task checkpoint、相同环境 snapshot、seed、模型、工具预算和解码设置出发；
- Restore 只能恢复被删除的同一 item，不得顺带恢复其他上下文或换用更强 prompt。

effective eviction 必须形成逐 case 的 pass/fail manifest，至少覆盖：

- canonical memory record 与其别名/近重复副本；
- embedding/ANN/graph/keyword 索引和 reranker 派生特征；
- retrieval cache、tool cache、summary cache；
- active prompt、scratchpad、session/KV context 和运行中变量；
- 由该 item 派生的 summary、rule、skill、plan、edge、tag 与 cached answer；
- 可被 agent 访问的 archive、日志或 debug endpoint。

仅允许隔离且不可被 agent、retriever、summarizer 或 tool 调用访问的审计记录保留 ID/hash。若泄漏检查失败，该 triplet 无效，不能计入 deletion effect。

### 9.2 80 条与 40 条

第二步报告的“先 80、后平衡 40”顺序正确，但统计用途必须锁死：

- **80 条未平衡候选池**：保留完整筛选流和四象限原始计数；只有在抽样框与纳入概率预先定义、没有按 outcome 选择时，才能估计该抽样框内 prevalence。
- **40 条平衡分析集**：四象限各 10 条，属于 case-control / stress analysis set，只用于比较方法、机制与效应异质性；不得估计 rare-critical memory 的自然 prevalence。
- 由于 80 条本身来自 AppWorld 轨迹、失败样例和人为候选构造，它也不能无条件外推为“自然 AppWorld prevalence”；最多报告“在预注册候选生成与采样框中的 prevalence”。

所有 prevalence 指标必须明确标注分母为 80 候选池还是完整 eligible stream，绝不能使用平衡 40 的 `10/40` 等比例。

### 9.3 FMEA

第二步报告已正确把 FMEA 限定为可选 triage schema，并拒绝传统 `RPN = S×O×D`。这一边界应保持：

- FMEA 不是核心 novelty，也不是 3A 成功条件；
- 不把 ordinal 乘积当作测量尺度；
- 后续至少比较 `severity-only`、`generic risk triage`、random 及非 FMEA retention 基线；
- 当前基线表已有 severity-only 和 random，但缺少明确的 generic risk triage，须在 Pilot 方案中补上。

## 10. Required revisions

下列修订不要求改写本轮已审查的两份原报告；可以在独立的 3A protocol freeze / manifest 中完成并与本意见共同作为准入记录。

### 10.1 启动 3A 前必须完成

1. **冻结七项邻近矩阵**：纳入 OSL-MR、CMI、MEMAUDIT package-oracle、Proactive Memory Agent、PREPING、ASSAY、When Retrieval Fails Before It Begins，并采用第 4 节的 collision 边界。
2. **排除未核实证据**：把 `What Eviction Destroys` 标为 U，不进入 novelty、方法动机或 Restore 先例的核心证据链。
3. **冻结完整组合 novelty**：逐字保留第 6 节八个限定，不再主张单组件首创。
4. **重标 AppWorld 证据类型**：3A 明确为 adapted + constructed/semi-synthetic 3-case mechanism smoke；禁止 natural lifecycle 表述。
5. **冻结每个 case 的 source→target dependency**：constraint、workflow、gotcha 各自列出 source item、target Need、独立 state evaluator、共享/隔离状态和构造方式。
6. **冻结三分支 manifest**：同 checkpoint、唯一 treatment difference、`Full−Evicted` 主效应、Restore 仅恢复控制，并逐项检查所有索引、缓存、summary、active context 和派生信息。
7. **冻结 generator/evaluator 防火墙**：target/gold/Need/severity 不向 witness generator 泄露，witness 不参与定义 evaluator success。
8. **限定 smoke 结论**：3A 只能回答“能否实施无泄漏三分支并观察可恢复的方向性 deletion effect”，不能回答自然 rarity、自然 prevalence、总体性能或 FMEA 优越性。

### 10.2 进入 40-case Pilot 前必须完成

1. 冻结 rarity 的任务分布、分母、阈值和 episode/time window；
2. 把 prevalence 的唯一允许来源绑定到预注册的未平衡候选池/eligible stream，并明确禁止使用平衡 40；
3. 冻结 memory budget 与 witness/testing budget 的独立计量单位和约束；
4. 在 FMEA/triage 比较中加入 generic risk triage；
5. 预注册 middle-frequency band、无稳定 Restore、泄漏失败和不稳定 triplet 的排除/报告规则。

## 11. 为什么不阻断 3A

本轮未发现需要阻断最小 smoke 的三类情形：

- **无完整核心碰撞**：七项强近邻分别覆盖了未知未来预算 retention、因果 masking、package oracle、主动干预、pre-task synthetic practice、AppWorld skill attribution 或 prerequisite eviction，但尚无一项覆盖第 6 节完整组合。
- **三分支可执行**：AppWorld 官方 checkpoint/revert 与 state-based tests 能固定环境分支；外部 memory 层可承担 item-level Full/Evicted/Restore。尚未验证的是实际集成与无泄漏，这恰是 3-case Smoke 应回答的问题。
- **因果错误可修复**：现有报告已把主效应与恢复控制区分开，剩余问题主要是 lifecycle 标注、信息防火墙和 leakage manifest 的协议冻结，不是不可修复的设计错误。

## 12. 最终判决

`GO_3A_WITH_REQUIRED_REVISIONS`
