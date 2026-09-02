# PREEMPT-Mem：ICLR 论文结构与内容规划

## 总体结构

这篇论文最合理的递进逻辑不是：

> Agent Memory → FMEA → PREEMPT → 实验

而应该是：

> **有限记忆必须淘汰 → 现有策略存在盲区 → rare 与 critical 必须分开 → 因果实验证明该现象真实存在 → 提出删除前主动压力测试 → 在相同双预算下验证收益。**

ICLR 2027 投稿正文最多 9 页，参考文献不计页数，附录不限但审稿人没有义务阅读；采用双盲审稿，并要求 AI Use Statement，建议提供 Reproducibility Statement。[ICLR 2027 Author Guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines)

## 推荐目录与页数

| 内容 | 建议页数 |
|---|---:|
| Title + Abstract | 0.45 |
| 1. Introduction | 1.0 |
| 2. Related Work | 0.65 |
| 3. Problem Formulation | 0.7 |
| 4. Characterizing Rare-but-Critical Memory | 0.8 |
| 5. PREEMPT-Mem | 1.6 |
| 6. Experimental Setup | 1.1 |
| 7. Results and Analysis | 2.2 |
| 8. Limitations and Conclusion | 0.5 |
| 合计 | 9.0 |

---

# Title

建议使用一个直接表达核心动作的标题：

> **PREEMPT-Mem: Stress-Testing Agent Memories Before They Are Forgotten**

或者保留现在更具叙事性的版本：

> **Remember Before It Matters: Pre-Trigger Counterfactual Risk Testing for Agent Memory Retention**

第一个更清楚，第二个更有 Story。可以组合为：

> **PREEMPT-Mem: Remember Before It Matters by Stress-Testing Agent Memories Before Eviction**

标题中不建议出现 FMEA，因为 FMEA 不是核心 novelty。

---

# Abstract

摘要应在实验完成后最后写，但结构现在可以固定为五层。

## 第一句：背景和问题

Agent 在长期运行中不断积累外部记忆，但容量限制迫使系统淘汰部分 memory。

## 第二句：现有方法的盲区

现有 retention 方法通常依赖 recency、frequency、relevance、historical utility 或当前 query，可能删除过去很少使用、但未来触发时会造成严重后果的信息。

不能写成“所有现有方法只看历史”，因为 OSL-MR 已研究未知未来需求下的顺序 retention。[OSL-MR](https://arxiv.org/html/2606.10616)

## 第三句：方法

提出 PREEMPT-Mem：在真实 trigger 出现前，为待删除 memory 生成可执行 Future Decision Witness，通过 Full/Evicted 配对干预估计遗忘损失，并用 Restore 检查干预可逆性。

## 第四句：实验

说明在什么环境、多少 memory、多少模型和哪些预算下评估。

## 第五句：核心结果

最终填写三个最重要的数字：

- severe failure 降低多少；
- 平均任务成功率是否保持；
- 相比 Full Counterfactual 节省多少测试成本。

摘要不要列四五项贡献，也不要突出 FMEA。

---

# 1. Introduction

Introduction 最好写成五个自然段。

## 第一段：有限 memory 是不可避免的问题

说明长期 Agent 会积累：

- 用户偏好；
- 环境状态；
- workflow；
- 失败经验；
- permission 和 constraint；
- environment gotcha。

但 memory storage、retrieval 和 active context 都受预算限制，因此必须选择保留和删除。

## 第二段：现有 retention 的盲区

介绍现有系统主要依据：

- recency；
- access frequency；
- semantic relevance；
- LLM importance；
- observed downstream utility；
- manual pinning。

问题不在于这些信号完全无效，而在于：

> 它们通常不能直接回答“删除这条 memory 后，在某个尚未出现的未来情境中会造成多严重的后果”。

## 第三段：给出一个具体例子

例如：

- Agent 很早发现某 API 在特定账户上存在隐藏约束；
- 之后几十个任务都没有再次触发；
- frequency/LRU 认为它无用并删除；
- 某个罕见未来任务再次遇到该状态；
- Agent 执行不可逆操作或违反用户约束。

用一个简短案例让审稿人理解：

> low frequency ≠ low future necessity。

## 第四段：核心 insight

引出 PREEMPT-Mem：

> 在删除前，不直接相信一个预测分数，而是主动寻找能够暴露遗忘风险的未来情境，并让真实 Agent 在环境中执行。

这里放主方法图 Figure 1：

\[
\text{Eviction Candidate}
\rightarrow
\text{Risk Triage}
\rightarrow
\text{Future Witness}
\rightarrow
\text{Full/Evicted Validation}
\rightarrow
\text{Retention}
\]

## 第五段：三项贡献

最终贡献只建议保留三项：

1. **Problem and empirical contribution**  
   操作化定义 rare-but-critical external memory，并证明现有 retention policy 在该区域存在系统盲区。

2. **Method contribution**  
   提出 PREEMPT-Mem，在 trigger 到来前生成候选特异的可执行 witness，通过有效删除干预验证条件性严重后果。

3. **Efficiency contribution**  
   在 memory budget 和 counterfactual-testing budget 双重约束下选择性测试与保留，降低 severe failure，同时控制计算成本。

FMEA 不单独列为贡献。

---

# 2. Related Work

Related Work 不要写成文献罗列，应围绕“每类工作解决了什么、还缺什么”组织。

## 2.1 Agent Memory Retention and Forgetting

包括：

- Memory-R1、AgeMem；
- TraceRetain；
- CURATOR；
- Learning What to Remember；
- OSL-MR；
- When Retrieval Fails Before It Begins。

承认它们已经覆盖：

- memory lifecycle；
- budgeted retention；
- future demand；
- delayed eviction cost；
- retention-before-retrieval failure。

剩余差异是：

> 没有同时主动生成未知 trigger 的可执行 deletion-risk witness，并将验证结果用于 rare high-severity retention。

## 2.2 Causal Memory and Skill Attribution

包括：

- Causal Memory Intervention；
- ASSAY；
- MemAudit；
- DeMem；
- Governance Decay。

承认它们已经覆盖：

- per-item/per-skill causal masking；
- remove-one intervention；
- decision loss；
- 严重工具行为；
- 事后有害 memory 审计。

区别是当前 query、开发任务或有害事件通常已经出现；PREEMPT 面向真实 trigger 尚未到来的删除决策。

## 2.3 Proactive Memory and Synthetic Practice

包括：

- PREPING；
- Proactive Memory Agent。

承认“主动生成任务”和“主动 memory intervention”本身已经有先例。[PREPING](https://arxiv.org/abs/2605.13880)、[Proactive Memory Agent](https://arxiv.org/html/2607.08716)

最终建议放一个紧凑的近邻比较表：

| Method | Unseen trigger | Active witness | Item eviction CF | Executable severe outcome | Actual retention | Testing budget |
|---|---:|---:|---:|---:|---:|---:|
| OSL-MR | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| CMI | ✗ | ✗ | ✓ | ✗ | 部分 | ✗ |
| ASSAY | ✗ | ✗ | ✓ | ✓ | Skill curation | ✗ |
| PREPING | ✓ | ✓ | ✗ | ✓ | Memory writing | 部分 |
| Proactive Memory Agent | 部分 | ✗ | ✗ | ✓ | ✗ | ✗ |
| PREEMPT-Mem | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

# 3. Problem Formulation

这一节要把 Story 变成严格问题。

## 3.1 研究对象

明确只研究：

> 显式、非参数化、可寻址、可删除和恢复的 external episodic/semantic memory。

排除：

- 参数权重中的内部知识；
- 普通 KV cache；
- procedural skill/code；
- 物理或合规意义上的永久删除。

Active context 只是 memory 的暴露层，不是第二个主研究对象。

## 3.2 Rarity

对于 memory \(m_i\) 和冻结的未来任务分布 \(\mathcal D_{\text{future}}\)，定义 need indicator：

\[
N_i(z)\in\{0,1\},
\]

表示完成未来任务 \(z\) 是否需要 \(m_i\)。

定义 rarity：

\[
\rho_i =
\Pr_{z\sim\mathcal D_{\text{future}}}
\left[N_i(z)=1\right].
\]

当：

\[
\rho_i\le \tau_r
\]

时，认为该 memory 在当前评测分布下 rare。

必须说明：

- 分母是 tasks、episodes 还是 event families；
- 阈值 \(\tau_r\) 如何预先确定；
- historical retrieval frequency 只是代理，不是真值。

## 3.3 Criticality

定义删除效应：

\[
\Delta_i(z)=
L\big(A(M\setminus\{m_i\},z)\big)
-
L\big(A(M,z)\big).
\]

条件性 criticality：

\[
c_i=
\mathbb E\left[
\Delta_i(z)
\mid N_i(z)=1
\right].
\]

当：

\[
c_i\ge\tau_c
\]

时，认为该 memory critical。

于是：

\[
m_i\text{ is rare-but-critical}
\iff
\rho_i\le\tau_r
\land
c_i\ge\tau_c.
\]

不要用 \(P\times Severity\) 定义 criticality，否则 rare 会再次把严重度压低。

## 3.4 双预算问题

需要同时定义：

- memory budget \(B_m\)；
- counterfactual testing budget \(B_t\)。

目标可以写成：

> 在满足平均任务效用约束的前提下，最小化 severe failure/tail risk。

不要为了显得理论而写一个与实际算法无关的复杂目标；最终公式必须与代码和评估一致。

---

# 4. Characterizing Rare-but-Critical Memory

这是论文成立的前置证据，应当放在方法前面。

标题可以更有冲击力：

> **Do Agents Forget What Matters Before Retrieval Even Begins?**

这一节回答三个问题：

## RQ1：rare-but-critical memory 是否真的存在？

需要报告：

- 多少 memory 属于四个象限；
- 是否不止几个手工案例；
- natural、adapted、constructed 各占多少；
- 置信区间。

## RQ2：现有策略是否更容易删除它们？

比较：

- LRU/recency；
- LFU/frequency；
- semantic relevance；
- LLM importance；
- random；
- pinning；
- 强 retention baseline。

## RQ3：删除是否真的导致严重后果？

通过 Full/Evicted 运行确认：

- task failure；
- policy violation；
- irreversible/collateral state change；
- repeated invalid action；
- cost escalation。

这里必须出现 Figure 2：

- 横轴：future need frequency；
- 纵轴：conditional eviction loss；
- 左上角：rare-but-critical；
- 用不同颜色标出各 retention policy 删除的 memory。

这可能是整篇论文最有记忆点的图。

---

# 5. PREEMPT-Mem

## 5.1 Eviction Candidate

PREEMPT 不重新评估整个 memory store，只处理现有 retention policy 准备淘汰的候选项。

这使方法能接入不同 memory system。

## 5.2 Prospective Risk Triage

低成本估计：

- possible failure mode；
- severity prior；
- evidence gap；
- witness feasibility；
- uncertainty/detectability。

FMEA 只作为这一结构化 schema 的灵感来源，不使用传统 RPN。

需要比较：

- random triage；
- severity-only；
- generic LLM risk score；
- FMEA-inspired schema；
- Full Counterfactual oracle。

## 5.3 Future Decision Witness Generation

对候选 memory \(m_i\)，生成一组尚未真实发生的可执行情境：

\[
W_i=\{w_{i1},\ldots,w_{iK}\}.
\]

要求：

- 与 memory 内容相关但不是机械改写；
- 符合环境 API 和状态约束；
- 不接触 held-out future evaluation tasks；
- 能被确定性 evaluator 判分；
- 记录 invalid witness rate。

这一节是最核心、也最需要技术细节的部分。

## 5.4 Executable Counterfactual Validation

从同一环境快照运行：

- **Full**：memory 正常存在；
- **Evicted**：normal data plane 完全不可达；
- **Restore**：恢复相同 item、ID、索引和 metadata。

主效应：

\[
\widehat{\Delta}_i =
L_{\text{Evicted}}-L_{\text{Full}}.
\]

Restore 只检验：

\[
L_{\text{Restore}}\approx L_{\text{Full}},
\]

用于发现缓存污染、环境漂移或删除实现错误，不是第三个独立因果效应。

## 5.5 Risk-Aware Retention

把验证后的严重度、正常 utility 和 memory size 一起用于选择。

需要明确：

- 哪些 memory 被 pin/protect；
- testing budget 用完时怎么办；
- 未被测试候选如何处理；
- memory 交互或冗余如何处理。

建议提供 Algorithm 1，完整伪代码放附录。

---

# 6. Experimental Setup

## 6.1 Main and Auxiliary Tracks

### AppWorld 主轨

负责：

- 可执行工具行为；
- checkpoint/reset；
- database state tests；
- collateral damage；
- Full/Evicted/Restore。

每条数据标记：

- natural；
- adapted；
- constructed。

### LongMemEval-V2 辅轨

负责：

- workflow；
- gotcha；
- dynamic state；
- premise awareness；
- 自然化 memory；
- 外部有效性。

但它本质上是 evidence gathering + QA，不能用来声称严重工具后果。

## 6.2 数据划分

必须有：

- memory/source episodes；
- witness generation split；
- development split；
- held-out future trigger test split。

同一生成器不能同时生成测试问题、定义标签和担任最终裁判。

40-memory 可以作为 Pilot，但正式 ICLR 实验最好扩大到至少上百个可审计 memory-task units，否则统计说服力偏弱。

## 6.3 Baselines

至少四类：

1. **简单 retention**
   - Random
   - LRU
   - LFU
   - relevance

2. **学习或 LLM retention**
   - importance scorer
   - Learning What to Remember
   - OSL-MR/CURATOR 类方法

3. **因果测试**
   - Random Counterfactual
   - Severity-only
   - CMI/ASSAY 式已知任务干预
   - Full Counterfactual Oracle

4. **系统上下界**
   - Keep All
   - No Memory
   - Gold Pinning/Oracle Retention

## 6.4 公平控制

所有方法保持一致：

- memory budget；
- token budget；
- retrieval top-k；
- Agent 模型；
- tool-call budget；
- 环境快照；
- seeds；
- future-task split。

---

# 7. Results and Analysis

本节按研究问题组织，不按模型组织。

## 7.1 RQ1：问题是否存在？

报告：

- rare-critical 数量和比例；
- 四象限分布；
- baseline eviction rate；
- 不同 memory 类型的分布。

## 7.2 RQ2：PREEMPT 是否减少严重失败？

主结果表建议为：

| Method | Task Success ↑ | Severe Failure ↓ | RBC Recall ↑ | Avg Utility ↑ | Memory Cost | Test Rollouts |
|---|---:|---:|---:|---:|---:|---:|

核心不是只提高平均 success，而是：

> 在相同 memory budget 下显著降低 severe failure，同时平均表现基本不下降。

## 7.3 RQ3：额外测试成本是否值得？

画 Figure 3：

- 横轴：counterfactual rollout/test cost；
- 纵轴：severe failure rate 或 protected RBC recall；
- 比较 random、severity-only、FMEA-inspired、PREEMPT、Full CF。

这张 Pareto 图支撑双预算贡献。

## 7.4 RQ4：Witness 是否能预测独立真实 trigger？

报告：

- witness validity；
- precision/recall；
- risk calibration；
- witness risk 与 held-out deletion loss 的相关性；
- false positive/negative；
- cross-generator/cross-judge 稳定性。

这一节决定方法是否存在自证循环。

## 7.5 RQ5：是否泛化？

比较：

- natural vs adapted vs constructed；
- workflow/gotcha/constraint/preference；
- 不同模型；
- 不同 memory budget；
- AppWorld → LongMemEval-V2 或另一环境。

## 7.6 Ablations

至少包括：

- 去掉 triage；
- severity-only；
- 不生成 candidate-specific witness；
- 不进行真实执行，只用 LLM judge；
- 不同 witness 数量；
- 不同 testing budget；
- 不同 rare/critical 阈值；
- generic triage vs FMEA-inspired schema。

Restore 不适合作为“去掉后性能是否下降”的普通方法消融；它主要是因果完整性检查。

## 7.7 Error Analysis

分析：

- contrived/invalid witnesses；
- memory 冗余导致 remove-one 效应为零；
- 多条 memory 互补；
- retriever 没有取回 Full memory；
- reader 取回后仍然忽略；
- constructed case 不能迁移；
- triage 漏掉高严重度 memory。

---

# 8. Limitations and Conclusion

## Limitations

必须主动写清：

- AppWorld 可能是 controlled/semi-synthetic lifecycle；
- 只研究 external addressable memory；
- item-level intervention 不完全处理 memory interaction；
- witness generator 可能继承模型偏差；
- effective eviction 不等于物理或合规删除；
- 反事实执行成本仍然较高；
- 无法从平衡数据估计生产世界 prevalence。

## Conclusion

用两段即可：

1. 总结发现：过去访问频率不能可靠表示未来严重性。
2. 总结方法：PREEMPT 把 memory retention 从被动评分升级为删除前的主动风险测试。

最后一句可以回扣全文 Story：

> **An agent should not have to suffer a rare failure before learning what it must remember.**

---

# 正文之后必须包含

按照 ICLR 2027 要求和建议：

- **AI Use Statement：必须；**
- Reproducibility Statement：强烈建议；
- Ethics Statement：本项目涉及自动化工具行为和风险情境，建议提供；
- References；
- Appendix。

附录建议包含：

- 完整定义和额外证明；
- 数据构造与标注协议；
- 所有 prompts；
- Algorithm 完整版本；
- AppWorld reset/effective eviction checklist；
- 完整 baseline 参数；
- 额外结果与置信区间；
- witness 和 failure 案例；
- 全部 tool-call/state-diff 日志；
- 数据许可和模型信息。

核心结果、主方法和关键因果完整性不能只放附录，因为 ICLR 明确说明审稿人没有义务阅读附录。

## 最终论文主线

整篇论文最终应当让审稿人依次接受六件事：

1. **Agent 必须删除 memory；**
2. **rare 与 critical 不是一回事；**
3. **现有 retention 确实会删除 rare-but-critical memory；**
4. **删除确实造成可恢复的严重因果损失；**
5. **PREEMPT 能在真实 trigger 到来前发现这种风险；**
6. **这种发现能力在同等预算下带来足够大的收益，值得额外成本。**

只要这六层证据完整，这篇论文的 Story 就会非常顺；如果第 3、4、5 层缺少实验证据，即使 Introduction 和方法写得再 fancy，也很难支撑 ICLR 投稿。
