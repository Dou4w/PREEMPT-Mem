# PREEMPT-Mem：论文完整 Story v1.1

## 核心 Story

> **Agent 不应该先经历一次严重失败，才能知道哪段记忆必须保留。**

PREEMPT-Mem 研究的不是普通“记忆重要性评分”，而是：

> **在 Agent 真正删除一段记忆前，提前发现忘记它可能造成的未来严重后果。**

当前首选题目：

> **Remember Before It Matters: Preemptive Counterfactual Retention for Rare-but-Critical Agent Memory**

中文：

> **在真正需要之前记住它：面向低频关键 Agent 记忆的前瞻式反事实保留**

`PREEMPT-Mem` 是当前方法名。如果后续出现更准确、更好记且不与近邻工作冲突的名称，可以调整；但不能因命名改变核心 Story。

---

# 一、论文完整 Story 线

## 第一幕：Agent 必须遗忘

长期运行的 Agent 会不断积累：

- 用户事实和偏好；
- 历史任务经验；
- 工具使用方法；
- 环境状态；
- 权限和操作规则；
- 任务之间的依赖关系。

但是上下文窗口、检索预算和存储空间有限，因此 Agent 必须压缩或删除一部分记忆。

现有方法通常根据以下信号决定删除什么：

- relevance；
- recency；
- frequency；
- semantic importance；
- redundancy/reconstructability；
- 过去是否帮助过任务；
- learned future value；
- 人工 pinning。

这些方法虽然越来越复杂，但主要使用的证据仍然来自过去访问、已经出现的任务或已经观察到的反馈。

它们本质上都在回答：

> **这段记忆过去或在当前任务中看起来有多有用？**

---

## 第二幕：过去不重要，不代表未来不关键

假设 Agent 记住了三段信息：

1. Alice 属于特殊客户组 B；
2. 客户组 B 的退款上限是 £500；
3. 超过上限需要经理批准。

Alice 几个月没有申请过大额退款，因此第一条记忆几乎没有被使用。它看起来既不新，也不常用，甚至不像一条明显的安全规则。

压缩器因此将它删除。

当 Alice 第一次申请 £720 退款时：

- Agent 仍然记得“超过 £500 需要审批”；
- 但已经忘记 Alice 属于客户组 B；
- 所以直接执行退款。

这里真正关键的不是显式审批规则，而是一段看起来普通、只有在特定未来情境中才会改变决策的条件性事实。

这就是 rare-but-critical memory：

- **Rare**：在未来任务分布中很少被真正需要；
- **Critical**：一旦未来任务需要它，删除会造成严重决策损失。

“低频信息也可能重要”并不是本文首次发现。本文真正要解决的是：

> **如何在它第一次真正重要之前，主动获得足以指导 retention 的行为证据？**

---

## 第三幕：现有 retention policy 存在事后学习盲区

如果一条记忆从未在历史任务中被真正使用，系统就很难从访问日志中证明它重要。

只有当真实触发事件出现后，系统才可能观察到：

> 原来删除这段记忆会导致严重失败。

但对于 rare-but-critical memory：

> **第一次产生“这段记忆很重要”的学习信号，也可能正是第一次不可逆失败。**

更强的 importance scorer 或 future-value predictor 可以改善平均 retention，但预测本身不等于行为验证；已经观察到的 decision conflict 也无法覆盖尚未出现的 trigger。

论文的科学问题由此自然出现：

> **当关键触发事件尚未在历史日志中出现时，Agent 能否在删除记忆前主动发现其未来风险？**

这里必须区分：

- **pre-deletion**：删除尚未发生；
- **pre-trigger**：真实需要该记忆的未来任务尚未发生。

PREEMPT-Mem 的亮点是 pre-trigger counterfactual supervision。

---

## 第四幕：把记忆删除从压缩问题改写为风险测试问题

传统记忆管理把删除看作：

> 哪些内容最不值得继续占用预算？

PREEMPT-Mem 将其改写为：

> **如果删除这段记忆，它可能在什么未来情境下导致 Agent 失败？我们能否在真实失败发生前先运行一次这样的测试？**

这是一种 prospective risk analysis：

\[
\text{潜在遗忘风险}
\rightarrow
\text{未来场景生成}
\rightarrow
\text{记忆删除干预}
\rightarrow
\text{Agent执行验证}.
\]

FMEA 可以为 failure mode、severity、occurrence 和 detectability 的分解提供设计灵感，但不是论文必须使用的框架。论文真正需要保留的是：

> **低成本风险筛选 + 可执行未来测试。**

如果 FMEA-inspired 筛选不能比更简单的 risk-aware selection 带来独立价值，可以去掉 FMEA 名称，而不影响核心 Story。

---

## 第五幕：PREEMPT-Mem 方法

整个方法包含五个步骤。

### Step 1：得到准备删除的记忆

现有 retention policy 先根据 relevance、recency、frequency、importance 或 learned value，提出 eviction candidates。

PREEMPT-Mem 不替代所有压缩方法，而是作为删除前的风险控制层。

这里的 deletion 优先定义为 **effective eviction**：目标 memory 在规定预算、正常检索接口和 Agent 权限下不再可用。系统可以保留 Agent 无法访问的审计副本，用于 Restore。

### Step 2：Prospective Risk Triage

不可能对所有 memory 都运行昂贵反事实实验，因此先用低成本信号判断哪些候选最值得测试：

- 在什么未来情境中可能被需要；
- 删除后可能造成什么后果；
- 后果是否严重；
- 普通 retention policy 是否容易漏掉它；
- 运行验证的成本是否合理。

这一阶段解决的是：

> **有限的 counterfactual testing budget 应该优先花在哪些 eviction candidates 上？**

该筛选可以采用 FMEA-inspired risk decomposition，也可以采用更一般的 risk-aware candidate selection。最终名称和实现由实验效果决定。

### Step 3：生成 Future Decision Witness

对于高风险候选，主动生成一个合理、可执行、尚未在历史中发生的未来任务：

> 能否找到一个未来情境，使这段 memory 的存在与否改变 Agent 的正确决策？

例如，为“Alice 属于客户组 B”生成：

> Alice 请求通过退款工具退款 £720。

这个未来情境称为：

> **Counterfactual Future Decision Witness**

有效 witness 不能只是把 memory 原文机械改写成问题。它需要来自可信任务空间，能够实际执行并由可靠 evaluator 判断结果。

### Step 4：Full/Evicted/Restore 反事实验证

在完全相同的任务和环境下执行三次：

| 条件 | Memory 状态 | Agent 行为 |
|---|---|---|
| Full | 目标 memory 正常可用 | 正确请求经理审批 |
| Evicted | 目标 memory effective eviction | 直接退款，发生违规 |
| Restore | 从审计副本恢复目标 memory | 重新请求审批 |

如果行为呈现：

\[
\text{正确}\rightarrow\text{失败}\rightarrow\text{正确},
\]

就能获得目标 memory 缺失造成决策损失的强证据。

Full/Evicted 是主要 effect estimate；Restore 用来检查行为能否恢复，并降低随机性、执行漂移或环境异常造成的误判。Full/Evicted/Restore 本身不是 novelty，主动生成尚未出现的 Future Witness 才是关键区别。

### Step 5：Risk-aware Retention

验证结果随后用于真正的保留决策：在固定 memory budget 下，优先保护经执行验证具有高遗忘风险的 memory，同时允许低风险条目继续淘汰。

为避免自生成任务上的闭环自证，需要用独立 future triggers 检查 witness 上观察到的 forgetting risk 是否能迁移到真实测试任务。它是一项关键验证实验，但不是论文 Story 的新主角。

---

# 二、论文最亮眼的四项贡献

## Contribution 1：从“历史重要性”转向“未来遗忘后果”

现有方法主要估计：

> 这段 memory 过去是否有用，或在当前任务中是否相关？

PREEMPT-Mem 关注：

> **如果未来确实需要它，删除会造成多大损失？**

论文将 memory value 拆成两个不同维度：

- 触发概率：未来多大概率真正需要它；
- 条件损失：一旦需要，忘记它有多严重。

这使 rare-but-critical memory 不再被压缩进一个模糊的 importance score。

一句话贡献：

> **We shift agent memory retention from retrospective utility estimation to prospective forgetting-risk analysis.**

---

## Contribution 2：Pre-trigger Counterfactual Supervision

这是论文最核心、最容易被审稿人记住的贡献。

现有方法通常依赖：

- 已经观察到的访问记录；
- 已经发生的任务；
- 已经出现的 decision conflict；
- 已经发生的失败；
- 未经执行验证的 future-value prediction。

PREEMPT-Mem 在真实 trigger 发生前：

1. 主动生成未来决策情境；
2. 删除目标 memory；
3. 实际运行 Agent；
4. 恢复目标 memory；
5. 验证行为是否恢复；
6. 将得到的证据用于 retention。

一句话贡献：

> **PREEMPT-Mem actively creates supervision for unseen memory risks before their real triggers occur.**

---

## Contribution 3：Selective Prospective Risk Testing

PREEMPT-Mem 不把风险分析停留在一个 LLM 分数，而是把它转化为有限预算下的可执行测试策略：

\[
\text{风险候选}
\rightarrow
\text{未来场景}
\rightarrow
\text{记忆干预}
\rightarrow
\text{行为证据}.
\]

它回答的是：

> 在不能测试全部 memory 时，应该优先为哪些 eviction candidates 主动生成和执行未来测试？

FMEA-inspired decomposition 可以成为一种筛选实现，但贡献本身是 selective prospective testing，而不是 FMEA 的跨领域迁移。

一句话贡献：

> **We turn prospective forgetting-risk hypotheses into targeted, executable tests for memory eviction.**

---

## Contribution 4：低成本筛选与高可信验证的闭环保留

直接对全部 memory 执行 Full/Evicted/Restore 成本过高。

PREEMPT-Mem 采用：

\[
\text{Cheap Risk Triage}
\rightarrow
\text{Targeted Counterfactual Validation}
\rightarrow
\text{Risk-aware Retention}.
\]

最终不是只输出风险报告，而是在相同 memory budget 下真正决定保留什么。

预期达到：

- 平均任务性能基本不下降；
- rare-critical retention recall 提高；
- severe failure rate 显著下降；
- 反事实 rollout 数量远低于全量测试。

一句话贡献：

> **PREEMPT-Mem protects rare-critical memories under practical budgets by concentrating expensive counterfactual tests on high-risk eviction candidates.**

---

# 三、与近邻工作的统一差异

| 方向 | 它们回答的问题 |
|---|---|
| Recency/Frequency | 过去多常使用？ |
| Semantic importance | 看起来有多重要？ |
| Learned future value | 根据已知分布预测未来是否有用？ |
| Decision-centric compression | 已观察任务中是否影响决策？ |
| Restore audit | 给定问题的失败是否由记忆删除造成？ |
| Constraint pinning | 哪些已知规则必须永久保留？ |
| **PREEMPT-Mem** | **在未来任务尚未出现时，忘记它可能造成什么严重后果？** |

最重要的差异不是 counterfactual 本身，而是：

> **pre-trigger generation + executable validation + actual retention decision。**

---

# 四、整篇论文最关键的实验图

主结果应该是一条“平均性能—严重风险—测试成本”的 Pareto 曲线。

同一 memory budget 下比较：

- recency/LRU/LFU；
- relevance；
- semantic importance；
- learned future-value baseline；
- random counterfactual testing；
- full counterfactual testing；
- PREEMPT-Mem。

风险筛选模块可以增加 generic 与 FMEA-inspired 两个消融，但它们不应变成两套平行论文主线。

最理想的结果是：

> PREEMPT-Mem 与最佳基线平均成功率接近，但在未见 rare triggers 上显著降低 severe failure，同时只使用全量反事实测试的一小部分成本。

另一项关键实验是：Future Witness 上测得的 deletion loss 是否能预测独立 future trigger 上的真实 loss。该实验用于证明系统确实获得了有用的 pre-trigger supervision。

---

# 五、论文 Spotlight

这篇论文最应该被读者记住的不是 FMEA、RPN 或某个 risk score，而是下面两句话：

> **An agent should not have to suffer a rare failure before learning what it must remember.**

以及：

> **Before deleting a memory, ask not how useful it was in the past, but what failure its absence could cause in the future.**

最终完整定位是：

> **PREEMPT-Mem 是一个面向长期 Agent 的前瞻式记忆保留框架：它在有限测试预算下筛选值得验证的 eviction candidates，在真实触发事件发生前主动生成 Future Decision Witness，并通过 Full/Evicted/Restore 执行验证删除损失，从而在固定 memory budget 下保护 rare-but-critical memory。**

FMEA 可以是风险筛选的设计灵感，但 pre-trigger counterfactual supervision 才是论文身份。
