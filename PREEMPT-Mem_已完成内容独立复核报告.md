# PREEMPT-Mem 已完成内容独立复核报告

**复核日期：** 2026-08-27  
**复核对象：** `PREEMPT-Mem_第一步_文献调查与概念梳理.md`、`preempt可行性报告_v1.1.md`、`论文完整story_v1.1.md`  
**参照但未执行：** `ICLR2027-PREEMPT-Mem_新项目续研指令_v1.2.md`  
**复核边界：** 本报告只审查已完成内容；没有修改三份原报告，没有执行第二阶段续研，没有实现代码、下载大规模数据、运行实验或重新寻找论文 Idea。

## 证据标记与复核方法

本文使用以下证据标记：

- **[P] 论文正文直接支持**：正式 proceedings、OpenReview 论文或官方 arXiv 正文；
- **[C] 官方源码/数据页直接支持**：由论文指向或作者组织维护的仓库、数据页；
- **[S] 多篇一手文献综合推断**：不是任何单篇论文的原句；
- **[R] 当前报告推测**：三份待审报告中的判断，尚未被独立证实；
- **[E] 尚待实验验证**：必须由源码审计、数据审计、标注或 Pilot 才能确定。

对三份原报告在写入本报告前记录的 SHA-256 如下；文末复查结果相同：

| 原报告 | SHA-256 |
|---|---|
| `PREEMPT-Mem_第一步_文献调查与概念梳理.md` | `517FC984751DE57D0133EE974B690D4AF9593C05AB19554BCE9A5D513F234EC1` |
| `preempt可行性报告_v1.1.md` | `1563E3DCEC382BC9493F538135689D667E1A888241717E4C15D536714DC36A48` |
| `论文完整story_v1.1.md` | `944F247A9F1855935314CEC26300CD02A36DFC352FF52906566D90DD653D11C6` |

---

## 1. 执行结论与审查等级（不超过一页）

### 总等级：**PASS WITH REVISIONS**

截至本次复核，**PREEMPT-Mem 的研究问题、外部可寻址 memory 范围和 pre-trigger counterfactual retention 的核心组合仍然成立，没有发现覆盖完整组合的核心碰撞**。[S] 但“仍然成立”只适用于以下收窄后的组合：

> **在部署时未知的未来触发分布下，主动构造独立且可执行的 Future Decision Witness；对可寻址外部 memory 做成对的有效移除干预，估计遗忘的条件性严重后果；再在 memory budget 与 testing budget 双重约束下保护有益 memory。**

不能继续把 rare-important、future utility、主动 memory、预算化 eviction、decision loss、item-level counterfactual、Full/Evicted/Restore 或 FMEA 中的任何单点写成 novelty。它们都已有强近邻。[P][S]

本轮发现三份报告没有纳入四篇会显著改变宽泛定位的强近邻：

1. [OSL-MR](https://arxiv.org/html/2606.10616) 已把未知未来需求、延迟 miss/reacquisition/staleness 后果、部分可观测性和硬预算写成顺序 retention 问题；
2. [Causal Memory Intervention](https://arxiv.org/html/2605.17641) 已在外部 memory 上逐条比较 no-memory / with-memory / perturbed-memory，并在当前 query 下按因果效用选择；
3. [MemAudit package-oracle](https://arxiv.org/html/2605.02199) 已审计未来 query requirements 下的预算化 memory writing；
4. [Proactive Memory Agent](https://arxiv.org/html/2607.08716) 已在 Terminal-Bench 2.0 与 τ²-Bench 的真实工具循环中主动维护 memory 并选择何时注入提醒，且有[官方仓库](https://github.com/yifannnwu/proactive-memory-agent)。

这些工作**不覆盖** PREEMPT-Mem 的完整组合：OSL-MR 和 package-oracle MemAudit 没有严重工具后果和主动 witness；Causal Memory Intervention 使用已出现的当前 query，主要是回答级选择；Proactive Memory Agent 没有逐条删除反事实、rare × conditional severity 目标或 retention/testing 双预算。[P][S] 因而它们造成的是 **Claim 收窄**，不是 **核心碰撞**。

三份报告的可靠性并不相同：

- 第一份文献调查对证据边界、术语区分和未决问题的表述总体可靠，可以作为继续工作的基础；
- 可行性报告 v1.1 和 Story v1.1 在未完成源码/数据审计、定义冻结和 Pilot 的情况下，把若干“候选空白”升级成了较确定的 feasibility 与 contribution；这需要在进入 Pilot 前纠正；
- “公开资源提供了足以尝试拼装各组件的候选基础”可以保留；“数据问题已经解决”“没有公司日志不是核心障碍”目前只能算可行性假设。[C][S][E]

范围选择合理：主对象应保留为**非参数化、显式、可寻址的外部 episodic/semantic memory**；active context 是读取/暴露层和扩展对照，不应在主 claim 中悄然变成第二个主要删除对象；procedural memory 暂缓是合理的。[S]

`effective eviction` 可以化解“永久删除”与 Restore 的表面冲突，但必须定义为：**在正常 agent 接口、检索索引、缓存和当前上下文中均不可达，仅实验控制面保留不可见审计副本**。Restore 是可逆性/对称性控制，不是独立的主要因果估计，也不能单独“减少随机性”。[S][E]

FMEA 的当前降级定位合理：**保留为可选 triage 设计来源，不是核心模块或 novelty**。传统 `RPN = Severity × Occurrence × Detection` 会把低 occurrence 的高 severity 项压低；现代 FMEA 实务也已使用强调 severity 的 Action Priority 来弥补这一缺陷。[P] PREEMPT-Mem 不应默认采用传统乘积 RPN。

**进入 Pilot 前的硬性修正：**补入上述强近邻并重写 novelty；冻结可测的 rarity/criticality 定义与非循环阈值；把 Full/Evicted/Restore 改写为成对干预加恢复控制；完成 benchmark 组件级可接入性审计；把“数据已解决”和四项贡献改回假设/计划状态。

---

## 2. 核心 claims 逐项核验表

| # | 核心 claim | 独立核验证据与判断 | 结论 | 分类 | 推荐动作 |
|---:|---|---|---|---|---|
| 1 | Agent memory 在有限预算下必须选择保留/淘汰 | Memory-R1、AgeMem、TraceRetain、CURATOR、OSL-MR 均直接研究有限 memory/context 下的管理或保留。[P] | 成立 | 已确认优势 | 保留，但区分 storage、retrieval 和 active-context budget。 |
| 2 | “低频但重要”现象已被文献识别 | [Agent Memory survey](https://arxiv.org/html/2512.13564) 明确指出 LRU 可能淘汰少访问但必要知识；TraceRetain 也直接讨论 rare-but-important。[P] | 现象被识别；普遍性/规模未证实 | 已确认优势 + 缺失证据 | 只能写“recognized concern”，不能写成已证明的大规模自然分布规律。 |
| 3 | 现有方法主要只看历史/当前信号 | TraceRetain、Learning What to Remember 等多用历史特征或已给 query；但 OSL-MR 明确建模未知未来需求和延迟后果，MemAudit 固定未来 query requirements，Proactive Memory Agent 主动干预。[P] | 宽泛表述不成立 | Claim 收窄 | 改为：尚未发现同时主动生成未知 trigger witness、执行 item-level deletion 并做尾部 retention 的工作。 |
| 4 | rarity 应等于真实 future need probability | 真实部署未来不可观测；只能在预先冻结的 held-out trigger 分布上估计，或用在线可观测代理。[P][S] | 作为概念量可用，作为直接测量定义不可用 | Claim 收窄 | 明确 estimand、样本空间、分母、时间窗和阈值；部署估计与离线真值分开。 |
| 5 | low retrieval 可代表 rare | retrieval 还受召回器、query、索引和 exposure 影响；外部-memory survey 也指出检索会失败。[P][S] | 不能作为真值 | 缺失证据 | 仅作带偏代理；至少与 held-out need incidence、retrieval opportunity 和 retriever recall 分解。 |
| 6 | criticality 是忘记后的条件损失，与 rarity 解耦 | 该区分在风险语义上合理；Governance Decay 展示移除约束后的严重工具行为，MemAudit 展示 remove-one 后 harm 变化。[P][S] | 概念成立；操作定义待冻结 | 已确认优势 + 缺失证据 | severity rubric 先于 rarity 阈值冻结，避免用同一 witness 同时定义 rare 与 critical。 |
| 7 | 必须先证明 rare-but-critical memory 存在 | 作为问题存在性与非平凡性检查合理；不需要先证明现实世界普遍性。[S] | 成立，但原证明标准需适中 | Claim 收窄 | Pilot 证明“可信分布中有非单例、可复现、基线易删且删除损失较高”的案例即可。 |
| 8 | 外部 episodic/semantic memory 是最佳主对象 | 可寻址 ID、稳定干预面和可恢复控制使其最适合 item-level 因果实验；CMI/MemAudit 也在外部 memory 面实施干预。[P][S] | 成立 | 已确认优势 | 主实验锁定外部 memory；active context 只作为读取层/扩展对照。 |
| 9 | effective eviction 解决 deletion/Restore 矛盾 | 若 normal plane 完全不可达、audit plane 仅用于实验恢复，则科学上等效于删除；不等于合规或物理删除。[S] | 有条件成立 | 已确认优势 + 工程风险 | 明确访问边界、索引/缓存清理、上下文泄漏检查和审计副本权限。 |
| 10 | Full/Evicted/Restore 提供反事实监督并降低随机性 | Full−Evicted 是主要成对效应；Restore 检验可逆性、对称性和状态漂移。Restore 本身不降低模型/环境随机性。[S][E] | 机制可行，因果角色表述不准确 | Claim 收窄 + 工程风险 | 配对 seeds、环境快照、顺序随机化/交叉设计、重复运行；Restore 作为控制。 |
| 11 | “公开数据足以支撑研究” | LongMemEval-V2、LoCoMo、LongMemEval 等提供 memory/QA；ConstraintRot 提供严重工具行为；但未发现单一公开资源同时提供自然 memory、独立未来 trigger、可重置执行环境、严重结果 evaluator。[P][C][S] | 仅为可行性假设 | 缺失证据 + 工程风险 | 在源码与许可审计、组件拼装和小样本 Pilot 后再确认。 |
| 12 | 没有公司日志不是核心障碍 | 公共资源可能足够做论文级受控验证，但不能由现有页面证明能覆盖自然频率或部署外推。[C][S][E] | 过早确定 | Claim 收窄 | 改为“公司日志并非启动受控研究的必要条件；外部有效性仍受限”。 |
| 13 | FMEA 可作为 prospective triage，但不是 novelty | ASQ 对 FMEA 的定义支持其前瞻风险枚举/优先级用途；传统 RPN 对罕见高严重项不友好，且没有证据表明 FMEA 为本任务提供不可替代能力。[P][S] | 当前定位合理 | 已确认优势 | 保留为可选实现与 ablation，不使用“首次用于 Agent”式 claim。 |
| 14 | 完整核心组合具有剩余 novelty | 已核验近邻分别覆盖 future retention、主动干预、逐条因果选择、严重执行后果或预算，但未发现一项同时覆盖 unseen trigger generation、可执行删除干预、rare×conditional-severity 和预算化保护。[P][S] | 暂时成立，不是最终查新证明 | 已确认优势 + 缺失证据 | 使用收窄句式并在投稿前持续查新；不能写“首次”或“没有任何工作”。 |

---

## 3. 关键文献真实性、发表状态与引用适配性

### 3.1 指令点名文献

| 文献 | 真实题目、作者与状态 | 正文/官方资源核验 | 对报告引用的适配性 | 结论 |
|---|---|---|---|---|
| Agent Memory 综述 | [Memory in the Age of AI Agents: A Survey: Forms, Functions and Dynamics](https://arxiv.org/html/2512.13564)，Tobias Weiß 等，arXiv v2，2026-01 | 正文直接讨论按时间、频率、重要性遗忘，并指出少访问但必要知识可能被启发式淘汰。[P] | 支持“问题被识别”和术语脉络；不能单独证明自然数据中的发生率或损失分布。 | **真实；引用基本适配，证据强度需注明为 survey synthesis。** |
| Agent Memory 综述 | [Rethinking Memory Mechanisms of Foundation Agents in the Second Half: A Survey](https://arxiv.org/html/2602.06052v3)，arXiv 2026 | 正文区分独立于参数更新的 external memory，讨论可编辑性与检索失败。[P] | 适合支持 external/internal 范围和“低 retrieval 不等于低需求”。 | **真实；适配。** |
| TraceRetain | [Selective Memory Retention for Long-Horizon LLM Agents](https://arxiv.org/html/2606.29178)，Pranath Reddy，arXiv v1，2026-06-28；[OpenReview PDF](https://openreview.net/pdf?id=9JiPHfleLn) 标示 ICML 2026 CATS workshop |  bounded external memory；按 success、age、access frequency、redundancy、specificity、similarity、downstream utility 评分并真实淘汰；ALFWorld noisy-write 压测包含 synthetic rare-but-important。[P] 未在论文页定位官方代码。 | 报告对方法描述基本准确。它证明预算保留和 rare-important 压测不是新点，但没有主动 unseen witness、逐条 remove/restore 或条件严重度。 | **真实；workshop/arXiv 状态必须准确标注。** |
| Learning What to Remember | [Learning What to Remember: A Cognitively Grounded Multi-Factor Value Model for Agentic Memory](https://arxiv.org/html/2606.12945)，Zhibao Chen、Qian Cheng，arXiv v2，2026-06 | 七因素模型；真实 LongMemEval-S 无 API 实验中 value alignment、task utility、usage history 三项恒为 0，主要指标是固定 keep budget 下 gold-evidence retention；[官方仓库](https://github.com/zhibao-dev/Learning-Multi-Factor-Memory) 为 MIT 并含实验结果。[P][C] | 第一份报告“真实设置只激活 4/7 因素、以 gold evidence 为代理”的描述准确。不能把其 retention 指标等同可执行 Agent 后果。 | **真实；引用适配。** |
| CURATOR | [Forget to Improve: On-Device LLM-Agent Continual Learning via Budget-Curated Memory](https://arxiv.org/html/2606.25115)，Beining Wu、Zihao Ding、Jun Huang、Yanxiao Zhao，arXiv 预印本，2026-06 | 以 net value per byte 管 KEEP/SHARE/TRUST；value 含 recent-query retrieval propensity、加入检索集的 expected marginal utility 与 abstraction gain；执行预算淘汰。[P] 未在论文页定位官方代码。 | 报告把它描述为 value/byte 与 current/recent query 近邻，基本准确。它已覆盖 budgeted eviction 与预测/边际 utility，故这些不能单独声称 novelty。 | **真实；引用适配。** |
| DeMem | [Remember the Decision, Not the Description: A Rate-Distortion Framework for Agent Memory](https://arxiv.org/html/2605.10870)，Mingxi Zou 等，arXiv v1，2026-05-11 | decision-centric rate-distortion；把压缩质量定义为可实现 decision quality 损失；在 history-query pair/已观察 decision conflict 上精炼 runtime slots，并以有/无候选 slot 的回答重跑评分。[P] | “以 downstream decision loss 定义压缩质量”准确；但对象是 runtime slot/状态抽象，不等于 external item persistent deletion，也不是未知未来 witness。 | **真实；需补清对象差异。** |
| What Eviction Destroys | 报告给出 OpenReview ID `8rOh73WoJh` 和标题 *What Eviction Destroys* | 2026-08-27 对论坛/PDF/API 的直接访问均触发 OpenReview challenge；精确标题检索未得到稳定的一手元数据。下载到的所谓 PDF 实为 challenge HTML。 | 本轮无法独立确认题目、作者、状态和方法；这不证明文献不存在，但它不能承担关键 novelty 证据。 | **未核实。必须取得原 PDF/元数据后再引用，并准确标注匿名/在审状态。** |
| Governance Decay / ConstraintRot | [Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents](https://arxiv.org/html/2606.22528)，Shiyang Chen，arXiv 预印本，2026-06-21 | ConstraintRot 比较 full/compacted/absent/pinned，使用确定性 tool-call grading；完整上下文违规率为 0，压缩后约 30%，部分设置达 59%；移除/恢复 policy 支持 policy-loss 机制。[P] 未定位官方仓库。 | 适合证明“忘记约束可能造成严重可执行行为”和 Full/absent 类对照先例；对象是 active context compaction、已知 policy 与给定 trigger，不是外部 memory retention。 | **真实；引用适配，但公开数据/代码可用性未证实。** |
| MemAudit（poisoned memory） | [MemAudit: Post-hoc Auditing of Poisoned Agent Memory via Causal Attribution and Structural Anomaly Detection](https://arxiv.org/html/2605.23723)，Zhewen Tan 等，arXiv 预印本，2026-05-22 | 重放已发生 harmful event，逐一移除候选 memory，比较 harm reduction，再删除可疑 memory；RAP 含真实工具行为。论文开放性附录明确未公开 data/code。[P] | 第一份报告把它作为 post-hoc remove-one 最近邻是准确的。它已覆盖 item-level causal intervention，但方向是事后删除有害 memory，不是 pre-trigger 保护有益 memory。 | **真实；不可写成有官方复用代码。** |
| Memory-R1 | [Memory-R1: Enhancing Large Language Model Agents to Manage and Utilize Memories via Reinforcement Learning](https://aclanthology.org/2026.acl-long.583/)，Sikuan Yan 等，ACL 2026 Long Paper | Memory Manager 学 ADD/UPDATE/DELETE/NOOP，Answer Agent 预选并推理；PPO/GRPO；152 个训练 QA，LoCoMo/MSC/LongMemEval。[P] | 支持“显式 memory 操作可学习”；不支持 pre-trigger causal claim。 | **真实；正式 ACL 2026，报告状态应按 proceedings 标注。** |
| AgeMem | [Agentic Memory: Learning Unified Long-Term and Short-Term Memory Management for Large Language Model Agents](https://aclanthology.org/2026.acl-long.981/)，Yi Yu 等，ACL 2026 Long Paper | 把 store/retrieve/update/summarize/discard 暴露为工具动作，统一 LTM/STM，三阶段 RL 与 step-wise GRPO。[P] | 报告对其“统一操作与 RL”描述准确；它不做 item-level pre-trigger witness。 | **真实；正式 ACL 2026。** |
| Xiong 等实证研究 | [How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior](https://aclanthology.org/2026.acl-long.27/)，Xiong 等，ACL 2026 Long Paper | 官方摘要明确研究 memory addition/deletion，并用 future-task evaluation 作为已存 memory 的免费质量标签。[P] | 支持“future task labels 可训练管理”；报告中更细的周期/历史规则未在本轮源码层复核，不宜扩写。 | **真实；高层引用适配。** |
| LongMemEval-V2 | [LongMemEval-V2](https://arxiv.org/html/2605.12493)，Di Wu 等，arXiv v1，2026-05-12；[官方仓库](https://github.com/xiaowu0162/LongMemEval-V2)，Apache-2.0 | 451 个手工整理问题，history 最长 500 trajectories / 115M tokens；轨迹来自 synthetic sandbox web/enterprise traces。接口是插入 trajectory、对 question 返回 compact evidence，再由固定 reader QA；仓库含 data/evaluation/memory modules。[P][C] | 适合自然化外部 memory 候选池、证据支持和规模压力；不提供环境回放、独立未来 trigger 或严重工具结果。报告把它称为自然 trajectory 时必须加“synthetic sandbox-derived”。 | **真实；数据存在，但不能单独闭合 PREEMPT-Mem。** |

### 3.2 本轮新发现、会改变 novelty 边界的强近邻

| 文献 | 一手核验 | 与 PREEMPT-Mem 的实质关系 | 影响分类 |
|---|---|---|---|
| [Learning What to Remember: Observability-Safe Memory Retention via Constrained Optimization for Long-Horizon Language Agents](https://arxiv.org/html/2606.10616)（Kang 等，OSL-MR，arXiv v6，2026-06-29） | 硬 storage budget；未知未来 evidence demand；延迟 miss/reacquisition/stale penalties；online/OAS 分离；在 LoCoMo/LongMemEval 做顺序保留。实验仍是 evidence retention/QA，tool-agent 扩展列为 future work；正文未给出官方代码链接。[P] | 已覆盖“未知未来需求下的预算 retention”与顺序后果，直接否定宽泛的“现有 retention 只看过去/当前”和“prospective retention 本身新”。未覆盖主动 witness、rare×severity 或可执行删除后果。 | **高优先级 Claim 收窄。** |
| [Causal Intervention-Based Memory Selection for Long-Horizon LLM Agents](https://arxiv.org/html/2605.17641)（Saksham Sahai Srivastava，arXiv，2026-05-17；[官方仓库](https://github.com/Saksham4796/causal-memory-intervention)） | 对每条候选比较 no-memory / with-memory / perturbed-memory，按当前 LoCoMo query 的 deterministic scorer 选择，约束 memory 数量；Causal-LoCoMo 有 useful/irrelevant/synthetic harmful memories。[P][C] | 已覆盖 external-memory item intervention、因果 utility 与预算选择。未覆盖未出现 trigger、环境工具后果、恢复控制或保留 rare beneficial item。 | **高优先级 Claim 收窄。** |
| [MemAudit: An Exact Package-Oracle Evaluation Protocol for Budgeted Long-Term LLM Memory Writing](https://arxiv.org/html/2605.02199)（Bhargava、Barrento，arXiv，2026-05-04；另检得[同名公开 artifact](https://huggingface.co/datasets/edgeclustr/memaudit-code)，但作者归属未独立闭环） | 固定 experience stream、candidate representations、cost、semantic evidence units、future-query requirements 和 budget；用 exact/MILP oracle 评估写入。自然切片是 model-adjudicated，主目标是 semantic coverage，不是 runtime product 或严重 Agent 行为。[P] | 已覆盖“未来 query requirements 下预算化写入审计”，进一步压缩 future-value/预算 novelty；未覆盖主动生成未知 witness 和可执行尾部损失。 | **高优先级 Claim 收窄；artifact provenance 待核。** |
| [Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents](https://arxiv.org/html/2607.08716)（Yifan Wu 等，Meta AI，arXiv v1，2026-07-09；[官方代码](https://github.com/yifannnwu/proactive-memory-agent)，Apache-2.0） | 独立 memory agent 每隔若干步维护 structured bank，决定注入 memory-grounded reminder 或沉默；在 Terminal-Bench 2.0 和 τ²-Bench 中执行工具行为。可 update/delete bank entry，但没有 storage budget、逐条 deletion counterfactual 或 rare-tail severity 目标。[P][C] | 已覆盖“proactive memory intervention”和 executable agent loop。PREEMPT-Mem 不能把主动记忆/未来行动保护本身称为首创，必须落到 deletion-risk witness 和双预算保留。 | **高优先级 Claim 收窄。** |

### 3.3 发表状态与源码审查总判断

1. 三份报告中的多数核心文献真实存在，方法转述总体没有凭空捏造；第一份报告的证据纪律明显最好。
2. Memory-R1、AgeMem、Xiong 等是正式 ACL 2026 论文；TraceRetain 是 workshop/arXiv；其余多为 2026 arXiv 预印本，不能统称正式 conference paper。
3. 已直接核验的官方实现包括 Learning multi-factor、LongMemEval-V2、Causal Memory Intervention、Proactive Memory Agent；MemAudit（poisoned）论文明确未开放 data/code。未找到代码不等于证明不存在，但不得写成已审计或可复用。
4. `What Eviction Destroys` 在本轮无法取得一手正文，是引用链中的唯一重大真实性未闭环项。

---

## 4. 最强近邻统一比较

符号：`是` 表示正文直接覆盖；`部分` 表示只有相邻版本；`否` 表示未覆盖；`未知` 表示本轮无法获取一手正文。

| 工作 | Trigger 时点 | 证据来源 | 单条 memory remove/restore | 真实 Agent/工具执行 | 目标语义 | 时间方向/用途 | memory / testing budget |
|---|---|---|---|---|---|---|---|
| **PREEMPT-Mem 目标组合** | 真实 trigger 尚未出现；从冻结的未来分布采样/生成 | 主动 Future Decision Witness + 执行结果 | **有效移除；Restore 控制** | **是** | **条件性严重遗忘损失，显式 rare×critical** | **pre-trigger 保护有益 memory 并实际 retention** | **双预算** |
| OSL-MR | 当前 query 可见，未来 evidence demand 未知 | 历史日志、在线特征、离线 realized evidence | 淘汰 cache；无 remove/restore 因果实验 | 否，LoCoMo/LongMemEval evidence/QA | 累积 evidence utility、miss/reacquisition/stale cost | 未来需求下顺序 retention | 硬 storage budget；无 testing budget |
| Proactive Memory Agent | live trajectory 当前阶段已知 | 近期轨迹 + structured execution state | 可管理/delete，但无逐条反事实/Restore | **是**，Terminal-Bench/τ²-Bench | pass@1 与 intervention utility | 在线主动提醒；不是 deletion-risk audit | 无明确 storage/testing budget |
| Causal Memory Intervention | **当前 query 已出现** | no/with/perturbed memory 下回答 scorer | 单条 with/no/perturbed；无 Restore | 否，LoCoMo QA | 当前回答因果效用与抗 harmful memory | 当前选择有益 memory、排除有害项 | 选择数量预算；干预成本未成主问题 |
| MemAudit package-oracle | future-query requirements 已冻结为 benchmark label | evidence-unit coverage 与 exact oracle | 否；比较写入 package | 否 | semantic coverage / package-opt ratio | 写入时预算审计 | storage budget；无执行测试预算 |
| MemAudit poisoned | harmful event 已发生 | 重放该事件的 remove-one harm reduction | **remove-one；恢复/重放是控制的一部分但非 retention** | 部分；RAP 有工具行为 | 已观察 harm 的因果归因 | 事后删除有害 memory | 无保护性 memory budget |
| Governance Decay | policy 与触发任务预设、已知 | full/compacted/absent/pinned context | context/policy 条件，不是外部 item retention | **是**，确定性 tool-call grader | policy violation / severe behavior | 诊断 compaction 后治理衰减 | 无 memory/testing 双预算 |
| DeMem | history-query pair 或 decision conflict 已出现 | 有/无 runtime slot 的 answerer/scorer | slot counterfactual；无外部 item Restore | 主要为回答/决策 scorer | decision quality rate-distortion | 当前/已观察冲突下压缩 | runtime slot budget；无 testing budget |
| CURATOR | 当前与近期 query 分布 | propensity、marginal utility、abstraction gain | 实际 eviction；无逐条执行 counterfactual | 否/非核心 | average utility per byte | 当前分布下保留/分享/信任 | **memory budget**；无 testing budget |
| TraceRetain | 当前任务 | 历史 success/age/access/redundancy 等 | 实际 eviction；无 remove/restore | **是**，ALFWorld | 平均任务效用与 noisy-write robustness | 在线预算保留 | **memory capacity**；无 testing budget |
| Learning multi-factor | 当前评测 question 已知 | gold evidence + 4 个实际活跃因素 | keep/drop label，无执行反事实 | 否 | evidence retention | query-conditioned retention | keep budget；无 testing budget |
| What Eviction Destroys | 未知 | 未知 | 未知 | 未知 | 未知 | 未知 | 未知 |

### Novelty 判决

- **可以安全保留的一句 novelty：**  
  “To the best of our verified evidence, PREEMPT-Mem studies a still-unified gap: before a deployment trigger is observed, it actively constructs independent executable witnesses, estimates the conditional severe effect of effectively evicting an addressable external memory item, and uses the result for retention under both memory and counterfactual-testing budgets.”

- **必须收窄的一句 novelty：**  
  原先“从 retrospective utility 转向 prospective forgetting risk”过宽；OSL-MR 已建模未知未来需求与延迟 eviction cost，Proactive Memory Agent 已主动干预，CMI 已做逐条 causal selection。应改成“从一般未来 utility/主动提醒/当前-query 因果选择，收窄到未知 trigger 的主动可执行 deletion-risk witness 与 rare-tail retention”。

- **是否发现核心碰撞：** **没有。** 已核验文献覆盖多个单点和子组合，但没有发现一项覆盖 `unseen trigger + active witness generation + executable item-level eviction intervention + rare×conditional-severity + actual budgeted retention/testing` 的完整组合。[S] `What Eviction Destroys` 尚未核实，因此这一结论必须表述为“截至本次可核验证据”，不能写成绝对首次。

---

## 5. rare、critical、importance 与 effective eviction 定义审查

### 5.1 可以保留的定义

| 概念 | 可保留的操作性含义 | 证据属性 |
|---|---|---|
| **rarity** | 对**预先定义且与待测 item 不同源构造**的 held-out trigger/task 分布，估计 memory item 被完成任务所必需的事件发生率；rare 是该发生率低于预先冻结阈值，而不是历史检索次数低。 | [S][E] |
| **criticality / severity** | 在 trigger 确实需要该 item 的条件下，effective eviction 相对 Full 引起的后果损失；应基于预先冻结的 outcome rubric（如不可逆工具错误、policy violation、任务失败等级），与 occurrence 分开。 | [P][S][E] |
| **importance** | 上位概念或系统内部 heuristic，可包含 relevance、salience、observed utility、LLM rating 等；不得与 causal forgetting loss、rarity 或 severity 互换。 | [S] |
| **observed downstream utility** | 在已发生 query/task 上有/无 memory 的性能差；它是历史/当前证据，不等于对未知未来的 criticality。 | [P][S] |
| **effective eviction** | 在正常 agent 数据面上，item 从主存、检索索引、候选集、缓存及 active context 全部不可达；仅隔离的实验控制面保存不可见审计副本以便 Restore。 | [S][E] |

离线评测可用一个简单的、但不是最终理论的估计框架：对冻结的 held-out triggers (z_1,\ldots,z_N)，用“完成 (z_j) 是否需要 memory (m)”估计 need incidence；仅在 need 条件成立的样本上估计 `loss(Evicted) - loss(Full)`。阈值、严重度量表和 trigger 构造规则必须在看测试结果前冻结。

### 5.2 必须修正的定义或用法

1. **“真实 future need probability”不可作为直接可观测定义。** 它只能是 estimand；离线用 held-out distribution 估计，在线用不含未来标签的模型/统计代理预测。
2. **历史 retrieval frequency 不能定义 rarity。** 低 retrieval 可能是 retriever failure、query 不匹配、index 缺陷或 item 从未获得 exposure；必须至少记录 retrieval opportunity 与 recall。
3. **event base rate 与 future-need rate 不等价。** 某事件可能常见但只在少数状态需要该 memory，或事件罕见却多条 memory 均可替代。报告应指定分母是 tasks、event families、episodes 还是 time windows。
4. **token surprisal 不是任务 rarity。** 它可作为文本统计特征，不能作为 rare-critical 的真值。
5. **criticality 必须与 occurrence 解耦。** 不使用 `expected loss = probability × severity` 作为 critical 的定义；该乘积会重新压低 rare-high-severity 项。
6. **避免循环定义。** 不得先让同一 LLM 生成“会证明该 memory 关键”的 witness，再用该 witness 同时定义 need、rarity 和 criticality。需要独立 trigger pool、人工/规则审核、隐藏评测或 cross-generator/cross-judge 设计。
7. **交互与冗余不能被单条 remove-one 完全覆盖。** 多条 memory 互为替代时单条效应接近 0；互补时单条效应依赖其他项。主张应限于 item-level marginal effect，并把 group intervention 列为扩展。

### 5.3 “先证明 rare-but-critical memory”是否合理

合理，但证明标准应是**问题在可信研究分布中非平凡且可重复**，不是先证明整个现实世界的普遍规律。进入方法大规模比较前，30–50 个审计单元的 Pilot 至少应显示：

- 不止一个手工构造孤例；
- baseline 在冻结预算下确实倾向淘汰其中一部分；
- effective eviction 相对 Full 有可重复的较大条件损失，且 Restore 能恢复；
- 结果不依赖同一个生成器/评判器的自证循环；
- 报告置信区间、失败/无效 witness 比例和成本，而不是只展示成功案例。

这足以证明问题值得继续；对自然发生率与部署外推仍需后续证据。

---

## 6. 外部 memory 范围与 Full/Evicted/Restore 可行性

### 6.1 范围判决

| 对象 | 在 PREEMPT-Mem 中的建议位置 | 理由 |
|---|---|---|
| 显式、可寻址 external episodic memory | **主对象** | 有稳定 item ID、可单条干预、易做成对对照，直接对应经历/事件。 |
| 显式、可寻址 external semantic memory | **主对象** | 与 episodic 同样可干预，但需记录其来源与合并关系，防止一条 semantic item 隐含多条证据。 |
| active context | **读取/暴露层 + 扩展对照** | Full/Evicted 必须保证它同步清除，但不能把 context compaction 与 persistent retention 混成同一主问题。Governance Decay 可作为 transfer benchmark。 |
| procedural memory / skills | **首轮暂缓** | 其行为影响可能分散在代码、policy、参数或工具配置中，单条删除和 Restore 难以解释。Proactive Memory Agent 也说明 procedural state 是重要扩展，但不必首轮承担。 |
| 参数内/隐式 memory | **排除** | 没有稳定 item 地址，干预面与归因完全不同。 |
| 物理/合规删除 | **明确不声称** | audit copy 与 Restore 与不可恢复、法务意义的删除不相容；本研究只谈实验上的 effective unavailability。 |

因此，第一份报告“external persistent memory 为主、active context 为邻近对照”的范围选择应明确确认。可行性报告与 Story 中“外部 store 或 active state”式并列表述会扩大研究对象，应收回。

### 6.2 Full/Evicted/Restore 的因果角色

| 条件 | 正确角色 | 不能声称的角色 |
|---|---|---|
| **Full** | 未移除 item 的参考状态；与 Evicted 在相同环境快照、模型、工具版本和随机种子下配对。 | 不是自然部署的绝对真值；可能仍有 retrieval/reader failure。 |
| **Evicted** | 正常数据面完全不可达的处理状态；`Evicted − Full` 是主要 deletion effect。 | 只在 vector DB 中打标但仍存在缓存/上下文，不算有效干预。 |
| **Restore** | 把完全相同的 item、索引与元数据恢复；验证可逆性、干预对称性、缓存清理和环境漂移。 | 不是独立的主要因果估计；也不会自动减少 LLM 或工具随机性。 |

Restore 如果与 Full 是相同状态，在没有顺序控制时确实可能概念冗余；它的价值来自检测**顺序漂移、不可逆副作用和实现错误**。合适的最小协议应是：

1. 为每个 witness 固定环境 snapshot、agent/tool/model 版本、prompt 和 seed；
2. Full 与 Evicted 成对执行，随机化或交叉安排顺序；
3. 清空 retriever cache、reranker cache、context、tool state 和 derived summaries；
4. Restore 原 item 的内容、ID、embedding/index membership、metadata 和 provenance；
5. 重复执行并报告 stochastic variance；若环境不可重置，则该样本不得进入主要因果估计；
6. 记录 retrieval exposure：Full 条件若 item 从未被取回，观测到的是系统级 total effect，但不能进一步归因为 reader 使用；
7. 另设“检索成功但 reader 忽略”诊断，避免把 retention、retrieval 和 utilization 全部混为 deletion failure。

### 6.3 工程可行性判断

在研究 wrapper、tombstone/ACL filter、可重置 sandbox 和独立 audit store 中实现清晰的 effective eviction 是**技术上可行**的。[S][E] 但真实系统需要稳定 ID、派生 summary/graph edge 的依赖追踪、缓存失效、环境快照和 provenance；这些尚未通过源码审计。因此正确结论是“有明确实现路径，仍有中等工程风险”，不是“已经实现可行”。

---

## 7. 数据与 benchmark 可行性主张审查

### 7.1 四项所需能力不能由单一已核验 benchmark 同时提供

| 资源 | 自然/自然化 memory 来源 | 独立未知 future trigger | 可重置可执行 Agent 环境 | severe-outcome evaluator | 官方可用性结论 |
|---|---|---|---|---|---|
| [LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2) | **部分**：synthetic sandbox web/enterprise trajectories，规模大、较自然化 | 否：固定 question；memory query 接口已看到问题 | 否：返回 evidence 给 reader，不重放环境 | 否：主要 QA/证据使用；部分判分为 LLM judge | 代码/数据仓库可访问，Apache-2.0；是 memory-source 候选，不是完整环境。 |
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | 部分：合成长对话，500 questions | 否：固定 QA | 否 | 否 | 官方仓库与数据存在；适合 QA/evidence retention。 |
| [LoCoMo](https://github.com/snap-research/LoCoMo) / [ACL 2024](https://aclanthology.org/2024.acl-long.747/) | 部分：event graph/persona 生成、人工验证的长对话 | 否：固定 QA/summary tasks | 否 | 否 | 官方仓库存在；适合 conversation memory，不是工具环境。 |
| [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench) / [数据页](https://huggingface.co/datasets/ai-hyz/MemoryAgentBench) | 部分：增量长程 memory tasks | 否：评测任务已给定 | 主要否：QA/分类/总结/冲突解析 | 否 | ICLR 2026；官方仓库 MIT。当前仓库任务命名含 Conflict Resolution，不能从旧描述推断 persistent deletion。 |
| [ConstraintRot / Governance Decay](https://arxiv.org/html/2606.22528) | 否：预设 governance constraints 位于 active context | 否：trigger/policy 是 benchmark 设计的一部分 | **是/部分**：确定性 tool-call grading | **是**：policy violation | 论文可访问；本轮未定位官方代码/数据仓库，可接入性未知。 |
| TraceRetain + ALFWorld | synthetic memory 写入与 trajectory summary | 否：当前 ALFWorld task | **是** | 否：主要成功率，不是 rare severe taxonomy | 论文可访问；官方实现未定位。 |
| Terminal-Bench 2.0 / τ²-Bench（经 Proactive Memory Agent） | 运行中 execution state，可作为 memory 来源 | 部分：后续行动随轨迹展开，但不是独立生成的 held-out witness | **是** | 部分：binary task verifier / domain evaluator，不天然是 conditional severity | Proactive Memory 官方代码表明可集成；仍需逐项许可、任务重置与 item provenance 审计。 |

### 7.2 对两项可行性主张的判决

**“公开数据足以支撑研究”**：

- 若含义是“公开资源已经提供全部数据和执行闭环”，则**不成立**。
- 若含义是“公开资源分别提供 memory source、固定问题、可执行环境和严重行为先例，足以启动组件审计与小规模拼装 Pilot”，则**有希望但尚待验证**。[C][S][E]

**“没有公司第一手日志不是核心障碍”**：

- 对“能否启动一篇受控学术研究”而言，可能成立；LongMemEval-V2、LoCoMo 等可形成受控 memory pool，Terminal-Bench/τ²-Bench/ConstraintRot 提供执行侧候选。
- 对“是否自然存在、频率如何、是否可泛化到生产系统”而言，不成立；公开 synthetic/sandbox 数据不能替代真实部署分布。
- 推荐表述：**“公司日志不是启动受控验证的必要条件，但公共资源能否支持闭环以及结论的外部有效性尚未由源码审计和 Pilot 证实。”**

### 7.3 评分修正

`preempt可行性报告_v1.1.md` 中“数据 7/10、方法 8/10”只能保留为作者的主观先验，不能作为审计结论。当前更可信的文字评级是：

- **数据资源存在性：中高**；
- **单一 benchmark 适配度：低**；
- **多组件集成可行性：中等、未验证**；
- **可重置因果执行：中等工程风险**；
- **自然分布/外部有效性：高不确定性**。

---

## 8. FMEA 当前定位审查

### 建议：**保留当前定位**

[ASQ 的 FMEA 概览](https://asq.org/quality-resources/fmea) 将 FMEA 定义为在失败发生前识别 failure mode、effects，并按后果严重度、发生频率和可检测性排序的通用风险分析工具。[P] 这支持把它作为 Prospective Risk Triage 的设计来源，但不支持“首次把 FMEA 用于 Agent”或 FMEA 本身构成技术 novelty。

传统 `RPN = S × O × D` 的确与 rare × high-severity 目标存在结构冲突：低 O 会压低高 S 项。[ASQ 2026 practical guide](https://careers.asq.org/career-resources/on-the-job-3/fmea-failure-mode-and-effects-analysis-for-quality-engineer-2026-107) 也指出，传统 RPN 会隐藏 high-severity/low-occurrence 风险，AIAG-VDA 2019 的 Action Priority 改用查表并提高 severity 权重。[P]

因此：

1. 不把 occurrence 乘入 criticality 真值；
2. 若借鉴 FMEA，仅保留 failure mode / effect / detection-cost 等结构化提示；
3. 可比较 severity-first、generic LLM risk triage、FMEA-inspired triage 与无 triage；
4. 只有 ablation 显示独特收益时，FMEA-inspired 设计才进入方法细节；否则继续降为 prompt/schema 实现选择；
5. 不恢复为核心模块，也不必从叙事中完全删除。

FMEA 没有提供 generic risk triage 明显不具备的独特技术能力；它的价值是**审计结构和工程语言**，不是理论或 novelty。

---

## 9. 三份报告的内部矛盾或不一致

| # | 对应文件与章节 | 原主张/不一致 | 核验证据与问题级别 | 统一修正 |
|---:|---|---|---|---|
| 1 | 文献调查 §1.1、§9；可行性报告 §5、最终判断 | 第一份明确“未系统审源码/数据、定义未定”，后者写“数据问题可以解决”“没有公司日志不是核心障碍”。 | 官方资源只分散覆盖四个组件；**高：Claim 收窄/缺失证据**。 | 恢复为“候选资源足以开始审计；闭环可行性待 Pilot”。 |
| 2 | 文献调查 §6；可行性报告 §4；Story Step 2/4 | 第一份主对象为 external persistent memory；后两份把 external store 与 loaded active state 并列。 | Governance Decay 说明 context 是另一干预面；**高：范围漂移**。 | active context 只作为读取层和 transfer 对照，主 claim 锁定外部可寻址 item。 |
| 3 | 文献调查 §1.3 的 persistent deletion；可行性报告/Story 的 effective eviction + Restore | 前者说未来通常不能恢复，后者保留 audit copy 并 Restore。 | 实验可恢复与永久删除语义不同；**中：措辞冲突**。 | 全文主术语改为 effective unavailability/eviction；明确不声称物理或合规删除。 |
| 4 | 可行性报告 §6；Story Step 4 | Restore 被写成减少随机性、增强因果估计。 | Restore 只验证可逆性/漂移；随机性靠配对与重复控制；**高：因果角色错误**。 | 主估计为配对 `Evicted−Full`；Restore 为 symmetry/recovery control。 |
| 5 | 文献调查 §4、§9；可行性报告 §1；Story 第二幕 | 第一份把 rarity 分母/阈值列为未决，后两份近似把 future need probability 写成定义。 | 真实未来不可观测；**高：定义过早冻结**。 | 概念 estimand 与 held-out estimator 分开；阈值预注册。 |
| 6 | Story 第三幕、Contribution 1；可行性报告 §2 | “现有方法主要依据过去/当前证据”“从 retrospective 到 prospective”写得过宽。 | OSL-MR、MemAudit package-oracle、Proactive Memory Agent 直接构成反例；**高：遗漏近邻/Claim 收窄**。 | 只声称主动构造未知 trigger 的 executable deletion-risk witness。 |
| 7 | 文献调查 §7；Story §三 | 第一份近邻表较完整且谨慎；Story 表省略 CURATOR、Learning、TraceRetain、DeMem、MemAudit，以及本轮四个新近邻。 | 统一比较会改变 novelty；**高：近邻遗漏**。 | 用本报告 §4 的维度重建表，不以选择性邻居制造空白。 |
| 8 | Story Contribution 3 与 4 | “Selective Prospective Risk Testing”与“低成本 triage + 高可信验证 + retention”高度重叠。 | 两者都对应 testing-cost gate；**中：贡献重复**。 | 合并为一个 efficiency contribution；在无实验前称 method design，不称已证贡献。 |
| 9 | 可行性报告 §7；Story §二、§四 | 计划达到的优越性被列成贡献/最关键图，语气接近已经证明。 | 尚无 Pilot/实验；**中：待验证写成预期事实**。 | 分开“hypothesized contribution”“evaluation plan”“supported contribution”。 |
| 10 | 三份报告的 FMEA 段落 | 第一份倾向风险框架，后两份已降为候选；地位基本一致但 Story 仍占较大篇幅。 | RPN 并不适合 rare-high severity；**低/中：叙事权重**。 | 保留候选实现，Spotlight 不突出 FMEA；无 ablation 前不列贡献。 |
| 11 | 文献调查 §5.2 与后两份 | “需要自然案例”容易被理解为必须先证明生产世界普遍性。 | 研究前置只需可信分布中的非平凡可重复性；**中：证明标准表述**。 | 将“自然”改为“自然化或可信、来源可追溯、非循环构造”，另报外部有效性限制。 |
| 12 | 三份报告对 `What Eviction Destroys` 的使用 | 将其作为可比较近邻，但未给可稳定核验的一手正文。 | 本轮无法核验；**高：引用真实性未闭环**。 | 在取得 PDF 前标为 unverified，不用于 novelty 结论。 |

### 合理的 Story 简化，不必删除

- “An agent should not have to suffer a rare failure before learning what it must remember.” 是合格的动机句；它不是操作定义，但在注明 rare/critical 需离线量化后可以保留。
- “past access is not future necessity” 是合理叙事压缩；它不应扩张为“所有 prior work 都只看 past access”。
- “把删除从压缩问题改写为风险测试问题”可保留为论文视角，但要承认 DeMem、CMI、MemAudit 已使用 decision/counterfactual 视角；新点在 pre-trigger executable witness 与 retention 闭环。
- `Remember Before It Matters` 与方法名 PREEMPT-Mem 可以保留；标题本身不构成 novelty claim。

---

## 10. 已确认、可以继续保留的优势

1. **问题真实且及时。** 多篇 survey、TraceRetain、OSL-MR 和 Governance Decay 共同表明有限 memory 会遗失少访问但必要信息，遗忘可能延迟显现并影响工具行为。[P][S]
2. **rare 与 critical 分离是正确的概念纪律。** 发生率与条件后果不应被混成平均 utility；这使尾部问题可被明确审计。[S]
3. **外部可寻址 episodic/semantic memory 是正确的首轮范围。** 它提供稳定干预面、可逆控制和 provenance，避免一开始陷入参数 memory 或 procedural skill 的归因困难。[S]
4. **effective eviction 是可用的实验语义。** 在清楚限定 normal plane/audit plane 后，它兼顾真实不可达与 Restore 控制；只需避免称为永久/合规删除。[S][E]
5. **Future Decision Witness + executable intervention 是最强的剩余组合。** 已核验近邻通常只覆盖未来价值、当前 query、主动提醒、逐条回答干预或事后 harm replay 中的一部分。[P][S]
6. **双预算视角有意义。** 不仅 memory 容量有限，反事实测试也昂贵；选择性测试与 retention 联合考虑仍是可保留的 method design。[S][E]
7. **FMEA 已被正确降级。** 不把跨领域框架包装成首创，降低了不必要的 novelty 风险。[P][S]
8. **第一份报告的术语边界值得继承。** 它清楚区分 retrieval filtering、context eviction、compression 与 persistent deletion，并把未完成部分列为问题而非结论。[R]
9. **核心 Story 可解释性强。** “不应先遭受失败才学会记忆”能准确传达 pre-trigger protection 的目的，只需让技术定义和近邻边界在正文中跟上。

---

## 11. 按严重级别排序的问题清单

本轮没有“核心碰撞”级问题。

### 高优先级：进入 Pilot 前必须修正

| ID | 问题 | 文件/章节 | 分类 | 推荐修正 |
|---|---|---|---|---|
| H1 | 遗漏 OSL-MR、Causal Memory Intervention、MemAudit package-oracle、Proactive Memory Agent 四个强近邻 | 可行性报告 §2；Story 第三幕、§三 | Claim 收窄 / 缺失证据 | 加入统一矩阵，重写 Contribution 1 和 novelty 句。 |
| H2 | 把 prospective retention、主动 memory、causal selection 等单点暗示为新 | 可行性报告 §2、§7；Story Contribution 1–2 | Claim 收窄 | 只保留完整组合 novelty，逐项承认先例。 |
| H3 | 数据与无公司日志结论过于确定 | 可行性报告 §5、最终判断 | 缺失证据 / 工程风险 | 改为组件拼装假设；完成源码、许可、重置、evaluator 审计后再评级。 |
| H4 | rarity 定义依赖不可观测真实未来，分母/阈值未冻结 | 三份报告 rare/critical 段落 | Claim 收窄 / 缺失证据 | 明确 held-out trigger distribution、estimator、阈值、时间窗与独立性。 |
| H5 | Full/Evicted/Restore 因果角色与随机性说法不准确 | 可行性报告 §6；Story Step 4 | Claim 收窄 / 工程风险 | 配对 Full−Evicted 为主效应；Restore 为 recovery/symmetry control；加 snapshot/seeds/repeats。 |
| H6 | external memory 与 active context 范围漂移 | 可行性报告 §4；Story Step 2/4 | Claim 收窄 | 主对象锁定 external addressable item；context 仅暴露层与 transfer。 |
| H7 | `What Eviction Destroys` 无法一手核验 | 三份报告近邻/引用段 | 措辞/引用问题 | 取得 PDF、作者、日期、状态；此前不用于核心结论。 |

### 中优先级：方法冻结前修正

| ID | 问题 | 分类 | 推荐修正 |
|---|---|---|---|
| M1 | 同一生成器可能生成并验证 witness，形成自证循环 | 工程风险 / 缺失证据 | 独立 trigger pool、cross-model/cross-judge、规则/人工 audit、隐藏集。 |
| M2 | remove-one 忽略 memory 冗余与交互 | Claim 收窄 | 首轮明确估计 marginal item effect；记录替代/互补，后续加 group intervention。 |
| M3 | Contribution 3 与 4 重复 | Story/结构问题 | 合并为“testing-cost-aware selective validation and retention”。 |
| M4 | 把计划结果写成贡献/预期优越性 | 措辞问题 | 无实验前使用“hypothesis/design/evaluation target”。 |
| M5 | LongMemEval-V2 被称为自然轨迹而未注明 synthetic sandbox-derived | 措辞/引用问题 | 精确注明来源；不外推为生产日志。 |
| M6 | effective eviction 未列缓存、derived summary、graph edge 和 context 的污染路径 | 工程风险 | 制定 intervention integrity checklist。 |
| M7 | severe outcome 仍可能由 LLM judge 主导 | 工程风险 | 优先 deterministic tool/state checker；LLM judge 仅辅助并做一致性审计。 |

### 低优先级：写作与报告卫生

- 把正式 proceedings、workshop、arXiv 和匿名稿统一写成“论文”的地方应逐项标注状态。
- 数字化可行性评分应注明主观先验，不要伪装成测量结果。
- Spotlight 中保留简洁叙事，但把限定条件放在摘要/引言贡献句中。
- “rare-but-critical memory”应统一写清是 memory item 在 task distribution 下的属性，不是文本自身永恒属性。

---

## 12. 建议修改的具体句子或 claims（不直接修改原文件）

| 文件与章节 | 原主张/原意 | 建议替换文本 |
|---|---|---|
| `PREEMPT-Mem_第一步_文献调查与概念梳理.md` §5.2 | “尚未发现同时满足六个条件的工作” | “截至 2026-08-27 本次可核验的一手证据，尚未发现同时覆盖未知 trigger 的主动 witness 生成、可执行 item-level effective eviction、条件严重度与实际预算化保护的工作；OSL-MR、Causal Memory Intervention、MemAudit package-oracle 和 Proactive Memory Agent 分别覆盖其中若干子问题。” |
| 同文件 §5.3 | “必须先证明 rare-but-critical memory 自然存在” | “在方法比较前，应先证明其在来源可追溯、非循环构造的可信研究分布中非平凡且可重复；这不等同于已证明生产世界的普遍发生率。” |
| 同文件 §6/术语 | “persistent deletion” | “主干预采用 effective eviction：item 在正常 agent 数据面不可达，审计副本仅供隔离控制面 Restore；本文不声称物理或合规删除。” |
| `preempt可行性报告_v1.1.md` §2 | “真正 novelty 是从过去效用转向未来遗忘风险” | “未来效用和顺序 retention 已有 OSL-MR、CURATOR、MemAudit 等近邻；PREEMPT-Mem 的候选 novelty 是在真实 trigger 未出现时主动构造独立可执行 witness，测量外部 item 被有效移除后的条件严重损失，并把该信号用于双预算 retention。” |
| 同文件 §4 | “研究外部 store 及其 loaded active state” | “主研究对象限定为显式、可寻址 external episodic/semantic memory；active context 仅作为该 memory 的暴露层与 transfer/control setting。” |
| 同文件 §5 标题 | “数据问题可以解决” | “公开资源提供了可拼装的候选组件，但闭环数据与环境可行性仍待源码审计和 Pilot。” |
| 同文件 §5 | “因此，没有公司第一手日志不是核心障碍。” | “公司日志并非启动受控验证的必要条件；但公共 synthetic/sandbox 资源能否闭合 memory–trigger–execution–severity 链条，以及结论的外部有效性，尚待验证。” |
| 同文件 §6 | “Full/Evicted/Restore 降低随机性并提供反事实估计” | “配对的 Full−Evicted 比较提供主要系统级 deletion effect；Restore 用于验证可逆性、干预对称性与状态漂移。随机性由环境快照、固定/配对 seeds、顺序控制和重复运行处理。” |
| 同文件 §7 | “可以形成的论文贡献” | “以下是待 Pilot 支持的 hypothesized contributions；在完成问题存在性、因果完整性和成本收益实验前，不视为已证贡献。” |
| `论文完整story_v1.1.md` 第三幕 | “现有 retention policy 主要依赖过去或当前证据” | “现有工作已从历史启发式扩展到未来需求建模、主动提醒和当前-query 因果选择，但仍缺少在 trigger 未出现时主动生成可执行 deletion-risk witness 并直接保护 rare high-severity memory 的统一闭环。” |
| 同文件 Step 4 | “Restore 减少随机性/执行漂移” | “Restore 是 recovery/symmetry control，用于检测不可逆副作用、缓存污染和顺序漂移；它不替代 Full−Evicted 主比较，也不自动降低随机性。” |
| 同文件 Contribution 1 | “从 retrospective utility 转向 prospective forgetting-risk” | “从一般 future utility/active intervention 收窄到 pre-trigger executable forgetting-risk：在未知 trigger 前生成独立 witness，并测量 effective eviction 的条件严重后果。” |
| 同文件 Contribution 2 | “Pre-trigger Counterfactual Supervision” | “保留该标题，但正文明确区别于 CMI 的 current-query answer intervention、MemAudit 的 post-hoc harm replay、Governance Decay 的已知 policy/context 条件，以及 OSL-MR 的 evidence-level delayed cost。” |
| 同文件 Contribution 3/4 | 两项分别强调 selective testing 与低成本闭环 | 合并为一项：“Testing-cost-aware selective validation and retention：低成本 triage 只决定哪些 item 值得执行昂贵 witness；验证结果在独立触发集上用于预算保留。” |
| 同文件 §三近邻表 | 只列少量近邻 | 用本报告 §4 的统一维度重建，至少加入 OSL-MR、Proactive Memory Agent、Causal Memory Intervention、MemAudit package-oracle、CURATOR、TraceRetain、DeMem、MemAudit、Governance Decay。 |
| 三份报告引用 | 将 `What Eviction Destroys` 当作已核验近邻 | “该 OpenReview 条目在本轮无法取得一手正文，暂列 unverified，不作为 novelty 判决的决定性证据。” |

---

## 13. 第二阶段续研计划是否足以覆盖这些问题

### 总判断：**覆盖大部分问题方向，但按当前文本还不足以保证闭环；需小幅增补后再执行。**

`ICLR2027-PREEMPT-Mem_新项目续研指令_v1.2.md` 已正确承认：候选数据只被识别、源码没有系统核验、rare/critical 定义和阈值未定，并安排了来源审计、数据审计、定义、Pilot 和 FMEA 评估。这与本报告的主要缺口高度一致，说明 v1.2 的方向是可靠的。[R]

| 本报告问题 | v1.2 覆盖度 | 还需补充 |
|---|---|---|
| 文献真实性与源码/数据审计 | 高 | 把 OSL-MR、CMI、package-oracle MemAudit、Proactive Memory Agent 列为必审；单独闭环 `What Eviction Destroys`。 |
| rare/critical 定义 | 高 | 加入 trigger 分布独立性、非循环阈值、retrieval opportunity/recall 分解和 group interaction 记录。 |
| benchmark 拼装 | 中高 | 增加“四组件能力矩阵”、许可/下载/运行入口、环境 reset、deterministic evaluator、stable item ID 的 go/no-go gate。 |
| Full/Evicted/Restore | 中 | 明确 Full−Evicted 主效应、Restore 控制、快照/seeds/顺序/缓存清理和 retrieval exposure 诊断。 |
| novelty 与 Story 收窄 | 中 | 在 Pilot 前先冻结一版 updated strongest-neighbor matrix 和 safe claim；否则 Pilot 可能验证一个已被宽泛先例覆盖的 claim。 |
| FMEA | 足够 | 保持候选/ablation；禁止默认传统 RPN。 |
| Pilot | 中高 | 预先规定成功/停止标准、invalid witness 率、成本、置信区间、负结果处理，避免只挑成功案例。 |

因此，v1.2 可以作为后续工作的骨架，但它本身是**计划，不是对 feasibility 或 novelty 的证据**。在执行前应把上述新增近邻和因果协议写入其 gate；本轮按用户要求不执行该计划。

---

## 14. 下一步最重要的五项修正或核验任务

以下仅是后续优先级，不在本轮执行：

1. **更新 prior-art 与 safe claim。** 一手审计 OSL-MR、Causal Memory Intervention、MemAudit package-oracle、Proactive Memory Agent，并取得 `What Eviction Destroys` 的真实 PDF/元数据；据此冻结统一近邻表和一条不含“首次”的 novelty 句。
2. **冻结可测定义与反循环规则。** 指定 trigger/task 分布、need incidence 分母、rare 阈值、conditional severity rubric、独立 witness 生成/审核、retrieval failure 分解和测试集隔离。
3. **完成组件级数据/环境 go/no-go 审计。** 对 LongMemEval-V2、ConstraintRot、LongMemEval、LoCoMo、MemoryAgentBench、Terminal-Bench/τ²-Bench 逐项核对许可、入口、stable IDs、reset、tool execution、deterministic evaluator 与 provenance；不要假定单一 benchmark 全部提供。
4. **冻结 Full/Evicted/Restore 因果协议。** 明确 normal/audit plane、索引与缓存清理、环境 snapshot、配对 seeds、顺序控制、重复次数、Restore 接受标准和 retrieval/utilization 诊断。
5. **再做小规模问题存在性 Pilot。** 在 30–50 个来源可追溯单元上报告 rare-critical 非单例数、baseline eviction、条件损失、Restore recovery、invalid witness 率、评判一致性、成本与置信区间；达到预设 gate 后才进入完整方法/代码开发。

---

## 最终明确回答

**截至当前已完成内容，PREEMPT-Mem 的核心 Story 和 pre-trigger counterfactual retention 定位仍然成立，但只在收窄后的“完整组合”层面成立。** 没有发现覆盖 `unseen trigger + active Future Decision Witness generation + executable item-level effective eviction + conditional severe loss + budgeted retention/testing` 的核心碰撞；因此不是 `CORE COLLISION`，也不需要重新选择论文 Idea。[P][S]

**已经可以视为可靠基础的部分：** 问题动机；rare 与 critical 分离；external addressable episodic/semantic memory 的主范围；effective eviction 的实验方向；Future Decision Witness + executable intervention 的组合价值；FMEA 只作候选 triage；以及第一份报告对证据边界和未决问题的谨慎处理。

**进入 Pilot 前必须修正的部分：** 补入四个强近邻并收窄 Contribution 1；闭环 `What Eviction Destroys`；把数据可行性改为待审计假设；冻结可测且非循环的 rarity/criticality；纠正 Full/Evicted/Restore 的因果角色；锁定 external-memory 范围；合并重复贡献；把所有实验优越性从“贡献事实”改为“待检验假设”。

**最终等级：PASS WITH REVISIONS。**
