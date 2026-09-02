# PREEMPT-Mem 第二步结论修订附录

> 冻结日期：2026-08-27  
> 准入判决依据：`GO_3A_WITH_REQUIRED_REVISIONS`  
> 适用阶段：第三步 A——AppWorld 3-case Smoke 及其后续独立复核  
> 文件性质：对第二步结论的独立修订与证据边界冻结；**不覆盖、不修改**三份原始报告。

## 0. 修订效力与范围

本附录在第三步 A 及之后的协议、代码、日志和报告中具有以下约束效力：

1. 若本附录与第二步报告的宽泛表述冲突，以本附录的更窄结论为准；
2. 本附录不重选题，不改变 PREEMPT-Mem、Agent Memory 方向或 AppWorld 主轨；
3. 本附录不授权 30–50/40-memory Pilot、rarity/prevalence 估计、FMEA 优越性比较、模型训练或大规模实验；
4. 第三步 A 只允许回答：是否能在 AppWorld 上实现可审计、无泄漏、可恢复的三分支方向性 deletion-effect smoke；
5. 所有第三步 A 案例只能标记为 `adapted` 或 `constructed/semi-synthetic`，不得标记为 `natural`。

---

## 1. 七项强近邻冻结矩阵

符号：`Y`=直接覆盖；`P`=部分/邻近覆盖；`N`=未覆盖。矩阵只用于冻结边界，不把任何单项的缺失自动解释为 PREEMPT-Mem 的 novelty。

八个组合要素缩写：

- `UT`：unseen trigger；
- `CS`：candidate-specific；
- `EW`：executable Future Decision Witness；
- `IE`：item-level effective eviction；
- `FE`：Full–Evicted paired primary effect；
- `RC`：Restore recovery control；
- `CL`：conditional severe loss；
- `DB`：memory/testing dual budgets。

| 强近邻 | 一手入口与已冻结范围 | UT | CS | EW | IE | FE | RC | CL | DB | 对 PREEMPT-Mem 的约束性结论 |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **OSL-MR** / *Learning What to Remember: Observability-Safe Memory Retention via Constrained Optimization for Long-Horizon Language Agents* | [arXiv:2606.10616](https://arxiv.org/abs/2606.10616)；未知未来 evidence demand、硬 storage budget、延迟 miss/reacquisition/staleness 成本和顺序 retention | Y | P | N | P | N | N | N | P | 未知未来需求、prospective retention、硬 memory budget 均不是单组件 novelty；剩余差异必须落在 candidate-specific executable deletion-risk witness、Restore、conditional severity 和 testing budget |
| **Causal Memory Intervention** | [arXiv:2605.17641](https://arxiv.org/abs/2605.17641)；[作者仓库](https://github.com/Saksham4796/causal-memory-intervention)；当前 query 下逐条 no/with/perturbed memory 因果选择 | N | Y | N | P | P | N | N | N | “对单条 external memory 做 causal intervention/selection”不是 novelty；PREEMPT 必须坚持 trigger 尚未出现和可执行 future task consequence |
| **MEMAUDIT package-oracle** | [arXiv:2605.02199](https://arxiv.org/abs/2605.02199)；固定 future-query requirements、candidate packages、cost、budget 与 exact/MILP oracle 的写入审计 | Y | P | N | N | N | N | N | P | “未知未来 query 下的预算 memory writing/retention”不是 novelty；package-oracle 不等同 executable item deletion effect |
| **Proactive Memory Agent** | [arXiv:2607.08716](https://arxiv.org/abs/2607.08716)；[作者官方仓库](https://github.com/yifannnwu/proactive-memory-agent)；Terminal-Bench 2.0/τ²-Bench 工具循环中的主动 memory bank 与 reminder 注入 | P | P | P | N | N | N | N | N | “主动维护记忆”“主动让记忆影响决策”“真实工具循环”均不是 novelty；PREEMPT 的对象是 pre-trigger deletion-risk validation 与 retention |
| **PREPING** | [arXiv:2605.13880](https://arxiv.org/abs/2605.13880)；目标任务前 proposer 生成 synthetic practice，solver 执行、validator 过滤并形成 procedural memory，包含 AppWorld | Y | P | Y | N | N | N | N | N | “任务前生成可执行 practice/test”“在 AppWorld 做 pre-task generation”不是 novelty；必须限定 witness 针对一个候选 external item，并验证删除效应而非构建 procedural skill |
| **ASSAY / Not All Skills Help** | [arXiv:2606.15390](https://arxiv.org/abs/2606.15390)；小 dev set 中随机 mask skill、估计 per-skill causal attribution、离线修复库，并在 AppWorld/τ-bench 做任务特异 masking；论文列出的仓库在复核日不可访问 | N | Y | N | Y | P | N | P | N | “AppWorld 上 item/skill masking、因果异质性、任务特异筛选”不是 novelty；ASSAY 是第三步 A 最强实现邻近之一，必须用 item 类型、unseen witness、Restore 与双预算区分 |
| **When Retrieval Fails Before It Begins** | [arXiv:2608.20400](https://arxiv.org/abs/2608.20400)；[复现仓库](https://github.com/smkgenesis/dsgc)；固定 prompt budget 下 prerequisite 在 retrieval 前被错误淘汰，强调依赖/组效应与相似度代理失败 | P | P | N | P | N | N | N | P | “retrieval 前的 prerequisite eviction failure”“frequency/similarity 非真实价值”“依赖组效应”不是 novelty；remove-one 主张必须限于 item-level marginal effect |

### 1.1 碰撞判决冻结

纳入上述七项后，当前仍未发现一项已核验工作同时覆盖本附录第 3 节的全部八个要素。因此：

- 当前没有足以要求重选题的完整核心碰撞；
- 这不是“绝对首次”或穷尽性查新结论；
- 任一单组件、两个组件或删去关键限定后的子组合都不得宣称原创；
- 后续 novelty 结论只能写成“截至当前可核验的一手证据，完整八要素组合仍未见统一覆盖”。

---

## 2. `What Eviction Destroys` 的证据状态冻结

`What Eviction Destroys` 固定标记为：

```text
evidence_status: U
verification_status: unverified lead
allowed_use: future retrieval lead only
forbidden_use:
  - novelty support
  - Restore precedent
  - item-level deletion precedent
  - no-collision conclusion
  - method motivation evidence
```

原因：截至 2026-08-27，OpenReview forum、PDF 与 API 均只返回 challenge 页面；未取得可核验正文、作者列表、发表/投稿状态或官方源码。无法核验不证明文献不存在，但在取得一手材料前，它不进入任何决定性证据链。

第三步 A 的设计、判决和日志均不得引用该线索来解释 Restore 或 deletion effect。

---

## 3. 唯一安全 novelty：八要素完整组合

唯一允许冻结的 novelty 表述为：

> **在真实 trigger 尚未出现时，针对每个候选 external memory item 生成候选特异、可执行且可证伪的 Future Decision Witness；随后在相同 future-task checkpoint 上实施可审计的 item-level effective eviction，以 Full–Evicted 配对估计主要 deletion effect，并仅用 Restore 作为 recovery/symmetry control；以确实需要该 memory 的 future task 为条件测量 severe loss，最终在 memory budget 与 witness/testing budget 双重约束下决定 retention。**

该表述必须完整保留以下八项，缺一即不再视为安全 novelty：

1. `unseen trigger`；
2. `candidate-specific`；
3. `executable Future Decision Witness`；
4. `item-level effective eviction`；
5. `Full–Evicted paired primary effect`；
6. `Restore recovery control`；
7. `conditional severe loss`；
8. `memory/testing dual budgets`。

### 3.1 禁止的单组件首创主张

本项目不主张以下任一单项或宽泛组合为首次：

- rare/rare-but-important/rare-critical 现象；
- 未知未来需求或 future utility；
- prospective retention；
- proactive memory intervention/reminder；
- pre-task synthetic practice；
- memory/skill masking、causal intervention 或 remove-one；
- executable agent memory evaluation；
- effective eviction、Full/Evicted 或 Restore；
- conditional loss/severity；
- memory budget 或 testing budget；
- FMEA、failure-mode analysis 或 generic risk triage；
- 在 AppWorld 上进行 memory/skill 选择或因果评估。

---

## 4. 研究对象、干预语义与 FMEA 边界

### 4.1 研究对象冻结

PREEMPT-Mem 的主研究对象固定为：

> **非参数化、显式、具有稳定唯一 ID、可寻址、可记录 provenance、可单条删除与恢复的 external episodic/semantic memory。**

不属于第三步 A 主对象：参数记忆、KV cache、纯 active-context token、隐式 recurrent state、procedural skill/code artifact。active prompt/session/KV context 只作为必须清空和审计的暴露面，不是第二个主要 memory 对象。

### 4.2 Full/Evicted/Restore 因果角色冻结

- `Full−Evicted`：唯一主要 deletion effect；
- `Restore`：只验证恢复、对称性、缓存清理和状态漂移；
- Restore 只能恢复被删除的同一个 item、同一个 ID、原始内容、metadata、provenance 和索引成员关系；
- Restore 不得增加上下文、替换更强 prompt、恢复其他 items 或改变工具/模型；
- Restore 不被描述为“降低随机性”，随机性由相同 checkpoint、相同 seed/参数和重复执行控制。

### 4.3 FMEA 冻结

- FMEA 只允许作为可选的 Prospective Risk Triage schema；
- FMEA 不是核心模块、不是 novelty、不是第三步 A 通过条件；
- 禁止传统 `RPN = Severity × Occurrence × Detectability`；
- occurrence 不进入 criticality 真值，也不能压低 rare/high-severity candidate；
- 后续 Pilot 除 severity-only、random 等基线外，必须增加 **generic risk triage**：使用相同 agent-visible inputs，让通用 LLM 直接输出风险类别/严重度/不确定性，但不使用 FMEA 字段或术语；
- 第三步 A 不比较 FMEA、generic risk triage 或其他 triage 的优越性。

---

## 5. AppWorld 第三步 A 的证据类型与允许结论

第三步 A 的唯一允许定位为：

```text
adapted + constructed/semi-synthetic mechanism smoke
```

原因：AppWorld 官方 task-specific DB、checkpoint/revert 和 state-based evaluator 能支持可重复的分支机制验证，但官方 benchmark 不自动提供同一用户的有序跨任务 lifecycle，也不保证 source task A 的历史 memory 是 target task B 的自然必要信息。source→target dependency 必须由本项目显式桥接。

第三步 A 允许声称：

- 在明确适配/构造的三个案例上，AppWorld 接口能否支持同 checkpoint 三分支；
- external item 能否真正 effective-evict 并原样 Restore；
- state evaluator 能否稳定检测方向性 deletion effect；
- 泄漏面是否可以逐项审计。

第三步 A 禁止声称：

- natural cross-task lifecycle；
- 自然用户/Agent 任务流；
- 真实部署频率或外部有效性；
- rare-critical memory 的自然存在率；
- PREEMPT-Mem 的总体性能、优越性或论文主结果。

---

## 6. Rarity 与 prevalence 的统计用途冻结

### 6.1 三案例 Smoke

三个 workflow/gotcha/constraint 案例是有目的的机制测试，不能定义或估计：

- rarity；
- rare-critical prevalence；
- AppWorld 中任何 memory 类型的自然频率；
- 真实 Agent lifecycle 的发生率。

本阶段每个案例只冻结 `Need(m,target)` 的二元、案例特异依赖，用于判断 target 是否应依赖该 memory；它不是 frequency estimator。

### 6.2 未来 80/40 设计

- 未来未平衡 80 候选池只有在 eligible stream、抽样框、纳入概率和无 outcome selection 全部预注册时，才能估计**该构造抽样框内**的比例；仍不得外推为自然 AppWorld prevalence；
- 未来平衡 40 条分析集属于 case-control/stress set，只能用于方法比较和效应异质性；
- `10/40`、`25%` 或任何由四象限配额直接得到的比例不得作为 prevalence；
- 在进入 40-case Pilot 前必须另行冻结任务分布、分母、阈值、时间窗、中频灰区和 invalid-triplet 处理。本轮不执行。

---

## 7. 第三步 A generator/evaluator 防火墙

第三步 A 的每个案例必须满足：

1. target task、`Need(m,target)`、gold state tests、severity rubric 在 witness 进入 retention 决策前冻结并记录 hash；
2. witness generator 只可见候选 item、允许的 source history 和公开 AppWorld API/environment schema；
3. generator 不可见 target instruction、target task ID、gold tests、Need label、severity label、target final state 和 Evicted 结果；
4. generator 不得修改 target DB、evaluator、severity rubric 或 hidden manifest；
5. evaluator success 只由冻结的 state/tool assertions 决定，不使用 witness 文本、生成器自评、LLM 相似度或 rationale；
6. 若为了可执行 smoke 需要把人工预设 witness 固定为 protocol fixture，必须标为 `constructed protocol witness`，不得冒充模型自主发现；
7. 所有可见/不可见字段、prompt、模型、解码参数、seed、版本和 hash 写入第三步 A 协议 manifest。

---

## 8. 3A 前置修订准入核对

| ID | 第三份报告要求的前置修订 | 本附录落点 | 状态 |
|---|---|---|---|
| R1 | 冻结七项强近邻矩阵与碰撞边界 | §1 | **PASS** |
| R2 | `What Eviction Destroys` 标为 U，不进入核心证据链 | §2 | **PASS** |
| R3 | 冻结八要素完整组合 novelty，不主张单组件首创 | §3 | **PASS** |
| R4 | AppWorld 3A 重标为 adapted + constructed/semi-synthetic | §5 | **PASS** |
| R5 | 每个 case 冻结 source→target dependency | §7 已冻结强制字段；具体三案例将在第三步 A Manifest 中逐案实例化 | **PASS / INSTANCE REQUIRED BEFORE RUN** |
| R6 | 三分支与 effective-eviction manifest 逐项冻结 | §4.2；完整泄漏面将在第三步 A Manifest 中实例化 | **PASS / INSTANCE REQUIRED BEFORE RUN** |
| R7 | generator/evaluator 防火墙 | §7 | **PASS** |
| R8 | 限定 smoke 结论，不估 rarity/prevalence/FMEA 优越性 | §5、§6 | **PASS** |

附加边界：

- external addressable episodic/semantic memory 已在 §4.1 固定；
- FMEA 可选、不用 RPN、generic risk triage 基线已在 §4.3 固定；
- 三案例与平衡 40 不可估 prevalence 已在 §6 固定。

**前置修订门控结论：八项要求均已落地为规范；R5/R6 的案例实例字段必须在运行 Smoke 前写入 `PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest.md`。在该 Manifest 完成并通过静态核对前，不得运行三分支。**

