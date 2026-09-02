# PREEMPT-Mem 可行性报告 v1.1

> 首选工作题目：**Remember Before It Matters: Preemptive Counterfactual Retention for Rare-but-Critical Agent Memory**  
> 当前方法名：**PREEMPT-Mem**（如有实质更优名称可以调整）  
> v1.1 修订原则：保留 v1 的 Story 与方法主线；FMEA 降为可选的风险筛选设计，不影响核心 Idea 是否成立。

结论很明确：**PREEMPT-Mem 可行，且具有中上水平的 novelty 潜力。** 最有竞争力的地方不是“rare-but-critical”这个概念，也不是单独引入 FMEA，而是：

> **在真实触发事件发生前，主动寻找“删除某段记忆可能造成严重后果”的未来情境，并用可执行反事实实验验证，再把验证结果用于实际记忆保留。**

当前 Idea 的综合判断是：

| 维度 | 评价 |
|---|---:|
| 问题价值 | 8.5/10 |
| Story 吸引力 | 8.5/10 |
| 方法可实现性 | 8/10 |
| 数据可行性 | 7/10 |
| Novelty 潜力 | 7–7.5/10 |
| 当前 ICLR 投稿可行性 | 7/10 |

---

## 1. 这个研究问题是真实成立的

近期 Agent Memory 研究已经注意到：

- 长期压缩可能丢失 low-frequency details；
- rare but important knowledge 容易被访问频率或时间衰减策略淘汰；
- 当前系统仍缺少可靠的 memory importance 估计和 selective forgetting 方法。

相关综述与近期工作已经承认 rare-but-important 现象，因此我们不应宣称首次发现“低频信息也可能重要”。[Agent Memory Survey](https://arxiv.org/html/2603.07670)、[Rethinking Memory Mechanisms of Foundation Agents](https://arxiv.org/html/2602.06052v3)

论文真正需要建立的是：

1. 在历史或独立任务流中，一部分 memory 的触发频率确实较低；
2. 删除这些 memory 后，Agent 的任务损失、违规率或错误操作明显增加；
3. recency、frequency、relevance、importance/value 方法容易将其中一部分排到淘汰端；
4. PREEMPT-Mem 能在真实触发前发现并保护其中一部分。

最直观的主图可以是：

- 横轴：memory 的触发或需求频率；
- 纵轴：该 memory 被淘汰后的反事实损失；
- 左上角：rare-but-critical memory；
- 标出不同 retention policy 淘汰了哪些点。

这既证明现象存在，也自然引出方法。

### Rare 与 critical 应分开

- **Rare**：在独立 future-task distribution 中，真正需要该 memory 的任务出现概率较低；
- **Critical**：在任务确实需要该 memory 的条件下，缺失造成的决策损失或严重后果较高。

历史 retrieval count 可以作为 rarity 的代理，但不能直接当作真值，因为低 retrieval 也可能来自检索失败。Criticality 也不能与 semantic importance 或 relevance 混为一谈。

---

## 2. 真正的 novelty 在哪里

当前最接近的工作主要有：

| 现有工作 | 已经做了什么 | PREEMPT-Mem 的差异 |
|---|---|---|
| CURATOR | 根据 retrieval propensity、helpfulness、harm 和存储成本决定保留什么 | 主要依赖已观察数据，没有主动构造未见未来情境 |
| DeMem | 用 downstream decision loss 定义记忆压缩质量 | 根据已出现的 decision conflict 学习，没有在真实 trigger 前主动压力测试 |
| What Eviction Destroys | 对给定问题做 per-item restore-counterfactual eviction audit | 测试问题已经给定；PREEMPT 主动生成尚未发生的 future witness |
| Governance Decay | 证明压缩会删除安全约束，并用 constraint pinning 保护 | 主要保护明确标注的治理规则；PREEMPT 识别没有显式标签的条件性关键记忆 |
| MemAudit | 在有害行为发生后，用反事实 replay 找出有害记忆 | 是事后修复；PREEMPT 是删除前保护有益记忆 |

对应论文包括 [CURATOR](https://arxiv.org/html/2606.25115v1)、[DeMem](https://arxiv.org/html/2605.10870v1)、[What Eviction Destroys](https://openreview.net/forum?id=8rOh73WoJh)、[Governance Decay](https://arxiv.org/html/2606.22528v2) 和 [MemAudit](https://arxiv.org/html/2605.23723v1)。

因此，目前最清楚的创新点是：

> **现有方法通常根据过去的使用情况、已经到来的任务或已经发生的失败估计记忆价值；PREEMPT-Mem 在未来任务尚未到来时，主动构造可能暴露遗忘风险的情境，并通过真实 Agent 执行获得删除风险证据。**

可以将这一视角称为：

> **Pre-trigger Counterfactual Memory Risk Discovery**

必须区分：

- **pre-deletion**：删除动作尚未执行；
- **pre-trigger**：真实需要该 memory 的任务尚未发生，系统主动生成测试情境。

PREEMPT-Mem 的主要亮点是 pre-trigger，而不是普通的删除前打分。

同样需要避免以下错误表述：

- 首次研究 memory importance 或 future utility；
- 首次学习 memory deletion；
- 首次使用 downstream decision loss；
- 首次对 memory 做 remove/restore counterfactual；
- Full/Evicted/Restore 本身是 novelty；
- 首次把 FMEA 用于 AI Agent。

最重要的差异组合是：

> **pre-trigger generation + executable validation + actual retention decision。**

---

## 3. FMEA 应该怎样进入方法

FMEA **不是论文必须使用的组件**，也不应该成为唯一 spotlight。它当前最有价值的作用，是为低成本风险筛选提供一种结构化思路。

如果对每条待删除 memory 都生成未来场景，再执行 Full/Evicted/Restore，成本会很高。因此论文仍然需要：

\[
\text{全部待删除记忆}
\rightarrow
\text{低成本前瞻风险筛选}
\rightarrow
\text{高风险候选}
\rightarrow
\text{PREEMPT反事实验证}.
\]

FMEA 可以作为这一筛选步骤的候选实现：

| FMEA 概念 | Agent Memory 中的对应含义 |
|---|---|
| Failure Mode | 关键 memory 被删除、压缩失真或无法检索 |
| Severity | 删除后造成的任务失败、违规或错误操作程度 |
| Occurrence | 未来触发该 memory 的可能性 |
| Detection | 普通 retention policy 在失败前发现风险的能力 |
| Risk Priority | 是否值得运行昂贵的 PREEMPT 验证 |

但不能机械采用传统 \(S\times O\times D\)，因为 rare memory 的 occurrence 天然较低，乘法可能把极高 severity 的条目继续压到低风险区。

因此，当前更准确的表述是：

> **Prospective Risk Triage，初步可以采用 FMEA-inspired risk decomposition。**

FMEA 是否最终进入主文，由实验决定：

- 如果 FMEA-inspired triage 在相同 rollout budget 下显著提高 rare-critical candidate recall 或改善风险—成本 Pareto，则以可解释的筛选实现保留；
- 如果它不比更简单的 risk-aware candidate selection 更好，则删除 FMEA 名称，但保留低成本筛选功能；
- FMEA 的去留不会改变 PREEMPT-Mem 的核心 novelty。

---

## 4. 应该研究哪种记忆

建议主研究对象确定为：

> **Agent 的非参数化、可显式操作的记忆，即外部长期 memory store 中可寻址的 episodic/semantic memory，以及它们加载到当前上下文后的有效可用状态。**

不研究模型权重中的内部知识，也不把普通 KV-cache token pruning 作为主问题。

原因很直接：

- memory item 可以获得稳定 ID；
- 可以明确执行删除和恢复；
- 可以记录历史使用频率；
- 可以使用公开 Agent trajectory；
- Full/Evicted/Restore 的因果语义更清楚；
- 实验结果更容易解释。

这里的 deletion 更适合定义为 **effective eviction**：

> 目标 memory 在规定的 memory budget、检索接口和正常 Agent 权限下不再可用。

实验系统可以保留一个 Agent 无法访问的审计副本，用于 Restore。这避免把研究不必要地限定成物理永久擦除。

方法工作的具体位置是：

> 当外部 memory store 或 active context 即将淘汰某条 memory item 时，PREEMPT-Mem 决定是否允许其 effective eviction。

---

## 5. 数据问题可以解决

公开数据足以启动研究，但需要组合使用。

### 自然 Agent Memory 数据

[LongMemEval-V2](https://arxiv.org/abs/2605.12493) 提供公开 Web Agent 历史轨迹，包含：

- workflow knowledge；
- environment gotchas；
- dynamic state；
- premise awareness；
- 过去失败和环境经验。

其[官方仓库](https://github.com/xiaowu0162/LongMemEval-V2)和数据适合提供较自然的 memory 内容。

[MemoryAgentBench](https://arxiv.org/abs/2507.05257) 和 [LongMemEval](https://arxiv.org/abs/2410.10813) 可以作为普通长期记忆表现的补充，但主要衡量检索和回答准确率，不足以单独表示严重后果。

### 高损失 Agent 行为数据

[Governance Decay](https://arxiv.org/html/2606.22528v2) 的 ConstraintRot 证明，压缩丢失约束可以导致严重且可确定性评分的工具行为变化。这说明“删除 memory 导致重大后果”可以在安全的模拟环境中被构造成可执行 benchmark。

最合适的数据方案是：

1. 用 LongMemEval-V2 等公开轨迹提供自然 memory；
2. 从 workflow、environment gotchas、动态状态和用户例外中筛选潜在 critical memory；
3. 补充具有确定性工具结果的高后果场景；
4. 构造 rare/critical、rare/non-critical、frequent/critical、frequent/non-critical 四类对照；
5. 用独立 future trigger 检查 PREEMPT 生成的 witness 是否真的提供可迁移的风险证据。

第五点是关键实验控制，但不需要将整篇论文改写成 witness 泛化评测。

因此，没有公司第一手日志不是核心障碍。

---

## 6. 推荐的最终方法结构

PREEMPT-Mem 可以收敛成五个步骤：

1. **Eviction Candidate**  
   由现有 retention policy 选出准备删除的 memory。

2. **Prospective Risk Triage**  
   低成本识别哪些候选更值得运行昂贵验证。FMEA-inspired decomposition 是候选实现，不是预设必要条件。

3. **Future Decision Witness Generation**  
   为候选 memory 主动生成一个合理、可执行、尚未发生的未来任务，使该 memory 的存在与否可能改变 Agent 决策。

4. **Full/Evicted/Restore Counterfactual Validation**  
   在相同任务和环境下执行：

   - Full：保留目标 memory；
   - Evicted：目标 memory effective eviction；
   - Restore：从审计副本恢复后重放。

   Full–Evicted 是主要 effect estimate；Restore 用于检查行为能否恢复，并降低随机性或执行漂移造成的误判。

5. **Risk-aware Retention**  
   根据经过执行验证的 forgetting loss 决定保留什么，并在相同 memory budget 下与现有策略比较。

论文最关键的实验问题是：

> **在相同 memory budget 和 counterfactual rollout budget 下，PREEMPT-Mem 是否比 recency、frequency、semantic/learned importance 和随机反事实抽样保护了更多 rare-but-critical memory，并降低独立未来任务上的严重失败率？**

---

## 7. 可以形成的论文贡献

### Contribution 1：问题贡献

系统揭示现有 Agent retention 方法在 rare-but-critical memory 上的盲区，并通过“触发频率—条件性删除损失”二维分析量化该现象。

### Contribution 2：方法贡献

提出 PREEMPT-Mem，在真实触发出现前生成 Future Decision Witness，通过可执行 memory intervention 获得 pre-trigger counterfactual supervision，并将其用于实际 retention。

### Contribution 3：效率贡献

提出 selective prospective risk testing，将昂贵反事实执行集中在最值得验证的 eviction candidates 上，在控制 rollout cost 的同时提高关键记忆保留率。

FMEA 不单独列为贡献。只有实验证明 FMEA-inspired triage 具有独立增益时，才作为 Contribution 3 的一个具体实现出现。

---

## 8. 最关键的实验图

主结果应是一条“平均性能—严重风险—测试成本”的 Pareto 曲线。

同一 memory budget 下比较：

- recency/LRU/LFU；
- relevance；
- semantic/LLM importance；
- learned future-value baseline；
- random counterfactual testing；
- full counterfactual testing；
- PREEMPT-Mem。

Prospective Risk Triage 可以额外比较 generic 与 FMEA-inspired 两种实现，但不需要因此把论文变成三套方法的竞争。

最理想的结果是：

> PREEMPT-Mem 与最佳基线平均成功率接近，但在未见 rare triggers 上显著降低 severe failure，同时只使用全量反事实测试的一小部分成本。

---

## 最终判断

这个 Idea 不是简单地给 memory 多打一个 importance score，而是在改变记忆删除决策的逻辑：

> **现有方法问：这段记忆过去看起来有多有用？**  
> **PREEMPT-Mem 问：在真正忘记它之前，我们能否提前发现忘记它会造成什么后果？**

FMEA 可以增强低成本风险筛选的解释性，但不决定论文是否成立。真正应该被读者记住的是：

> **Agent 在第一次真实失败之前，主动生成未来测试，学习什么不能忘记。**
