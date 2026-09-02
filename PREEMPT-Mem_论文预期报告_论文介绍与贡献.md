# PREEMPT-Mem 论文预期报告：论文介绍、核心方法与预期贡献

> 项目：ICLR 2027 — PREEMPT-Mem  
> 报告性质：论文完成形态预期稿  
> 日期：2026-08-27  
> 当前阶段：第三步 A（AppWorld 三分支 Smoke）启动前  
> 当前准入判决：`GO_3A_WITH_REQUIRED_REVISIONS`

## 0. 报告说明

本报告描述 PREEMPT-Mem 在实验顺利完成后，预期形成的论文问题、方法、贡献和证据结构。报告中的方法设计与 novelty 边界来自已经完成的文献、数据和因果协议审查；所有实验效果、数值提升和统计显著性目前仍是**待验证目标**，不是已经取得的研究结果。

本报告主要用于：

1. 向合作者解释论文究竟研究什么；
2. 统一论文核心 Story、方法边界和贡献表述；
3. 约束后续代码、数据构造和实验不偏离核心问题；
4. 明确什么样的实验证据才足以支撑 ICLR 投稿。

---

## 1. 预期论文标题

主标题建议：

> **PREEMPT-Mem: Stress-Testing Agent Memories Before They Are Forgotten**

备选标题：

> **Remember Before It Matters: Pre-Trigger Counterfactual Risk Testing for Agent Memory Retention**

标题不包含 FMEA，因为 FMEA 只是一种可选的风险筛选 schema，不是论文的核心 novelty。

---

## 2. 一句话介绍

> PREEMPT-Mem 在一条 Agent memory 被删除之前，主动生成与该候选 memory 对应的可执行未来风险情境，并通过 Full/Evicted 配对干预测试遗忘后果，从而在有限 memory budget 和 testing budget 下保护低频但高严重度的关键记忆。

更直观地说：

> Agent 不必等到罕见失败真实发生以后，才知道某条 memory 不应该被遗忘；它可以在删除前主动对这条 memory 进行压力测试。

---

## 3. 研究背景与核心问题

长期运行的 Agent 会持续积累外部记忆，例如：

- 用户偏好；
- workflow 和操作顺序；
- environment gotcha；
- 权限与约束；
- 动态环境状态；
- 失败经验和修复方法；
- 与特定用户、账户或工具有关的规则。

由于存储容量、检索开销和 active-context 长度都受到限制，Agent 不可能永久保留所有内容，必须决定哪些 memory 被保留、压缩或删除。

现有 retention 策略通常使用：

- recency；
- access/retrieval frequency；
- semantic relevance；
- historical utility；
- LLM importance score；
- learned retention score。

这些信号通常能够识别经常使用或与当前 query 高度相关的 memory，但不能直接回答：

> **如果现在删除这条 memory，在某个尚未出现的未来情境中，会不会造成严重后果？**

这形成一个 retention-stage blind spot：某条 memory 在大多数历史和未来任务中都不被需要，却可能在极少数情境中成为避免严重失败的必要前提。一旦该 memory 在 trigger 出现前已经被淘汰，之后再强的 retriever 也无法从 memory store 中取回它。

---

## 4. Rare-but-Critical Memory

### 4.1 Rarity 与 Criticality 必须分开

对于候选 memory \(m_i\) 和冻结的未来任务分布 \(\mathcal D_{future}\)，定义：

\[
\rho_i=
\Pr_{z\sim\mathcal D_{future}}
[N_i(z)=1],
\]

其中 \(N_i(z)\) 表示未来任务 \(z\) 是否需要 \(m_i\)。\(\rho_i\) 衡量该 memory 被需要的频率。

再定义删除效应：

\[
\Delta_i(z)=
L(A(M\setminus\{m_i\},z))-
L(A(M,z)).
\]

条件性 criticality 为：

\[
c_i=
\mathbb E[\Delta_i(z)\mid N_i(z)=1].
\]

因此：

\[
m_i\text{ is rare-but-critical}
\iff
\rho_i\le \tau_r
\land
c_i\ge \tau_c.
\]

### 4.2 为什么不能使用平均风险

若把发生概率与严重度直接相乘，罕见事件会因为低概率而获得较低总体分数。这样虽然可能优化平均任务准确率，却会继续删除极少发生、但一旦发生便造成高损失的 memory。

PREEMPT-Mem 因此不把 criticality 定义为 occurrence 与 severity 的乘积，而是重点测量：

> 在 memory 确实被需要的条件下，删除它会造成多严重的后果。

---

## 5. 核心方法：PREEMPT-Mem

整体流程为：

\[
\text{Eviction Candidate}
\rightarrow
\text{Prospective Risk Triage}
\rightarrow
\text{Future Decision Witness}
\rightarrow
\text{Executable Counterfactual Validation}
\rightarrow
\text{Risk-Aware Retention}.
\]

### 5.1 Eviction Candidate

PREEMPT-Mem 不持续重新评估整个 memory store，而是作为可插拔 retention layer，接收现有 memory policy 准备删除的候选项。

这使其可以与 LRU、LFU、relevance scorer、learned retention policy 或其他 memory system 组合使用。

### 5.2 Prospective Risk Triage

由于对每条 memory 运行多个真实 Agent rollout 成本过高，系统首先进行低成本风险筛选，估计：

- 可能的 future failure mode；
- 后果严重度；
- 当前 evidence gap；
- witness 是否可构造和执行；
- 风险判断的不确定性；
- 是否值得分配反事实测试预算。

FMEA-inspired schema 可以作为其中一种结构化实现，但不使用传统 \(RPN=S\times O\times D\)，也不把 FMEA 当成核心贡献。

### 5.3 Candidate-Specific Future Decision Witness

对于候选 memory \(m_i\)，系统生成一个或多个 Future Decision Witness：

\[
W_i=\{w_{i1},\ldots,w_{iK}\}.
\]

每个 witness 是一个在真实 trigger 到来前生成的、候选特异、可执行、可被环境 evaluator 证伪的未来情境。

Witness 必须满足：

1. 与候选 memory 的决策作用有关，而不是机械改写 memory 文本；
2. 符合环境 API、用户、权限和数据库状态约束；
3. 不读取 held-out future task、gold state 或最终标签；
4. 能由真实 Agent 在工具环境中执行；
5. 最终结果由独立、确定性的 state evaluator 判断；
6. 生成失败、不可执行和重复 witness 必须被记录，而不能静默丢弃。

### 5.4 Full/Evicted/Restore 三分支验证

对同一个 future-task checkpoint，运行：

- **Full**：候选 memory 正常存在并可以被检索；
- **Evicted**：候选 memory 及其索引、缓存、summary 和派生信息全部不可达；
- **Restore**：恢复被删除的同一个 item、ID、metadata 和索引。

主要 deletion effect 是：

\[
\widehat{\Delta}_i=
L_{Evicted}-L_{Full}.
\]

Restore 不是第三个主要因果效应，而是 recovery/symmetry control，用于检查：

- 删除操作是否真的只改变了候选 memory；
- 缓存、summary 或 active context 是否泄漏；
- 环境是否发生漂移；
- 恢复同一 memory 后能否重新获得 Full 的行为和状态结果。

### 5.5 Effective Eviction

删除不能只删除 memory store 中的一行记录。PREEMPT-Mem 需要对以下位置执行可审计的不可达性检查：

- canonical memory record；
- alias 和近重复副本；
- embedding/ANN/keyword/graph index；
- reranker 派生特征；
- retrieval、tool 和 summary cache；
- active prompt、scratchpad 和 session context；
- 派生的 summary、rule、skill、plan、edge、tag 和 cached answer；
- Agent 可以访问的 archive、日志和 debug endpoint。

任何存在信息泄漏的 triplet 均不能计入 deletion effect。

### 5.6 Risk-Aware Retention Under Dual Budgets

系统同时受到两类约束：

\[
|M|\le B_m,
\qquad
\operatorname{Cost}_{test}\le B_t,
\]

其中：

- \(B_m\) 是 memory capacity/storage budget；
- \(B_t\) 是 witness generation 和 counterfactual rollout budget。

最终 retention policy 综合考虑：

- 已验证的 conditional severe loss；
- 正常任务 utility；
- memory size；
- witness validity 与置信度；
- 剩余测试成本；
- memory 间的冗余与互补关系。

论文的目标不是无成本地发现全部风险，而是在相同双预算下，比现有 retention 方法保护更多 rare-but-critical memory，并降低严重失败率。

---

## 6. 预期论文贡献

### 贡献一：问题与现象贡献

> 将 Agent memory retention 中的低频需求与条件严重度明确分离，操作化定义 rare-but-critical memory，并系统研究 retention policy 是否会在 retrieval 发生前删除这类必要信息。

预期证据包括：

- future need frequency 与 conditional eviction loss 的四象限分布；
- rare-critical memory 的类型、来源和失败后果；
- LRU、LFU、relevance 和 importance scorer 对该区域的淘汰偏差；
- retrieval frequency 作为 rarity proxy 的 false-negative 情况。

这一贡献的重点不是宣称“首次发现重要 memory”，而是把问题转化成具有明确分母、条件损失和可执行后果的研究对象。

### 贡献二：方法贡献

> 提出 PREEMPT-Mem，在真实 trigger 尚未出现时，为每个待删除候选 memory 生成 candidate-specific executable Future Decision Witness，并使用真实工具环境验证其遗忘风险。

安全 novelty 必须始终以以下完整组合表述：

1. unseen trigger；
2. candidate-specific；
3. executable Future Decision Witness；
4. item-level effective eviction；
5. Full–Evicted paired primary effect；
6. Restore recovery control；
7. conditional severe loss；
8. memory/testing dual budgets。

任一单独组件均不作为首创主张。

### 贡献三：因果实验与可审计 benchmark 贡献

> 建立可审计的 Full/Evicted/Restore 三分支协议，通过同一环境 snapshot、确定性 state evaluator、effective-eviction manifest 和数据库 state diff，将 memory deletion 与工具行为后果建立直接因果联系。

AppWorld 主轨预期定位为：

> **controlled/semi-synthetic executable causal benchmark**

它用于验证机制、工具行为和严重后果，而不用于直接声称自然的跨任务生命周期或生产 prevalence。

LongMemEval-V2 或其他自然化长历史数据可作为辅助轨，用于支持 workflow、gotcha、dynamic state 和 premise awareness 的外部有效性，但不能替代 AppWorld 的可执行工具后果证据。

### 贡献四：预算化风险发现贡献

> 将 memory retention 扩展为同时受 memory capacity 和 counterfactual-testing cost 约束的主动风险发现问题，在相同预算下优化 severe failure/tail risk，而不仅是平均任务成功率。

预期需要证明：

- selective PREEMPT testing 优于 random testing；
- PREEMPT 优于 severity-only 和 generic risk scoring；
- 在显著少于 Full Counterfactual Oracle 的 rollout 成本下，达到接近其 rare-critical recall；
- severe failure 明显下降，而平均任务成功率和普通 utility 基本保持。

---

## 7. 与现有工作的边界

PREEMPT-Mem 不主张以下单项贡献：

- 未知未来需求下的预算化 retention；
- 对单个 memory 做 causal masking；
- 在目标任务前生成 synthetic practice；
- 主动把 memory 注入 Agent 决策；
- 首次发现 retention-before-retrieval failure；
- 首次在 AppWorld 上筛选 memory/skill。

主要近邻包括：

- OSL-MR：未知未来需求下的顺序 retention 与预算优化；
- Causal Memory Intervention：当前请求下的 memory 因果选择；
- MEMAUDIT：未知未来 query 前的预算化 memory writing 和 exact package oracle；
- PREPING：目标任务前的 synthetic practice 和 memory construction；
- ASSAY：AppWorld/tau-bench 上的 per-skill causal masking 与 curation；
- Proactive Memory Agent：主动 memory-grounded intervention；
- When Retrieval Fails Before It Begins：retrieval 前 prerequisite eviction failure；
- DeMem：decision-centric forgetting boundary 和 memory–distortion frontier。

PREEMPT-Mem 的差异不来自某一个新组件，而来自完整闭环：

> 对尚未出现的 trigger，为待删除的具体 memory 主动生成可执行风险 witness，通过无泄漏 item-level 删除干预测量条件严重后果，并在双预算下将结果用于真实 retention 决策。

---

## 8. 预期实验设计

### 8.1 AppWorld 主轨

AppWorld 提供真实 API 调用、数据库状态变化、程序化 state tests 和 collateral-damage 检查，适合执行 Full/Evicted/Restore。

第三步 A 首先验证三个最小案例：

1. workflow；
2. gotcha；
3. constraint/permission。

三者只能标记为 adapted 或 constructed/semi-synthetic，不能标记为 natural cross-task lifecycle。

### 8.2 Pilot 数据结构

预期数据结构为：

- 一个预注册、未平衡的候选池，用于报告抽样框内的四象限计数；
- 一个平衡分析集，用于比较机制、方法和效应异质性；
- 独立的 witness-generation、development 和 held-out future-trigger split。

平衡分析集不得用于估计自然 prevalence；任何 prevalence 结论都必须明确分母、采样框和纳入概率。

### 8.3 Baselines

预期至少包括：

- Random；
- LRU/FIFO；
- LFU；
- semantic relevance；
- LLM importance；
- severity-only；
- generic risk triage；
- FMEA-inspired triage；
- random counterfactual testing；
- strong learned/budgeted retention baseline；
- Full Counterfactual Oracle；
- Keep All、No Memory、Gold Pinning。

### 8.4 核心指标

- Task Success；
- Severe Failure Rate；
- Rare-Critical Recall；
- Conditional Eviction Loss；
- Average Utility；
- Memory Cost；
- Counterfactual Rollout Cost；
- Witness Validity/Invalid Rate；
- Witness Precision、Recall 与 calibration；
- Effective-Eviction Leakage Rate；
- Full–Restore Consistency；
- collateral database changes。

---

## 9. 预期核心结果

本节描述论文需要争取验证的结果形态，不代表当前已经获得这些结果。

### 9.1 预期发现一：Rare-but-Critical 区域真实存在

预期观察到：

- future need frequency 与 conditional severity 并不等价；
- 一部分低频 memory 在被需要时具有明显更高的删除损失；
- retrieval frequency、recency 或 semantic relevance 会漏掉其中一部分 memory；
- 平均任务成功率无法完整反映这些尾部失败。

理想主图：横轴为 future need frequency，纵轴为 conditional eviction loss，左上角形成 rare-but-critical 区域，并标注不同 retention policy 删除的 memory。

### 9.2 预期发现二：可执行 witness 能提前暴露真实风险

预期 witness 不仅能在自己构造的情境中产生 Full/Evicted 差异，还能预测独立 held-out future trigger 上的 deletion loss。

需要报告：

- witness validity；
- invalid/contrived witness rate；
- witness score 与 held-out deletion loss 的相关性；
- precision、recall、calibration；
- false-positive 和 false-negative 类型。

### 9.3 预期发现三：PREEMPT 降低严重失败

理想结果是：

> 在相同 memory budget 下，PREEMPT-Mem 显著降低 severe failure rate，同时平均 task success 与 Keep-All/强 retention baseline 基本持平。

这里不预设具体提升数字。最终摘要只能填写真实实验得到的效果量、置信区间和统计检验。

### 9.4 预期发现四：主动测试成本是值得的

预期形成 testing-cost Pareto 曲线：

- random testing 成本利用率低；
- severity-only 容易过度保护高严重度但不可触发的候选；
- Full Counterfactual 效果强但成本最高；
- PREEMPT 通过 candidate triage 和 witness validation，在更低 rollout 成本下接近 oracle 的风险保护能力。

---

## 10. 论文最重要的三张图

### Figure 1：PREEMPT-Mem 方法总图

展示：

\[
\text{Candidate}
\rightarrow
\text{Triage}
\rightarrow
\text{Witness}
\rightarrow
\text{Full/Evicted/Restore}
\rightarrow
\text{Retention}.
\]

### Figure 2：Rare–Critical 四象限图

- 横轴：future need frequency；
- 纵轴：conditional eviction loss；
- 左上角：rare-but-critical memory；
- 颜色或符号：不同 baseline 删除/保留的 memory。

这应当是整篇论文最具记忆点的现象图。

### Figure 3：双预算 Pareto 曲线

- 横轴：witness/counterfactual testing cost；
- 纵轴：severe failure rate 或 rare-critical recall；
- 比较 random、severity-only、generic triage、PREEMPT 和 Full Counterfactual。

该图决定额外风险测试是否具有实际价值。

---

## 11. 预期论文 Story

整篇论文应让审稿人依次接受：

1. 长期 Agent 必须在有限容量下淘汰 memory；
2. memory 被需要的频率不等于被需要时的严重度；
3. 现有 retention policy 确实会删除 rare-but-critical memory；
4. 删除这些 memory 会造成可执行、可恢复的严重因果后果；
5. PREEMPT 能在真实 trigger 到来前主动发现这种风险；
6. 在相同 memory/testing budget 下，这种发现能力能减少严重失败；
7. 额外测试成本与收益相比是合理的。

预期论文核心表述为：

> **PREEMPT-Mem turns memory retention from passive importance scoring into active, executable risk discovery before eviction.**

---

## 12. 局限性

即使实验成功，论文仍需主动承认：

- AppWorld 跨任务 lifecycle 主要是 controlled/adapted/semi-synthetic；
- 研究对象仅限 external addressable memory；
- item-level intervention 不能完整处理 memory 冗余和高阶交互；
- witness generator 可能产生 contrived、invalid 或偏置情境；
- effective eviction 是实验层面的不可达，不等于物理或合规删除；
- counterfactual execution 成本仍然较高；
- 小型平衡分析集不能估计生产环境 prevalence；
- AppWorld 上的工具风险不能自动外推到所有真实 Agent 系统。

---

## 13. 论文成功与止损标准

### 13.1 第三步 A 成功标准

- 至少 2/3 案例中 Full 与 Restore 一致或功能等价；
- Evicted 相对 Full 出现可解释的失败或严重状态差异；
- effective eviction 不存在泄漏；
- evaluator 能稳定复现结果。

### 13.2 Pilot 成功标准

- 未平衡候选池中存在非个例的 rare-critical memory；
- 简单和强 retention baseline 均存在可测量的 RBC miss；
- witness 对 held-out trigger 具有预测能力；
- PREEMPT 在匹配双预算下改善 severe failure/tail risk；
- 收益不依赖单一 constructed template、模型或 seed。

### 13.3 应当停止或重构的情况

- 无法构造无泄漏且可恢复的 Full/Evicted/Restore；
- Full 与 Evicted 长期没有可解释的行为或状态差异；
- rare-critical memory 只存在于人为设计的极端故事中；
- witness 只能预测自己构造的任务，不能迁移到 held-out trigger；
- 相同 testing budget 下，PREEMPT 不优于 severity-only 或 random testing；
- 额外 rollout 成本远大于其减少的严重失败价值。

---

## 14. 预期 ICLR 价值评估

若上述结果完整兑现，PREEMPT-Mem 的优势将不是某个单点技术首次出现，而是：

- 问题具有现实价值和清楚的安全/可靠性意义；
- Story 简洁、直观并具有记忆点；
- 将 retention-before-retrieval failure 推进到真实工具后果；
- 具有可执行因果协议，而不只依赖 LLM judge；
- 同时回答效果、风险和额外测试成本；
- 方法能够作为外部 layer 接入多种 memory system。

如果只有三个手工案例和一个 LLM risk scorer，论文会被视为合理但偏工程的 pipeline。如果能够提供非平凡的现象规模、held-out witness validity、同预算 Pareto 优势和跨模型/类型泛化，论文才有机会形成具有竞争力的 ICLR 主会投稿。

综合预期：

| 维度 | 当前状态 | 实验完整后的预期潜力 |
|---|---:|---:|
| 问题价值 | 8.5/10 | 9/10 |
| Story 记忆点 | 8.5/10 | 9/10 |
| 组合 novelty | 7/10 | 8/10 |
| 技术深度 | 4/10 | 7.5–8/10 |
| 实证说服力 | 尚无结果 | 取决于 Pilot 与正式实验 |
| ICLR 竞争力 | 当前不足投稿 | 结果完整时有竞争力，但不是稳收 |

---

## 15. 预期摘要骨架

> Long-horizon agents accumulate external memories that exceed finite storage and retrieval budgets, forcing them to decide what to forget. Existing retention policies often rely on recency, frequency, relevance, or observed utility, which may overlook memories that are rarely needed but critical when triggered. We introduce PREEMPT-Mem, a framework that stress-tests an eviction candidate before deletion. For each candidate memory, PREEMPT-Mem generates candidate-specific executable Future Decision Witnesses and estimates its deletion effect through paired Full and Evicted rollouts in a stateful tool environment, while using Restore as a recovery and intervention-integrity control. The resulting evidence supports risk-aware retention under joint memory and counterfactual-testing budgets. We evaluate whether rare-but-critical memories form a systematic blind spot for existing retention policies and whether PREEMPT-Mem reduces severe failures without sacrificing average task utility. [真实环境、数据规模、主要效果量和成本收益将在实验完成后填写。]

---

## 16. 核心参考近邻

1. AppWorld: <https://aclanthology.org/2024.acl-long.850/>
2. OSL-MR / Learning What to Remember: <https://arxiv.org/abs/2606.10616>
3. Causal Memory Intervention: <https://arxiv.org/abs/2605.17641>
4. MEMAUDIT: <https://arxiv.org/abs/2605.02199>
5. PREPING: <https://arxiv.org/abs/2605.13880>
6. ASSAY / Not All Skills Help: <https://arxiv.org/abs/2606.15390>
7. Proactive Memory Agent: <https://arxiv.org/abs/2607.08716>
8. When Retrieval Fails Before It Begins: <https://arxiv.org/abs/2608.20400>
9. DeMem / A Rate-Distortion Framework for Agent Memory: <https://arxiv.org/abs/2605.10870>

---

## 17. 最终定位

PREEMPT-Mem 最终不应被介绍为“把 FMEA 用到 Agent memory”，也不应被介绍为“一个新的 memory importance score”。

它的正确定位是：

> **一种面向长期 Agent memory retention 的预算化主动风险发现方法：在真实触发出现前，通过候选特异的可执行反事实压力测试，识别并保护低频但高严重度的外部记忆。**

论文最终希望传达的核心观点是：

> **An agent should not have to suffer a rare failure before learning what it must remember.**
