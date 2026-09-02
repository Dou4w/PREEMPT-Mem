# PREEMPT-Mem 前期七项问题回答情况审计报告

> 项目：ICLR 2027 — PREEMPT-Mem  
> 审计日期：2026-08-27  
> 审计目的：逐项判断前期调研与 Idea 构思阶段提出的七个关键问题，是否已经被当前研究工作回答  
> 当前项目门禁：`GO_3A_WITH_REQUIRED_REVISIONS`

## 0. 审计材料与判定口径

本报告综合审查以下当前项目材料：

1. `PREEMPT-Mem_已完成内容独立复核报告.md`；
2. `PREEMPT-Mem_第二步_数据源码与现象验证审计.md`；
3. `PREEMPT-Mem_第二步交叉复核与第三步A准入意见.md`；
4. `PREEMPT-Mem_ICLR论文结构与内容规划.md`；
5. `PREEMPT-Mem_论文预期报告_论文介绍与贡献.md`。

本报告区分三种不同意义上的“已回答”：

- **概念回答**：已经给出清晰定义、范围和理论判断；
- **协议回答**：已经设计出可以验证问题的实验、数据和判定流程；
- **实证回答**：已经运行真实代码和实验，并得到可重复结果。

只有第三种才能写成论文的 supported claim。前两种只能写成 problem formulation、method design 或 evaluation plan。

---

## 1. 总体结论

### 1.1 一句话判断

> 七个前期问题在研究设计层面已经基本得到处理，但只有“研究哪一种 memory”被完整冻结；最关键的科学问题——rare-but-critical memory 是否在可信分布中真实、非单例且可重复地存在——仍未获得实验答案。

因此，当前项目状态不是“问题已经全部解决”，而是：

> **研究问题和验证方法基本闭环，实证证据尚未闭环。**

### 1.2 状态总表

下表中的完成度是项目管理意义上的主观估计，不是统计量。

| # | 前期问题 | 当前状态 | 估计完成度 | 是否阻塞 3A Smoke | 是否阻塞论文核心 claim |
|---:|---|---|---:|---:|---:|
| 1 | 文献、rare、importance、criticality 与源码 | **大部分回答，尚需冻结修订** | 80% | 否 | 是，投稿前必须完整闭环 |
| 2 | 是否先证明 rare-but-critical memory 存在 | **验证协议已完成，实证尚未开始** | 35% | 否 | **是，核心阻塞项** |
| 3 | 内部还是外部 memory | **已回答并冻结** | 95% | 否 | 否 |
| 4 | 无公司日志时从哪里获得 memory/数据 | **资源路径已回答，真实拼装未完成** | 70% | 部分 | 是，外部有效性仍受限 |
| 5 | 利用细微差异形成可 defend 的创新 | **已形成安全组合 claim，需持续查新** | 85% | 否 | 投稿前持续更新 |
| 6 | FMEA 是否可引入 Agent memory | **定位已回答，效果未知** | 60% | 否 | 否，FMEA 不是核心贡献 |
| 7 | 是否需构造/筛选暴露严重删除损失的数据 | **明确需要，协议已设计，数据未形成** | 65% | 是，需先完成 3A | **是** |

### 1.3 当前最重要的判断

七项问题中：

- 第3项已经完成；
- 第1、5项主要解决 novelty 和术语边界；
- 第4、7项解决数据从哪里来以及如何形成可执行实验；
- 第6项解决 FMEA 的地位；
- 第2项才是决定论文科学假设是否成立的核心实证门禁。

---

## 2. 问题一：文献、rare、importance、criticality 与源码

### 2.1 原始问题

需要调查现有 Agent memory 工作如何研究上下文和长期记忆；是否定义 rare-but-critical memory；如何定义 rarity、importance 和 criticality；必要时分析论文源码。

### 2.2 当前已经回答的部分

#### A. 已经建立 Agent memory 研究版图

当前工作已经把相关研究至少划分为以下几类：

1. **预算化 retention/memory management**  
   Memory-R1、AgeMem、TraceRetain、CURATOR、Learning What to Remember、OSL-MR、MEMAUDIT package-oracle。

2. **decision-centric 或 causal memory selection**  
   DeMem、Causal Memory Intervention、ASSAY、MemAudit poisoned-memory audit。

3. **主动 memory intervention 与任务前生成**  
   Proactive Memory Agent、PREPING。

4. **retention-before-retrieval failure**  
   When Retrieval Fails Before It Begins。

5. **遗忘造成的执行和治理后果**  
   Governance Decay/ConstraintRot，以及 AppWorld 中可被数据库状态 evaluator 检测的任务失败与 collateral damage。

因此，项目已经纠正了早期过宽的判断：不能再说“现有工作只研究历史或当前 relevance”，因为 OSL-MR 已研究未知未来需求，MEMAUDIT 已研究 future-query requirements，PREPING 已在目标任务出现前生成 synthetic practice，CMI/ASSAY 已做 item/skill-level 因果选择。

#### B. 已经回答“文献中是否存在统一的 rare 定义”

当前审计得到的结论是：

> 现有工作和综述已经识别“rare-but-important”“少访问但必要信息可能被淘汰”的问题，但尚不存在一个被 Agent memory 社区统一采用、能够直接支撑本项目的 rare-but-critical 操作定义。

已有工作中的 rare 往往对应：

- 历史访问频率低；
- retrieval count 低；
- query relevance 低；
- 在人为压力测试中出现次数少；
- 某类 prerequisite 与表面 query 弱相关。

这些都不能直接作为本项目的 rarity 真值，因为 retrieval 还受到 retriever、index、query 和 exposure 的影响。

#### C. 已经给出本项目的 rarity 定义

当前推荐定义是：对预先冻结的 future task stream \(T\)，使用与 retriever 行为独立的需求指示：

\[
Need(m,t)=1,
\]

表示任务 \(t\) 的正确决策是否需要 memory \(m\) 所表达的信息。

定义：

\[
RarityRate(m;T)=
\frac{\sum_{t\in T}Need(m,t)}{|T|}.
\]

因此：

- rarity 是 memory 相对于一个明确 future-task sampling frame 的属性；
- 它不是 memory 文本自身永久不变的属性；
- historical retrieval frequency 只能作为有偏 proxy；
- 必须同时报告 `NeedRate`、`RetrievalRate` 和 `Need=1 ∧ Retrieved=0` 的 retrieval miss。

#### D. 已经区分 importance 与 criticality

当前工作已经明确：

- **importance** 是上位概念或系统 heuristic，可能包含 relevance、salience、recency、historical utility、LLM rating 等；
- **observed utility** 是在已经发生的 query/task 上 memory 带来的性能差异；
- **criticality** 是在任务确实需要该 memory 的条件下，effective eviction 相对 Full 造成的严重损失；
- importance 不能与 rarity、causal forgetting loss 或 conditional severity 互换。

条件 criticality 可表达为：

\[
c_i=
\mathbb E[
L(A(M\setminus\{m_i\},z))-L(A(M,z))
\mid Need(m_i,z)=1
].
\]

这解决了低 occurrence 会把 high severity 压低的问题。

#### E. 已经完成一定程度的源码和官方资源审计

第二步审计已经检查多项论文的官方仓库、数据卡或实现状态，包括：

- LongMemEval-V2 的数据、harness、schema 和许可；
- Learning What to Remember 的公开 baseline 实现；
- Causal Memory Intervention 和 Proactive Memory Agent 官方仓库；
- AppWorld 的任务、API、数据库状态测试和 checkpoint/reset 接口；
- ALFWorld、WebShop、MemoryAgentBench 等备选资源；
- Memory-R1/AgeMem 的实现和许可可用性边界。

这已经超过只读论文摘要的阶段。

### 2.3 尚未回答或尚未冻结的部分

1. 第三步 A 尚未在本地真实安装和运行 AppWorld，因此当前只证明官方接口存在，未证明项目 adapter 能稳定接入。
2. AppWorld 的 task/scenario/variation/user/DB lifecycle 仍需运行时确认，尤其是不同 task 使用 task-specific DB 的影响。
3. 七项强近邻虽然已经由交叉复核补齐，但尚未写入统一的“第二步结论修订附录”。
4. `What Eviction Destroys` 仍是 `U/unverified lead`，不得进入核心证据链。
5. rarity 的 sampling frame、分母、时间窗和阈值必须在 40-case Pilot 前正式预注册。
6. 投稿前 Related Work 还应持续检查 DeMem、Policy-Carriage Integrity、TraceRetain 等邻近工作的更新，避免快速变化的 2026 文献继续压缩 novelty。

### 2.4 判决

**状态：`SUBSTANTIALLY_ANSWERED_WITH_FREEZE_PENDING`**

问题一已经在概念和审计层面得到大部分回答，但还不能视为完全结束。进入 3A 不受阻；进入正式 Pilot 和论文写作前，必须将修订后的近邻矩阵、定义和证据等级写入单一冻结文件。

---

## 3. 问题二：是否必须先证明 rare-but-critical memory 存在

### 3.1 当前给出的明确回答

答案是：

> **必须在提出和大规模比较 PREEMPT-Mem 之前，证明 rare-but-critical memory 在一个来源可信、非循环构造、可重复的研究分布中非平凡地存在；但不需要先证明它在所有真实公司 Agent 中普遍存在。**

这是“问题存在性验证”，不是“生产世界 prevalence 证明”。

### 3.2 当前已经完成的证明设计

项目已经设计出以下验证顺序：

1. 从与未来标签无关的来源形成80条未平衡候选 memory；
2. 独立冻结 eligible future-task/task-opportunity stream；
3. 在 witness 生成前冻结 task、Need label、gold state evaluator 和 severity rubric；
4. 独立标注 `Need(m,t)`，不允许 retention scorer 参与定义；
5. 从同一环境 snapshot 执行 Full/Evicted/Restore；
6. 用 Full−Evicted 测主要 deletion effect；
7. 用 Restore 检查干预可逆性和泄漏；
8. 先获得真实四象限标签，再形成平衡40条分析集；
9. 平衡40条只用于方法和机制比较，不能估计 prevalence。

第二步曾给出 Pilot gate，例如：

- 至少8条 restore-confirmed rare-critical records；
- 至少覆盖3个 failure-mode families；
- 至少一个常见 baseline 在固定预算下漏掉非平凡比例的 RBC；
- rare-critical eviction loss 明显高于 rare/non-critical；
- Full↔Restore 高一致率且泄漏为0。

这些阈值仍需在 Pilot protocol 中正式冻结，不能在看到结果后调整。

### 3.3 当前尚未完成的关键事实

项目目前没有运行任何 3A 或 40-memory Pilot，因此尚未证明：

- rare-but-critical records 是否不止几个手工案例；
- 它们在预注册 sampling frame 中占多少；
- LRU/LFU/relevance/importance 等 baseline 是否真的更容易删除它们；
- 删除是否真的产生等级3/4后果；
- Restore 是否能够恢复；
- witness 风险是否能够迁移到独立 held-out future trigger。

### 3.4 3A 能回答什么，不能回答什么

3-case Smoke 只能回答：

> 是否能够无泄漏地实施 Full/Evicted/Restore，并观察可恢复、方向正确的 deletion effect。

它不能回答：

- rare-critical memory 的比例；
- 自然发生率；
- baseline 系统性偏差；
- PREEMPT 的总体收益；
- FMEA 是否有效。

### 3.5 判决

**状态：`CONCEPTUALLY_ANSWERED_EMPIRICALLY_OPEN`**

这是目前最关键的未闭环问题。它不阻塞 3A，因为 3A 正是前置机制检查；但它阻塞论文的 problem contribution、主图和完整 Pilot 结论。

---

## 4. 问题三：研究内部记忆还是外部记忆

### 4.1 当前给出的明确回答

研究对象已经冻结为：

> **显式、非参数化、可寻址、可持久化、可单条删除与恢复的 external episodic/semantic memory。**

### 4.2 纳入与排除边界

| 对象 | 项目定位 | 原因 |
|---|---|---|
| External episodic memory | 主对象 | 有 source episode、稳定 ID 和清晰 provenance |
| External semantic memory | 主对象 | 可寻址和干预，但需追踪合并来源与同义副本 |
| Active context | 暴露/读取层和扩展对照 | 必须随 eviction 清除，但不是第二个主研究对象 |
| Procedural skill/code | 首轮暂缓 | 行为影响可能分布在代码、policy、配置和工具中 |
| 参数权重中的知识 | 排除 | 无稳定 item ID，无法做同类 remove/restore |
| KV cache/普通 prompt token | 排除 | 属于不同的 memory 和压缩问题 |
| 物理或合规永久删除 | 不声称 | 实验仍保留隔离 audit copy 以便 Restore |

### 4.3 Effective eviction 的语义

本项目研究的不是法律或物理意义上的永久删除，而是：

> memory 在正常 Agent 数据面、检索索引、缓存、summary、active context 和派生记录中全部不可达；仅隔离控制面保留 Agent 不可见的审计副本。

Restore 只从隔离控制面恢复同一 item、ID、metadata 和 index membership。

### 4.4 尚未完成的部分

范围已经回答，但实现尚未验证：

- 是否能够清除 alias、near-duplicate、graph edge 和 derived summary；
- 是否能够失效 retrieval/tool/summary cache；
- active prompt、scratchpad、session context 是否泄漏；
- Restore 是否只恢复目标 item 而没有顺带增强 prompt。

这些是 3A 的工程完整性问题，不再是研究对象选择问题。

### 4.5 判决

**状态：`ANSWERED_AND_FROZEN`**

第3项已经完整回答，不应重新开放。只有当外部 memory adapter 无法实现稳定干预时，才需要重新评估实验载体，而不是重新扩大到内部 memory。

---

## 5. 问题四：无公司日志时从哪里获得 memory 和数据

### 5.1 当前给出的明确回答

公司第一手日志不是启动受控学术研究的必要条件，但公开数据也不能自动提供完整闭环。

更准确的结论是：

> 公开资源足以提供 memory source、可执行环境、future-task 候选和 evaluator 组件，支持受控 feasibility study；但不能直接证明生产环境中的自然 prevalence 和外部有效性。

### 5.2 当前确定的资源分工

| 资源 | 在项目中的角色 | 能支撑什么 | 不能支撑什么 |
|---|---|---|---|
| AppWorld | 因果执行主轨 | API 执行、task-specific DB、checkpoint/reset、state tests、collateral damage | 原生自然跨任务 memory lifecycle、自然 prevalence |
| LongMemEval-V2 | 自然化 memory/外部有效性辅轨 | workflow、gotcha、premise、dynamic state、长 trajectory 和独立 QA | 原环境 replay、严重工具后果 |
| ConstraintRot/Governance Decay | failure taxonomy/evaluator 设计来源 | constraint loss、prohibited effect、确定性参数检查 | 外部 memory retention 主实验 |
| Learning What to Remember | learned retention baseline | blind future evidence retention baseline | 工具后果和 conditional severity |
| ALFWorld | AppWorld 失败时的执行备选 | reset/step、可重复任务失败 | 隐私、权限、财务等强 severe outcome |
| LongMemEval/LoCoMo | 对话/事实辅助对照 | 事实、时间、偏好和 QA forgetting | 可执行环境和 severe state change |

### 5.3 AppWorld 的关键修正

交叉复核指出：AppWorld 每个 task 使用 task-specific DB 和独立起始状态；官方 benchmark 不自动提供同一用户跨独立 task 的长期连续生命周期。

因此：

- 不能把两个官方 task ID 顺序执行就称为 natural lifecycle；
- source episode→target task 的 dependency 必须由项目明确建立；
- 每个案例必须标记为 `adapted` 或 `constructed/semi-synthetic`；
- 3A 不得标为 natural cross-task evidence；
- LongMemEval-V2 承担自然性/外部有效性辅助，而不是 severe-outcome 主证据。

### 5.4 当前未完成的部分

1. 尚未实际安装、下载或运行 AppWorld 小切片；
2. 尚未从真实 AppWorld trajectory/baseline output 抽取任何候选 memory；
3. 尚未实现 stable memory ID、provenance、delete、restore 和 index rebuild；
4. 尚未验证 protected bundle、许可、task variation 和 state evaluator 的实际可用性；
5. 尚未判断公开历史是否足以形成80条候选；
6. LongMemEval-V2 辅轨尚未实际抽取样本。

### 5.5 判决

**状态：`RESOURCE_PATH_ANSWERED_INTEGRATION_OPEN`**

项目已经回答“从哪里获得 memory”，但还没有回答“这些资源拼起来能否稳定形成论文级数据”。没有公司日志不是启动障碍，但仍是自然性和部署外推的限制。

---

## 6. 问题五：寻找细微视角差异，而非追求绝对完美

### 6.1 当前工作如何回应这一要求

当前工作没有因为每个子模块都有近邻就放弃 Idea，而是逐项承认已有覆盖，再寻找尚未被统一解决的组合。

已确认不是 novelty 的单点包括：

- rare-but-important memory；
- future-aware/budgeted retention；
- item-level causal intervention；
- pre-task synthetic practice；
- proactive memory intervention；
- AppWorld skill/memory curation；
- retention-before-retrieval failure；
- FMEA 或一般 prospective risk prediction。

在这些限制下，当前唯一安全的组合是：

> 在真实 trigger 尚未出现时，针对每个待删除 external memory item 生成 candidate-specific executable Future Decision Witness；在相同 checkpoint 上执行可审计的 effective eviction，用 Full−Evicted 测主要 deletion effect，以 Restore 做 recovery control；条件于 future task 对该 memory 的需要测量 severe loss，并在 memory budget 与 testing budget 双重约束下决定 retention。

### 6.2 八个必须保留的限定词

1. unseen trigger；
2. candidate-specific；
3. executable Future Decision Witness；
4. item-level effective eviction；
5. Full–Evicted paired primary effect；
6. Restore recovery control；
7. conditional severe loss；
8. memory/testing dual budgets。

删除其中关键限定后，claim 很容易落入 OSL-MR、CMI、MEMAUDIT、PREPING、ASSAY、Proactive Memory Agent 或 DSGC 已覆盖的范围。

### 6.3 “利用 AI 的防御性”已经转化为什么

前期所谓利用 AI 的防御性，不应成为论文表述，而应体现为研究流程：

- 主动寻找最强反例和最近邻；
- 将宽泛 claim 压缩到可核验证据支持的范围；
- 区分核心碰撞与可修复问题；
- 不因普通措辞和协议问题无限阻断最小实验；
- 对 witness 自证循环、数据泄漏和 constructed-case 外推提前设置防线。

交叉复核最终给出 `GO_3A_WITH_REQUIRED_REVISIONS`，说明这种策略实现了正确平衡：没有追求“100%无人碰过任何组件”，也没有忽略实质碰撞风险。

### 6.4 尚未完成的部分

- 完整组合目前只具有 prospective novelty，尚未有技术结果支撑；
- 如果最终只是“LLM 生成任务，再运行三次 Agent”，仍可能被视为工程拼装；
- 必须用 held-out trigger、双预算 Pareto 和真实 state consequence 证明组合产生了新的能力；
- 2026 Agent memory 文献增长很快，投稿前必须持续查新；
- `What Eviction Destroys` 在取得一手材料前不得参与 novelty 证明。

### 6.5 判决

**状态：`ANSWERED_AS_NOVELTY_STRATEGY`**

问题五已经在研究策略层面得到良好回答。它不再要求重新寻找 Idea，而要求用实验把组合差异变成不可由现有单点方法解释的结果。

---

## 7. 问题六：FMEA 是否可以引入 Agent memory

### 7.1 当前给出的明确回答

答案是：

> **可以借鉴，但只能作为可选 Prospective Risk Triage 的结构化设计来源，不能作为核心方法、论文标题或 novelty。**

### 7.2 可以保留的部分

FMEA 可提供以下结构化字段：

- possible failure mode；
- trigger precondition；
- effect/severity；
- evidence gap；
- detectability/uncertainty；
- witness feasibility；
- validation result。

这些字段可以迫使模型回答“删除后可能发生什么”，而不是只给一个笼统 importance score。

### 7.3 必须删除或降级的部分

1. 不使用传统：

\[
RPN=Occurrence\times Severity\times Detection.
\]

低 occurrence 正是本项目要保护的对象，乘积会系统性压低 rare/high-severity memory。

2. 不声称首次把 FMEA 用于 LLM/Agent；LLM-assisted FMEA 和 proactive Agent risk prediction 都已有相关研究。
3. 不把 ordinal S/O/D 乘积当成严格测量尺度。
4. FMEA 不决定 rare/critical 真值，最终证据来自可执行三分支。

### 7.4 必须进行的比较

Pilot 中至少比较：

- random triage；
- severity-only；
- generic LLM risk triage；
- FMEA-inspired triage；
- Full Counterfactual Oracle。

若 FMEA-inspired 不能提高 executable witness rate、same-budget RBC hit rate 或 severe-failure reduction，则应继续降级为实现细节，甚至从主方法中删除。

### 7.5 当前尚未回答的问题

- FMEA-inspired schema 是否真的比 severity-only 更好；
- 是否产生更多可执行而非虚构的 witness；
- 是否在相同 testing budget 下提高 RBC recall；
- detectability 在 Agent memory 中应该如何稳定解释。

### 7.6 判决

**状态：`POSITION_ANSWERED_EMPIRICAL_VALUE_OPEN`**

FMEA 是否“可以用”已经回答；FMEA 是否“值得用”仍未回答。但这不阻塞 PREEMPT-Mem，因为 FMEA 不是核心 novelty，负结果也可以安全删除该组件。

---

## 8. 问题七：是否需要构造或筛选特定数据暴露严重删除损失

### 8.1 当前给出的明确回答

答案是：

> **需要。现有通用 benchmark 通常测 QA、evidence retention 或平均 task success，未必自然产生低频、高严重度的 memory deletion effect；必须建立受控的筛选与适配协议。**

### 8.2 当前已经设计的数据形成流程

#### 阶段 A：3-case mechanism Smoke

只构造：

1. workflow；
2. gotcha；
3. constraint/permission。

每个案例必须：

- 标为 adapted 或 constructed/semi-synthetic；
- 写清 source episode、candidate memory 和 target task；
- 预先冻结 Need、severity 和 deterministic state evaluator；
- 从同一 checkpoint 运行 Full/Evicted/Restore；
- 通过 effective-eviction leakage manifest；
- 不估计 rarity 或 prevalence。

#### 阶段 B：未平衡候选池

- 从预注册的 AppWorld train/dev 来源形成80条候选；
- 记录完整 inclusion flow、类型和 provenance；
- 候选不是由 PREEMPT/FMEA 根据结果反向生成；
- 只有预先定义 sampling frame 和纳入概率后，才能报告该框架内 prevalence。

#### 阶段 C：冻结 future-task stream

- 明确 eligible task/scenario/user/variation；
- 冻结 task family、时间窗和 hash；
- witness generator 不可访问 hidden target、gold label 或 evaluator 私有信息；
- 独立定义 source→target dependency。

#### 阶段 D：平衡40条分析集

- 在测得 Need 和 criticality 后，再按四象限抽取；
- 四象限平衡集只用于机制、方法和异质性比较；
- 不得用 `10/40` 推断自然 rare-critical prevalence。

### 8.3 为什么不能只使用现成通用 benchmark

| Benchmark 类型 | 能提供什么 | 对本论文的主要不足 |
|---|---|---|
| Long-memory QA | 长历史、事实、偏好、workflow、question | 没有可重置工具环境和严重 state effect |
| 普通 Agent task benchmark | task success 和工具轨迹 | 未必有跨任务 persistent memory dependency |
| Safety/constraint benchmark | 明确严重违规和 deterministic grader | trigger 通常已给定，memory 常在 active context |
| Learned retention benchmark | gold evidence retention | evidence miss 不等于 executable severe loss |

因此，需要把自然性、执行性和严重度分轨处理，而不是假定一个数据集同时提供全部证据。

### 8.4 当前尚未完成的部分

- 3个 Smoke cases 尚未构造和运行；
- 80条候选池尚未形成；
- future-task stream 尚未最终冻结；
- 40条平衡分析集尚不存在；
- natural/adapted/constructed 比例尚无数据；
- 数据标注一致性、invalid witness rate 和 state evaluator 稳定性尚无结果；
- AppWorld 是否能提供足够同环境 memory 来源尚待源码和运行审计。

### 8.5 判决

**状态：`PROTOCOL_ANSWERED_DATA_PENDING`**

“是否需要构造或筛选”已经得到明确肯定回答；“能否构造出足以支撑论文的数据”尚未回答。第三步 A 就是这个问题的第一个执行门禁。

---

## 9. 问题四与问题七的关系

这两项看似重复，实际回答不同层次：

- **问题四回答数据从哪里来**：AppWorld、LongMemEval-V2、ConstraintRot、ALFWorld 等公开资源如何分工；
- **问题七回答如何把资源转化成研究证据**：adapted/constructed lifecycle、80条未平衡候选池、冻结 future stream、40条平衡分析集和三分支执行协议。

因此两项都必须保留。只有数据来源而没有构造协议，会得到普通 QA/Agent benchmark；只有构造协议而没有可信来源，会得到纯手工故事。

---

## 10. 当前工作真正已经回答了什么

当前可以作为可靠项目基础的结论是：

1. 研究对象是 external addressable episodic/semantic memory；
2. rarity 必须基于冻结 future-task distribution 中的 `Need`，不能由 retrieval frequency 定义；
3. criticality 必须基于 `Need=1` 条件下的 eviction loss，与 occurrence 解耦；
4. importance 是 heuristic 上位概念，不能代替 causal forgetting loss；
5. rare-but-critical 必须先在可信研究分布中被实证证明，但不必先证明生产世界普遍性；
6. 公开数据足以启动受控研究，但没有单一现成 benchmark 提供完整闭环；
7. AppWorld 主轨必须定位为 adapted/constructed/semi-synthetic executable causal benchmark；
8. LongMemEval-V2 只承担自然性与外部有效性辅轨；
9. Full−Evicted 是主要效应，Restore 是 recovery/symmetry control；
10. effective eviction 必须清除索引、缓存、summary、active context 和派生泄漏；
11. FMEA 只能作为 optional triage schema，不使用传统 RPN；
12. novelty 只存在于八个限定组成的完整闭环，而不是任一单组件。

---

## 11. 当前仍没有回答的科学问题

以下问题仍然没有实验答案，不能写成论文结论：

1. rare-but-critical memory 是否在预注册 AppWorld sampling frame 中真实存在且不是孤例；
2. 其比例、置信区间和 failure-mode 分布是什么；
3. 现有 retention baseline 是否系统性漏掉它们；
4. Full/Evicted/Restore 是否可以无泄漏、稳定运行；
5. candidate-specific witness 是否可执行；
6. witness 风险能否预测独立 held-out trigger；
7. PREEMPT 是否在相同 memory/testing budget 下减少 severe failure；
8. PREEMPT 是否保持平均 task success；
9. FMEA-inspired triage 是否优于 severity-only 和 generic risk triage；
10. controlled/semi-synthetic 结果能否迁移到更自然的 memory 轨迹。

---

## 12. 后续阶段如何闭合七个问题

### 12.1 启动 3A 前

完成：

- 七项强近邻与完整 novelty 修订附录；
- `What Eviction Destroys = U`；
- AppWorld adapted/constructed 定位；
- 三案例 source→target dependency；
- generator/evaluator firewall；
- effective-eviction manifest。

这主要闭合问题1、3、5、6的协议冻结。

### 12.2 第三步 A

真实运行 workflow、gotcha、constraint/permission 三个案例。

它主要回答：

- AppWorld 是否可接入；
- external memory 能否有效删除和恢复；
- evaluator 是否稳定；
- 是否能观察可恢复的方向性 deletion effect。

这主要推进问题4和7，但尚不能证明问题2。

### 12.3 40-memory Pilot

在独立复核允许后：

- 形成80条未平衡候选池；
- 冻结 future-task sampling frame；
- 测 Need 和 conditional criticality；
- 形成平衡40条分析集；
- 比较 baseline、random/severity/generic/FMEA triage 和 PREEMPT；
- 报告 witness transfer、成本和置信区间。

这才真正回答问题2、6和7，并进一步验证问题1、4、5。

### 12.4 正式实验

只有 Pilot 通过后，才扩展：

- 样本和 failure family；
- 模型和 seed；
- memory/testing budget sweep；
- LongMemEval-V2 自然性辅轨；
- group intervention 与 memory 交互；
- 统计显著性和复现包。

---

## 13. 最终判决

### 13.1 对七项问题的总体回答

当前工作已经成功完成三件重要事情：

1. 把模糊的“rare but critical memory”直觉转化成可测的 rarity 与 conditional criticality；
2. 把宽泛的“未来重要性预测”收窄成可 defend 的 pre-trigger executable deletion-risk 闭环；
3. 找到公开资源和受控数据构造路径，使没有公司日志的项目仍然能够启动。

但当前还没有完成最重要的一件事：

> **用真实、可重复、无泄漏的执行证据证明 rare-but-critical memory 确实存在，并证明 PREEMPT 能在相同预算下更好地保护它。**

### 13.2 项目级结论

`RESEARCH_QUESTIONS_SUBSTANTIALLY_ADDRESSED__EMPIRICAL_CLAIMS_OPEN`

对应中文结论：

> **前期问题在研究设计层面已基本回答，可以继续第三步 A；但论文的核心科学贡献仍处于待验证状态，不能把计划中的现象和性能优势写成已经获得的结果。**

### 13.3 是否需要重新选题

不需要。当前没有发现完整核心碰撞，也没有发现无法修复的因果错误。正确行动不是重新寻找 Idea，而是按门禁完成：

\[
\text{Required Revisions}
\rightarrow
\text{3-case Smoke}
\rightarrow
\text{Independent Audit}
\rightarrow
\text{80→40 Pilot}.
\]

只有在以下情况才需要重构主轨：

- AppWorld 无法实现稳定三分支；
- effective eviction 无法排除泄漏；
- credible sampling frame 中不存在非单例 rare-critical memory；
- witness 无法迁移到 held-out trigger；
- PREEMPT 在同预算下不优于 random/severity-only/generic triage。

---

## 14. 主要一手来源

- AppWorld: <https://aclanthology.org/2024.acl-long.850/>
- LongMemEval-V2: <https://arxiv.org/abs/2605.12493>
- OSL-MR: <https://arxiv.org/abs/2606.10616>
- Causal Memory Intervention: <https://arxiv.org/abs/2605.17641>
- MEMAUDIT package-oracle: <https://arxiv.org/abs/2605.02199>
- PREPING: <https://arxiv.org/abs/2605.13880>
- ASSAY: <https://arxiv.org/abs/2606.15390>
- Proactive Memory Agent: <https://arxiv.org/abs/2607.08716>
- When Retrieval Fails Before It Begins: <https://arxiv.org/abs/2608.20400>
- DeMem: <https://arxiv.org/abs/2605.10870>
- TraceRetain: <https://arxiv.org/abs/2606.29178>
- Governance Decay/ConstraintRot: <https://arxiv.org/abs/2606.22528>
