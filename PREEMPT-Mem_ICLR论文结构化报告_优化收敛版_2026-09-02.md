# PREEMPT-Mem：ICLR 论文结构化报告（优化收敛版）

> 版本日期：2026-09-02  
> 文档性质：ICLR 风格论文蓝图与证据计划，不是已经完成的投稿稿件。  
> 证据规则：明确区分 `EVIDENCED`、`HYPOTHESIS`、`PENDING` 与 `RISK`；任何待验证结果均不得写成论文结论。  
> 核心取舍：只突出“删除前生成的可执行风险测试，能否预测生成器不可见的未来遗忘损失”这一长板；其余设计仅用于支撑该主张。

---

## Title

### 推荐标题

**Remember Before It Matters: Preemptive Counterfactual Retention for Rare-but-Critical Agent Memory**

### 证据不足时的收缩标题

**Remember Before It Matters: Preemptive Counterfactual Retention for Agent Memory**

只有当独立 workload 确认 low-Need/high-loss 子群确实存在，且 PREEMPT 对该子群具有稳定增量时，才保留标题中的 `Rare-but-Critical`。

### 一句话核心贡献

> PREEMPT-Mem turns memory eviction from retrospective scoring into a pre-deletion falsification test: it generates executable future witnesses, measures deletion risk counterfactually, and evaluates whether that risk transfers to generator-hidden future tasks.

中文：

> PREEMPT-Mem 将记忆淘汰从“根据过去打分”转变为“删除前主动证伪”：生成可执行未来情境，通过反事实执行测量删除风险，并检验该风险能否迁移到生成器不可见的未来任务。

---

## Abstract（当前结构稿，结果句待填）

Long-horizon agents must maintain external memories under finite storage and context budgets. Existing retention policies predominantly score memories using retrospective evidence—frequency, recency, relevance, salience, or realized utility—and may therefore undervalue memories whose future need is rare but whose absence is consequential. We study whether an agent can test the risk of forgetting a memory before the corresponding future need is observed. We introduce PREEMPT-Mem, a baseline-agnostic retention layer that generates a structured, executable Future Decision Witness for each candidate eviction, validates the witness through paired Full, Evicted, and Restore executions, and vetoes risky evictions under fixed memory and testing budgets. To distinguish prospective prediction from self-constructed test validity, we evaluate every witness on future triggers that are frozen before generation and hidden from the generator. We separately measure storage-retention criticality, information criticality, and retrieval gaps, with diagnostic Full-Oracle and Decoy interventions where required. **[PENDING：主实验完成后填写 witness-to-hidden transfer、固定预算 severe-failure reduction、平均效用变化、模型与 memory family 覆盖。]** Our framework reframes memory maintenance as prospective risk discovery rather than purely retrospective importance estimation.

### 摘要最终必须包含的数值

- 独立 memory units 数量；
- hidden triggers 数量；
- 模型家族数量；
- PREEMPT 相对最强 baseline 的 hidden-transfer 增量；
- 相同双预算下 severe failure 的变化；
- 平均任务效用变化及置信区间。

摘要中不得写入当前 selector-channel Smoke 的分数作为方法效果。

---

# 1. Introduction

## 1.1 Motivation：历史重要性无法观察尚未发生的后果

长期运行的 Agent 会持续积累用户偏好、状态更新、工具经验、workflow prerequisite 和隐式约束。外部 memory store 的容量有限，系统必须不断决定保留什么、删除什么。

现有策略通常依赖：

- frequency；
- recency；
- relevance；
- semantic/LLM importance；
- realized historical utility。

这些信号都只能利用已经发生的历史。一条 memory 可能长期没有被需要，因此被判定为低价值；但在少数未来任务中，其缺失可能造成严重失败、权限违规或高代价状态变化。

本文研究的核心盲区是：

> Historical evidence can show what has mattered, but not necessarily what will matter catastrophically for the first time.

## 1.2 Problem：rare 与 critical 必须分开

本文将两者独立定义：

- **Rare**：在相关功能、权限和工具存在的 eligible opportunity 中，任务真正需要该信息的概率低；
- **Critical**：当任务确实需要该信息时，删除具体 memory 会造成高条件损失。

低历史频率不等于 rare，LLM 认为“重要”不等于 critical，检索失败也不等于 storage eviction。

## 1.3 Key insight：Test before forgetting

与其继续设计更复杂的历史 importance 公式，PREEMPT-Mem 在 memory 被删除前主动提出一个问题：

> 如果未来出现一个真正依赖这条信息的可执行任务，忘记它会发生什么？

方法生成结构化 Future Decision Witness，在相同环境快照下比较 Full、Evicted 与 Restore。若删除产生严重后果且恢复能够逆转，则否决该次淘汰。

## 1.4 The central scientific challenge：避免自证循环

仅在生成器自己构造的 witness 上验证并不充分。生成器可能直接复述 memory，并构造一个必然依赖该 memory 的任务。

因此，本文的核心评价要求是：

> witness-derived risk must predict deletion harm on future triggers that were frozen before witness generation and hidden from the generator.

这使论文从“自动生成测试”提升为“删除前预测未知未来风险”。

## 1.5 Contributions

论文只保留一个核心贡献和两个支撑贡献：

1. **核心贡献——Prospective Counterfactual Retention。**提出 PREEMPT-Mem，在候选 memory 被删除前生成可执行 future witness，通过反事实执行获得风险证据，并将其用于固定预算下的 eviction veto。
2. **支撑贡献——Generator-Blind Evaluation。**建立预先冻结的 hidden-trigger 协议，检验自生成风险测试能否迁移到生成器未见过的未来任务，而非仅在自身场景中自洽。
3. **支撑贡献——Fixed-Budget Evidence。**在多种冻结 retention baseline、多个 memory family 和至少两个模型家族上，评估相同 memory/testing budgets 下的平均效用—严重风险权衡。

以下内容不单列贡献：Need 定义、Full/Evicted/Restore、Witness compiler、Full-Oracle、Decoy、tail metric 和复现基础设施。它们是保证主贡献成立的必要支撑。

---

# 2. Related Work

## 2.1 Long-term memory for agents

讨论外部 Agent memory 的写入、表示、检索、更新、压缩和维护，并明确本文研究 item-level storage eviction，而不是参数记忆、KV cache 或一般 context compression。

相关工作应覆盖代表性类别，而不是穷举所有系统：

- stream/reflection memory；
- hierarchical/tiered memory；
- vector/graph/hybrid memory；
- learned retention and consolidation；
- memory maintenance under capacity limits。

## 2.2 Importance and budgeted forgetting

总结 frequency、recency、relevance、LLM importance、historical utility、future utility 和 decision-centric memory。

必须明确：decision consequence 已被研究，因此“使用决策损失衡量 memory”不能单独作为创新。DeMem 将 memory compression 表述为 decision-centric rate-distortion 问题，并研究固定预算下的决策保真。[DeMem](https://arxiv.org/abs/2605.10870)

## 2.3 Counterfactual memory audit

讨论 remove-one、evict/restore 和反事实审计。Restore counterfactual 已有近邻，因此 Full/Evicted/Restore 是本文的因果测量工具，不是唯一 novelty。[What Eviction Destroys](https://openreview.net/pdf?id=8rOh73WoJh)

## 2.4 Prospective memory and delayed triggers

TriggerBench 和 PM-Bench 已经研究 Agent 是否能在未来 cue 或状态出现时执行延迟意图，并揭示 false alarm、干扰和监控困难。因此“未来 trigger”本身也不能单独声称为创新。[TriggerBench](https://arxiv.org/html/2606.23459)、[PM-Bench](https://arxiv.org/html/2607.12385v1)

## 2.5 Novelty boundary

论文应使用能力矩阵明确差异：

| 工作方向 | 预算淘汰 | 删除/恢复因果 | 删除前生成测试 | Generator-hidden transfer | 用于保留决策 |
|---|---:|---:|---:|---:|---:|
| LRU/LFU/importance | 是 | 否 | 否 | 否 | 是 |
| Decision-centric memory | 是 | 部分 | 否 | 否 | 是 |
| Restore audit | 否/有限 | 是 | 否 | 否 | 否/有限 |
| Prospective-memory benchmark | 否 | 否 | 否 | 否 | 否 |
| **PREEMPT-Mem** | 是 | 是 | **是** | **是** | **是** |

提交前必须重新运行系统文献审计，确认完整组合仍未被覆盖。当前只能称为“最有潜力的新颖性边界”，不能提前声称 first-ever。

---

# 3. Problem Setup

## 3.1 Scope and system model

研究对象是可寻址的外部长期 memory item：

\[
m_i=(id_i, content_i, provenance_i, version_i, scope_i, cost_i, carriers_i).
\]

context 生效链被分为：

\[
\text{Memory Store}
\rightarrow \text{Retrieval}
\rightarrow \text{Context Selection}
\rightarrow \text{Agent Action}
\rightarrow \text{Environment Consequence}.
\]

必须区分：

1. storage absence；
2. retrieval miss；
3. active-context exclusion。

## 3.2 Need

Need 定义在信息命题上，而不是由 Agent 是否引用 memory 决定。若改变命题值会改变满足任务成功标准和硬约束的正确行为集合，则任务需要该命题。

该定义防止形成：

```text
未检索 → 判定不需要 → 更容易删除 → 继续无法检索
```

## 3.3 Rarity

先定义 eligible opportunity \(E_i(z)\)：任务中的功能、权限、工具和操作阶段使该信息有机会成为必要条件。随后定义：

\[
\rho_i=P(N_i=1\mid E_i=1).
\]

rarity 必须：

- evaluation-only；
- 由独立 held-out workload 估计；
- 不进入 generator、importance 或 retention rule；
- 报告 \(k/n\)、区间和 bottom-q 子组；
- 不用于推断真实部署 prevalence。

## 3.4 Criticality

本文区分三种量：

\[
\Delta_{retention}=L(Evicted)-L(FullRetrieval),
\]

衡量正常系统中的实际保留价值；

\[
\Delta_{info}=L(Evicted)-L(FullOracle),
\]

衡量信息被可靠提供时的能力上界；

\[
Gap_{retrieval}=L(FullRetrieval)-L(FullOracle),
\]

衡量 retrieval/context pipeline 未兑现的信息价值。

PREEMPT 的主结果使用 \(\Delta_{retention}\)。其余两项用于诊断。

## 3.5 Budgets and objective

设 storage budget 为 \(B_m\)，允许的深度 counterfactual audit budget 为 \(B_a\)。冻结 baseline \(b\) 先产生拟删除集合 \(D_b\)。PREEMPT 在不超过 \(B_a\) 的前提下测试候选，并在 \(B_m\) 内构造最终保留集合。

主评价不是一个复杂合成公式，而是比较：

- average utility；
- severe failure；
- rare-critical rescue；
- storage cost；
- audit cost；
- Pareto frontier。

## 3.6 Main research question

> Can pre-eviction executable witnesses predict deletion harm on generator-hidden future tasks and improve retention under fixed memory and testing budgets?

## 3.7 Hypotheses

- **H1 — Retrospective Blind Spot：**历史 retention baseline 会删除一部分 low-Need/high-loss memory。
- **H2 — Prospective Transfer：**witness-derived risk 能预测 generator-hidden future deletion loss，并优于直接 LLM risk、模板和随机场景。
- **H3 — Retention Value：**在相同 \(B_m,B_a\) 下，PREEMPT 降低 hidden-workload severe failure，同时维持平均效用。

H2 是决定论文长板是否成立的核心假设。

---

# 4. PREEMPT-Mem

## 4.1 Overview

```text
Frozen retention baseline proposes D_b
        ↓
Generate structured Future Decision Witness
        ↓
Compile for executability, oracle quality and leakage
        ↓
Run Full / Evicted / Restore on the witness
        ↓
Estimate prospective deletion risk
        ↓
Veto risky evictions under fixed storage budget
        ↓
Evaluate on generator-hidden future tasks
```

hidden tasks 只用于评价，不能被方法读取。

## 4.2 Baseline-agnostic candidate interface

PREEMPT 接收任意冻结 baseline 产生的待删除集合，而不是绑定一个自定义 importance 公式。

实验至少覆盖：

- LRU；
- LFU；
- semantic/LLM importance；
- realized utility 或兼容的 learn-to-evict 方法。

## 4.3 Future Decision Witness Generator

Generator 可以读取：

- memory content；
- provenance 与允许公开的 metadata；
- environment schema；
- tool schema；
- scenario generation protocol。

Generator 不得读取：

- hidden trigger；
- held-out rarity；
- Need label；
- gold action；
- evaluator；
- Full/Evicted/Restore 结果；
-最终 criticality。

输出：

```yaml
memory_id:
target_proposition:
failure_mode:
future_trigger:
initial_state:
user_request:
available_tools:
expected_correct_behavior:
predicted_consequence:
risk_direction:
success_oracle:
violation_oracle:
equivalent_information_paths:
```

## 4.4 Witness Compiler

在任何 Agent rollout 前检查：

- 工具和参数是否合法；
- 环境状态是否可达；
- 成功和违规是否可程序化评价；
- 是否只是复述 memory；
- 是否泄漏 hidden information；
- equivalent carriers 是否可封锁；
- 是否与已有 witness 重复。

所有失败 attempt 都必须保存，不能只报告最终成功 witness。

## 4.5 Counterfactual self-audit

每个可执行 witness 至少运行：

- **Full-Retrieval**：memory 正常存在并经过真实 retrieval/context 链；
- **Evicted**：目标 memory 及 Agent 可达的等价载体被封锁；
- **Restore-Normal**：恢复完全相同 item，并重新经过正常 retrieval。

风险证据要求：

\[
Y^{Full}\approx Y^{Restore}>Y^{Evicted}.
\]

severity 由确定性 event/state diff 映射，不能由同一 LLM 自行评分。

## 4.6 Diagnostic interventions

**Decoy-Control 必须用于：**

- 所有初步 positive；
- hard violation 或不可逆影响；
- 新 memory family；
- 删除引起明显 prompt 结构变化的案例。

**Full-Oracle 必须用于：**

- Full-Retrieval 失败；
- Restore 失败；
- retrieval trace 显示目标信息未进入 active context；
-多次运行高度不一致。

## 4.7 Risk-veto retention

当 witness audit 显示稳定、特异且可恢复的严重删除损失时，PREEMPT 对该候选发出 eviction veto。最终保留集合：

1. 优先包含已验证高风险候选；
2. 剩余容量沿用原 baseline 排名；
3. 为救回一个 memory，必须释放等量存储成本；
4. 若已验证硬风险的最低成本超过预算，报告 `RETENTION_INFEASIBLE`，不得静默降低风险权重。

首篇论文不加入历史风险头、三轨主动审计或 stress-CVaR 优化。

## 4.8 Generator-hidden transfer evaluation

每个 memory 在 witness 生成前冻结至少两个 hidden triggers：

1. **In-family transfer**：改变用户、数值、表述或局部工具路径；
2. **Compositional transfer**：改变状态组合、任务顺序或干扰条件。

评估必须同时报告：

- 全部生成 attempts；
- 全部 executable witnesses；
- self-audit positive witnesses；
- 各层级在 hidden triggers 上的 transfer。

否则仅报告筛选后样本会高估预测能力。

---

# 5. Experimental Setup

## 5.1 Stage A-S: semantic Mini-Pilot

样本：8–12 个 memory–future-task units。

目标：验证真正的语义通道，而不是取得论文主结果。

门禁：

- prompt 确实进入模型；
- `policy_id` 不参与行为选择；
- memory ID 置换不改变语义行为；
- 保持 ID 但遮蔽语义会改变行为；
- distractor 变化不触发目标动作；
- private leakage 为 0；
- Full/Restore 一致率不低于 90%；
- executable witness rate 不低于 70%；
- 至少两种非 credential memory family 出现语义性删除损失；
- hidden transfer 相对随机/直接风险判断出现方向性增量。

A-S 不估计 prevalence，也不支持最终系统 claim。

## 5.2 Main controlled track: AppWorld

AppWorld 被定位为：

> controlled/semi-synthetic executable causal benchmark。

新增 item-level memory adapter、retrieval trace、delete/restore、equivalent-carrier scan、state evaluator、manifest 和 replay。

### 样本形成

1. 从 source episodes 形成 60–80 个候选；
2. 在查看分支结果前冻结筛选规则；
3. 按可执行性、oracle 清晰度、来源、重复度和机制覆盖形成 40 个核心 memory units；
4. 候选过多时在分层内随机抽样；
5. 保存全部排除时间和原因。

### Memory families

| Family | 建议核心数量 |
|---|---:|
| Workflow prerequisite | 10 |
| Tool gotcha / exception handling | 10 |
| State update / dynamic state | 10 |
| Implicit constraint / permission | 10 |

每类同时包含 anticipated-critical 与 ordinary/noncritical 对照；人工平衡不能用于 prevalence claim。

## 5.3 Natural external-validity track

优先只使用 LongMemEval-V2，验证：

- 自然跨会话 memory 内容；
- 长间隔；
- 语义改写和干扰；
- Need/evidence mapping；
- witness 是否只对 AppWorld 模板有效。

自然辅轨不承担严重工具后果的主结论，也不与 AppWorld 合并估计 prevalence。LoCoMo 只在主轨稳定且时间允许时作为扩展。

## 5.4 Models

ICLR 目标最低要求：

- 至少两个不同模型家族；
- 固定版本、system prompt、tool schema 和 decoding config；
- 主结果使用 paired trials/seeds；
- API 不可完全确定时记录重复运行和不可控随机源。

## 5.5 Baselines

### Retention baselines

- LRU；
- LFU；
- embedding relevance；
- LLM importance；
- realized utility / learn-to-evict；
- decision-centric 强基线（接口兼容时）；
- Full-memory oracle。

### Risk-discovery baselines

- direct LLM importance；
- direct LLM deletion-risk score；
- fixed failure templates；
- random future scenario；
- witness generation without execution；
- self-witness validation without hidden transfer；
- hidden-risk oracle upper bound。

最关键比较是 PREEMPT 与能够读取完整 memory 内容的强 LLM risk baseline，而不是只与 LRU 比较。

## 5.6 Interventions and controls

所有分支固定：

- model/version；
- system prompt；
- future-task prompt；
- tool schema；
- tool-call budget；
- initial world state；
- retrieval parameters；
- seed/trial pairing；
- evaluator version。

effective eviction 必须覆盖：

- canonical store；
- ANN/keyword/graph index；
- retrieval/tool cache；
- active context；
- session summary；
- aliases/near-duplicates；
- derived rules/skills/plans；
- Agent 可访问日志和备份。

## 5.7 Metrics

### Primary

- hidden-trigger severe failure rate；
- witness-to-hidden transfer AUROC/AUPRC 或 rank correlation；
- rare-critical rescue recall；
- fixed-budget average utility；
- average utility–severe failure Pareto；
- false rescue/over-retention rate；
- storage and audit cost。

### Causal integrity

- Full/Restore consistency；
- Decoy false-positive rate；
- retrieval gap；
- effective-eviction pass rate；
- leakage rate；
- replay/evaluator stability。

### Secondary

- P90/P95 conditional loss；
- executable witness rate；
- failure-mode coverage；
- latency/token cost。

CVaR 只有在损失分布非退化且相对 severe-event/P95 产生独立信息时才进入附录。

## 5.8 Statistical protocol

- memory/failure-mode cluster 是主要统计单位；
- seeds、paraphrases 和多个 hidden tasks 不能伪装成独立 memory；
- 使用 memory-level paired bootstrap confidence intervals；
- 二元配对结果可使用 McNemar；
- 对不同 family/model 报告分层结果；
- 主假设、样本排除、重跑规则和阈值在主实验前冻结；
- 若 40 个 memory 的区间过宽，扩展独立 memory 数，而不是只增加重复 rollout。

---

# 6. Results

> 本节当前只规定结果结构。除 §6.1 的机制级证据外，其余均为 `PENDING`，不得提前写结论。

## 6.1 Existing mechanism evidence — `EVIDENCED, NARROW SCOPE`

第三步 A-R 已在冻结 trusted-worker、constructed deterministic selector-channel 范围内验证：

- Full/Evicted/Restore 外部 memory 干预可以隔离执行；
- target eviction、distractor preservation、cache/index cleanup 通过；
- Restore 能恢复数据库终态；
- 越权能力探针被拒绝；
- evaluator、manifest、hash 和运行证据可以复核。

三个 Smoke 案例结果：

| Case | Full | Evicted | Restore |
|---|---:|---:|---:|
| workflow | 8/8 | 2/8 | 8/8 |
| gotcha | 5/5 | 2/5 | 5/5 |
| constraint/permission | 10/10 | 2/10 | 10/10 |

但 prompt 在该 Smoke 中是 dead input，行为由 selector channel 驱动。因此这只能证明基础设施机制，不能证明语义 memory、rare-critical 现象或 PREEMPT 效果。

## 6.2 Does the retrospective blind spot exist? — `PENDING`

需要报告：

- held-out eligible Need rate；
- baseline eviction set 对 bottom-q memory 的覆盖；
- low-Need memory 的 hidden deletion loss；
- 不同 family 的正例数量和置信区间。

## 6.3 Do generated witnesses transfer? — `PENDING, CORE RESULT`

需要报告：

- self-witness validation rate；
- hidden-trigger prediction；
- 与 direct LLM risk、template、random 的比较；
- in-family 与 compositional transfer；
- false positive/false negative；
- witness selection funnel。

这是主结果表和主图的中心。

## 6.4 Does PREEMPT improve fixed-budget retention? — `PENDING`

需要报告：

- 不同 memory budget 下的 severe failure；
- 不同 audit budget 下的 rescue recall；
- average utility；
- Pareto frontier；
-跨 baseline 增量；
- storage/audit cost。

## 6.5 Generalization — `PENDING`

需要报告：

- model family；
- memory family；
- source type：natural/adapted/constructed；
- LongMemEval-V2 辅轨；
- 失败或反向结果。

---

# 7. Analysis and Ablations

只保留直接解释核心长板的分析：

## 7.1 Self-validation vs hidden transfer

证明仅在自生成场景上成功会高估方法，hidden transfer 提供更严格评价。

## 7.2 Witness generation strategy

- free generation；
- template；
- hybrid；
- no compiler。

## 7.3 Causal diagnostics

- no Restore gate；
- no equivalent-carrier blocking；
- Full-Retrieval vs Full-Oracle；
- Decoy positives；
- retrieval-limited information。

## 7.4 Transfer difficulty

- paraphrase/in-family；
- changed tool path；
- changed environment state；
- compositional trigger；
- distractor load。

## 7.5 Failure cases

至少区分：

- witness generation failure；
- compilation failure；
- retrieval failure；
- utilization failure；
- tool execution failure；
- evaluator failure；
- non-specific deletion effect；
- harmful or stale memory；
- valid self-witness but failed hidden transfer。

不加入风险头、三轨 acquisition 和 CVaR 的大规模消融。

---

# 8. Limitations and Broader Impact

## 8.1 Controlled and semi-synthetic evaluation

AppWorld 场景具有可执行性和程序化 oracle，但不代表真实部署分布。论文只声称受控 benchmark 中的存在性、可识别性和保留价值。

## 8.2 No natural prevalence claim

人工候选池和分层样本不能估计真实 Agent 中 rare-critical memory 的自然比例。

## 8.3 Oracle and environment dependence

PREEMPT 依赖可执行环境和可靠 consequence evaluator。开放世界任务中的风险可能难以程序化评价。

## 8.4 Generator bias

Generator 可能偏向显式安全词、熟悉 failure mode 或容易执行的任务。hidden transfer、negative controls 和 failure-mode coverage 只能缓解，不能彻底消除。

## 8.5 Retrieval versus retention

信息 critical 不代表保留即可解决。若 Full-Oracle 成功而 Full-Retrieval 失败，系统需要修复 retrieval、context routing 或使用 deterministic guard。

## 8.6 Safety boundary

受控 sandbox 中的严重后果模拟不构成真实生产安全认证。论文不鼓励对真实用户、财务、隐私或权限系统执行危险测试。

## 8.7 Compute and audit overhead

Counterfactual execution带来额外成本。论文必须公开平均每条候选的运行次数、token/tool成本和延迟。

---

# 9. Conclusion（当前结构稿）

Memory retention in long-horizon agents is typically driven by evidence from the past. PREEMPT-Mem explores a complementary principle: before forgetting a memory, test whether its absence could matter in the future. The method generates executable Future Decision Witnesses, validates deletion effects counterfactually, and uses the resulting risk to veto harmful evictions under a fixed budget. Its central evaluation asks not merely whether a generated test is self-consistent, but whether the observed risk transfers to future tasks hidden from the generator. **[PENDING：根据主实验填写最终结论、适用范围和失败边界。]**

---

# 10. Recommended Figures and Tables

## Figure 1：核心故事图

左侧：历史 importance 删除低频 memory，未来 rare trigger 导致严重失败。  
右侧：PREEMPT 在删除前生成 witness，counterfactual test 发现风险并否决删除。

## Figure 2：方法与泄漏边界

展示 baseline proposal、generator、compiler、self-audit、risk veto，以及对方法完全隐藏的 future-trigger evaluation。

## Figure 3：核心 transfer 图

横轴为 witness-derived risk，纵轴为 hidden-trigger deletion loss；比较 PREEMPT、direct risk、template 和 random。

## Figure 4：固定预算 Pareto

average utility 对 severe failure，分别绘制不同 memory/audit budgets 和 baselines。

## Table 1：变量与可见性

列出 Need、rarity、importance、witness、hidden trigger、criticality 哪些可被 generator、retention rule 和 evaluator 读取。

## Table 2：Related-work capability matrix

突出 pre-eviction generation 与 generator-hidden transfer 的组合差异。

## Table 3：主结果

跨模型、baseline 和 budget 的 hidden transfer、rescue recall、severe failure、average utility。

## Table 4：因果完整性与失败案例

Full/Restore、Decoy、retrieval gap、leakage、invalid witness 和 failure taxonomy。

---

# 11. Claim–Evidence Matrix

| Claim | 当前状态 | 需要的最低证据 | 失败后处理 |
|---|---|---|---|
| 外部 memory 可有效删除和恢复 | `EVIDENCED_NARROW` | A-S真实语义复验 | 不再扩大因果claim |
| low-Need/high-loss memory 存在 | `PENDING` | held-out rarity＋hidden deletion loss | 删除rare标题或重构问题 |
| 历史 baseline 会遗漏该子群 | `PENDING` | 多baseline eviction coverage | 收缩为一般prospective audit |
| witness风险迁移到hidden task | `PENDING_CORE` | 显著优于强LLM/template/random | 核心方法claim失败 |
| PREEMPT降低固定预算严重失败 | `PENDING_CORE` | 多budget、多模型、memory-level CI | 只能保留诊断协议 |
| 方法跨family/model泛化 | `PENDING` | 至少三类family、两个模型家族 | 明确收缩适用范围 |
| 自然内容上仍有效 | `PENDING` | LongMemEval-V2辅轨 | 限定为受控benchmark方法 |

---

# 12. ICLR Go/No-Go Gate

## 必须满足

1. A-S证明模型真正使用 prompt 和 memory content；
2. hidden triggers 在 generator 前冻结且零泄漏；
3. witness-to-hidden transfer 显著优于 direct LLM risk 和模板；
4. 至少三类 memory family 出现可复现信号，不能只有 credential/permission；
5. 固定双预算下 severe failure 明显下降；
6. 平均任务效用没有不可接受的下降；
7. 结果在至少两个模型家族上方向一致；
8. Full/Restore、Decoy、effective eviction、manifest 和 replay 门禁通过；
9. 提交前近邻文献复核未发现完整核心碰撞。

## 核心 No-Go

- 语义行为仍由 ID、selector 或 hard-coded lookup 决定；
- witness只在自身场景成立，对hidden trigger没有增量；
- 优势不超过直接LLM risk baseline；
- rare由人为采样权重制造；
- positive只存在于一个显式credential模板；
- severe failure下降仅来自保留更多memory；
- Restore或Decoy不能支持删除因果归因。

若第二或第三项失败，不得用风险头、三轨调度、五臂数量或CVaR复杂度包装成方法创新。

---

# 13. Recommended Main-Paper Space Allocation

以最终 ICLR Author Guidelines 的页数要求为准，正文篇幅比例建议：

| 部分 | 正文比例 |
|---|---:|
| Introduction | 12–15% |
| Related Work | 8–10% |
| Problem Setup | 10–12% |
| PREEMPT-Mem | 20–23% |
| Experimental Setup | 16–18% |
| Results | 20–25% |
| Analysis/Limitations/Conclusion | 10–14% |

优先把版面留给 Figure 3 的 hidden-transfer 结果和 Figure 4 的固定预算 Pareto。工程细节、完整 prompt、manifest、所有案例、额外统计和第二自然 benchmark 放入 Appendix。

---

# 14. Final Assessment

当前论文最有竞争力的版本不是一个覆盖所有 memory 管理问题的复杂系统，而是一篇具有明确科学问题的方法论文：

> **Can an agent discover the future cost of forgetting before that future occurs?**

已完成的 A-R 证明了狭义干预基础设施可行，但论文核心科学证据仍为空缺。决定 ICLR 竞争力的不是报告长度、运行次数或模块数量，而是以下连续证据是否成立：

```text
Retrospective blind spot exists
    → executable witness reveals prospective risk
    → risk transfers to generator-hidden future tasks
    → transferred risk improves retention under equal budgets
```

只要这条链足够强，Need、rarity、三臂、诊断臂和自然辅轨都会成为有力支撑。若 transfer 不成立，其他模块再完整也难以形成突出的 ICLR 长板。
