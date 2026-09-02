# PREEMPT-Mem 论文内容与候选统一设计报告取舍说明

> 论文暂定题目：**Remember Before It Matters: Preemptive Counterfactual Retention for Rare-but-Critical Agent Memory**  
> 文档目的：介绍论文当前主线，并逐项说明哪些设计由当前项目保留、哪些优于候选《统一设计文档》、哪些内容从该文档选择性吸收，以及哪些内容未被采用。  
> 状态说明：本文区分“已完成的机制验证”“正在进行的实验”和“尚待实证的论文主张”。候选报告中的 `USER_CONFIRMED`、D1–D18 和预期结果，不自动构成本项目已经确认的事实。

## 1. 总体结论

PREEMPT-Mem 研究一个现有 Agent 长期记忆系统容易忽略的问题：**某条外部记忆在多数任务中很少被需要，因此会被基于频率、最近性或历史效用的策略删除；但它一旦在特定未来任务中被需要，缺失可能造成严重失败、硬约束违规或高代价后果。**

论文提出的核心方法不是简单提高 memory importance 分数，也不是在失败后恢复记忆，而是：

> 在记忆即将被删除之前，主动生成与该记忆相关、可执行的未来风险情境，即 Future Decision Witness；再通过与 witness 独立冻结的 hidden future trigger 检验它能否提前预测真实删除损失，并在相同存储和审计预算下优先保留高风险记忆。

候选《统一设计文档》不应被整体替换进论文。最合理的利用方式是：

- 保留当前论文的核心问题、hidden-trigger transfer、真实语义 Agent、分阶段实验和 80→40 正式 Pilot；
- 吸收候选报告中更严谨的 Need、Eligible rarity、等价信息载体、失败分层和诊断性对照；
- 暂不采用历史风险头、三轨主动审计、完整五臂全量化、分层存储与 stress-CVaR 等扩张模块。

因此，最终选择是**以当前方案为主、对候选报告进行选择性学习**，而不是完全排除或完全学习。

## 2. 论文研究对象与问题边界

### 2.1 研究对象

论文主要研究具有稳定 ID、自然语言内容、来源、版本和可删除/恢复能力的**可寻址外部长期记忆**，例如：

- 从历史交互中总结出的用户约束；
- 完成任务时发现的 workflow prerequisite；
- 工具使用中的 gotcha 或异常处理经验；
- 环境状态变化、权限边界和跨任务持续信息。

论文不把参数权重中的知识、不可分解隐状态或纯 KV cache 当作主要研究对象。检索和 active context selection 会被完整记录，但论文的主要干预点仍是 external memory storage eviction。

**标注｜吸收候选报告：**明确区分 storage absence、retrieval miss 和 active-context exclusion。该区分能判断失败究竟来自“记忆被删除”“记忆存在但未检索”还是“已检索但未进入上下文”，避免把 retention、retrieval 和 context management 混成同一个问题。

**标注｜我们的设计更优：**当前方案不仅形式上区分这三类失败，还要求在 A-S 语义 Mini-Pilot 中证明 prompt 和 memory content 真实进入模型，并通过 metamorphic tests 排除 `memory_id`、`policy_id` 或硬编码动作旁路。候选报告提供了系统分层，但没有针对当前已发现的 selector-channel 缺陷给出同等具体的修复和验证门禁。

### 2.2 核心研究问题

论文回答三个递进问题：

1. **现象问题：**公开、可执行的 Agent workload 中，是否存在低未来需求概率但高条件删除损失的外部记忆？常用 retention 基线是否会系统性漏掉它们？
2. **预测问题：**在自然 trigger 出现前，Future Decision Witness 能否发现这些记忆的潜在严重后果，并预测独立 hidden trigger 上的实际损失？
3. **决策问题：**在相同 memory budget 和 counterfactual-testing budget 下，PREEMPT-Mem 能否减少 severe failure 和尾部损失，同时基本保持平均任务成功率？

**标注｜我们的设计更优：**候选报告把问题扩展到五臂因果审计、历史风险头、三轨 active search 和分层风险优化，形成五个研究问题。当前三问结构更集中，每一问直接对应“现象—方法—系统收益”三项论文贡献，也更适合在一篇 ICLR 论文内形成完整证据链。

## 3. Rare、Need 与 Criticality 的定义

### 3.1 Need：任务是否真正依赖某项信息

Need 不由 Agent 是否检索或引用某条 memory 决定，而由任务的正确决策是否依赖该 memory 承载的信息命题决定。若改变该命题的真实取值会改变满足任务目标和硬约束的正确行为集合，则该任务需要该命题。

这使 Need 与 Agent 的具体行为分离：一个失败的 Agent 可能没有检索真正需要的信息，一个啰嗦的 Agent 也可能引用并不需要的信息。

**标注｜吸收候选报告：**采用命题级 Need，而不是用 retrieval log、字符串命中或“删除后是否失败”定义 Need。这样可以避免“未检索→被判为不需要→更容易删除”的循环，也避免用 criticality 实验反过来定义 Need。

### 3.2 Rarity：在合格机会中的低需求概率

对 memory \(m_i\)，先定义 eligible opportunity：相关功能、权限、工具和操作阶段确实存在，使该信息有机会成为必要条件。再定义：

\[
\rho_i=P(N_i=1\mid E_i=1).
\]

rarity 只在所有方法、阈值和选择规则冻结后，由独立 held-out workload 估计；它不进入 witness generator、importance、风险评分或保留选择器。

主分析报告连续 Need rate 以及 bottom 10%/20% 等预注册子组，不从人工平衡的 Mini-Pilot 或 40 条分析集推断真实部署 prevalence。

**标注｜吸收候选报告：**采用 Eligible-conditioned rarity 和 evaluation-only 原则。它防止把大量根本不可能需要该信息的任务放入分母，人为制造“rare”，也防止方法直接读取 rare 标签后形成信息泄漏。

**标注｜我们的设计更优：**在采用连续 rarity 曲线的同时，保留预注册且容易解释的 bottom 10%/20% 子组。候选报告主要依赖 bottom-q 连续分析；当前方案兼顾统计稳健性和论文可解释性，更容易回答“什么样的记忆被称为 rare”。

### 3.3 Criticality：需要该信息时，删除造成多大因果损失

Criticality 被定义为在 Need=1 的独立未来任务上，Evicted 相对 Full 的条件删除损失分布。主要记录：

- paired task loss；
- severe failure；
- 硬约束或权限违规；
- 不可逆或高影响状态变化；
- 恢复成本；
- Restore recovery；
- 平均效用与 P90/P95 等尾部风险。

severity 必须由程序化 evaluator event 或 state diff 确定，而不是由同一个 LLM 自行评分。0–4 等级可以用于人类理解，但不将 ordinal 分数相乘，也不使用传统 FMEA RPN 作为最终决策公式。

**标注｜吸收候选报告：**采用多维 criticality，不把 0/1/2 ordinal 均值当作唯一严重性指标；同时保留 hard violation、irreversible effect 和 recovery cost 等实际后果。

**标注｜我们的设计更优：**主 criticality 比较使用真实端到端的 Full-Retrieval/Evicted/Restore，而不是以强制把 memory 注入 active context 的 Full-Oracle 作为唯一基准。Full-Oracle 可以诊断“信息存在时的能力上界”，但若正常检索根本无法取得记忆，它会高估实际 storage retention 的收益。当前方案将真实保留价值与 oracle 上界分开解释，因果主张更贴近部署系统。

## 4. PREEMPT-Mem 核心方法

### 4.1 总体流程

PREEMPT-Mem 的主流程为：

1. 冻结的 retention baseline 在给定存储预算下提出拟删除集合；
2. 对拟删除 memory 生成 deletion-sensitive Future Decision Witness；
3. 静态检查 witness 的环境可达性、工具合法性、可执行 oracle、等价信息泄漏和重复 failure mode；
4. 冻结一个生成器不可见、与 witness 独立的 hidden future trigger；
5. 在相同模型、prompt、工具、环境快照和 seed 下执行 Full/Evicted/Restore；
6. 根据 hidden trigger 上的真实删除损失评估 witness 的预测能力；
7. 在相同 memory budget 与 testing budget 下，优先保留预测并验证为高风险的 memory；
8. 比较平均任务效用、严重失败、尾部风险和额外审计成本。

### 4.2 Future Decision Witness

Witness generator 可以看到：

- memory 的自然语言内容和允许公开的 provenance；
- 工具 schema；
- 环境能力和生成协议。

它不能看到：

- held-out rarity；
- hidden future trigger；
- Need 标签；
- gold action 或 gold evaluator；
- 最终 criticality 标签；
- Full/Evicted/Restore 运行结果。

Witness 输出未来触发条件、初始状态、任务请求、预期正确行为、成功/违规 oracle 和可能的等价信息路径。无法执行或没有明确 oracle 的 witness 只记为 invalid/hypothesized，不能计入 validated critical。

**标注｜吸收候选报告：**采用 Witness compiler，提前检查工具参数、环境可达性、程序化 oracle、等价信息载体和 failure-mode duplication。它可以减少生成器制造不可执行或重复场景的比例。

**标注｜我们的设计更优：**候选报告主要在生成器构造的 witness 上进行五臂验证，容易形成“生成情境—定义标签—在同一情境证明自己”的自证循环。当前方案要求 witness 预测一个生成器不可见、预先冻结的 hidden trigger；因此验证的是 prospective transfer，而不只是 witness 的内部自洽性。这是论文相对 restore audit、decision-loss audit 和普通 risk prompting 的关键差异。

### 4.3 Full/Evicted/Restore 主因果协议

每个 memory–future-task unit 从相同环境快照执行：

- **Full：**目标 memory 正常存在、正常检索和使用；
- **Evicted：**目标 memory 及 Agent 可达的等价载体和派生信息被有效删除；
- **Restore：**恢复完全相同的 memory item、ID、content、provenance、索引和 metadata。

预期的关键模式不是预写结果，而是待检验：

\[
Y^{Full}\approx Y^{Restore}>Y^{Evicted}.
\]

Full-Oracle 和 Decoy-Control 可以作为诊断：前者测量 forced exposure 上界，后者检查非特异性删除效应。但它们不替代 hidden trigger，也不必对所有案例、所有 seed 全量运行。

**标注｜吸收候选报告：**吸收 Full-Oracle 和 Decoy-Control 的诊断思想。对于检索失败、关键高风险案例或审稿人最可能质疑的子集，二者能帮助分离 retrieval gap 和随机删除效应。

**标注｜我们的设计更优：**以三分支作为主协议、五臂作为有针对性的诊断，比所有样本固定五臂更节省预算；节省的运行量可用于更多 memory family、独立 hidden tasks 和多 seed。这里不是认为五臂因果控制“不好”，而是当前分配能把计算用在更直接支撑核心 claim 的证据上。

### 4.4 Effective eviction 与安全执行

Evicted 必须从 canonical store、检索索引、缓存、active context、session summary、aliases、near-duplicates、派生规则和 Agent 可访问日志中封锁目标信息，同时证明 distractor 没有被误删。Restore 必须恢复原始 item，而不是以语义近似文本替代。

模型只能产生结构化 JSON/tool call，由 allowlisted executor 执行；未知工具、非法字段和路径访问 fail-closed。模型不执行任意 Python、shell 或文件系统代码。所有请求、响应、检索、工具调用、数据库差异、evaluator、manifest 和 SHA-256 都需保存并可独立重放。

**标注｜吸收候选报告：**采用 proposition 与 equivalent carriers 的映射，防止 summary、project instruction、重复 memory 或工具 guard 暗中承载相同信息。

**标注｜我们的设计更优：**当前主线增加了候选报告没有充分展开的 raw evidence 独立重放、上游数据锚点、severity 可达性测试、结构化工具执行、leakage probe 和 manifest 完整性。这些控制直接回应 A-R fresh reviewer 的 WARN，能够提高实验的可复核性和安全边界可信度。

## 5. 实验设计与当前阶段

### 5.1 已完成：机制级因果隔离 Smoke

第三步 A-R 已经证明：在冻结的 trusted-worker、constructed deterministic selector-channel 范围内，可以对目标 external memory 实现隔离的 Full/Evicted/Restore 干预，且恢复数据库状态、越权探针、哈希与 manifest 均可复核。

但该结果不能证明模型真正理解 memory 语义，因为旧行为仍由 `policy_id` selector 驱动，prompt 是 dead input。因此它只能作为 causal infrastructure validation，不能写成论文的主科学结果。

**标注｜我们的设计更优：**当前方案主动保留这一负面证据边界，没有把通过 Smoke 写成 PREEMPT 已有效。候选报告虽标记很多设计为 `EMPIRICALLY_PENDING`，却把若干未经用户确认的模块标成 `USER_CONFIRMED`，容易在后续实施中混淆“设计设想”和“项目事实”。

### 5.2 正在进行：8–12 条真实语义 Mini-Pilot

Mini-Pilot 的首要目标是证明：

- prompt 确实进入真实模型；
- Agent 根据 memory 的自然语言内容而不是 ID/selector 决策；
- Evicted 无法通过旁路取得目标信息；
- 至少两类 memory 出现可解释的 Full≈Restore>Evicted；
- witness 对独立 hidden trigger 的删除损失方向具有预测能力；
- critical 与 noncritical 对照同时存在。

通过 metamorphic tests 检查：改变 ID 不应改变语义行为；保留 ID 但遮蔽关键语义应产生可解释变化；distractor 的改变不应触发目标动作。

只有 Mini-Pilot 通过内部门禁并经 fresh reviewer 独立审计，才进入完整 Pilot。

**标注｜我们的设计更优：**先做小规模真实语义 GO/NO-GO，再投入主实验，比直接执行 540-run 更符合当前证据阶段。它能以较低成本尽早发现模型不读 memory、witness 无 transfer、检索链失效或 evaluator 泄漏等致命问题，避免在错误通道上扩大样本。

### 5.3 后续正式 Pilot：80 候选池→40 分析集

正式 Pilot 从更大的候选池中按预注册规则形成 40 条分析集，覆盖 workflow、gotcha、constraint/permission 和可行的 dynamic state，并标记 natural、adapted、constructed 来源。每条包含目标 memory、语义相近 distractor、source episode、future-task relationship、witness 与独立 hidden trigger。

主轨使用 AppWorld 构建 controlled/semi-synthetic executable causal benchmark；自然性辅轨使用 LongMemEval-V2 检查真实跨会话内容、长间隔、语义改写和检索外部效度。自然辅轨不承担严重工具后果主结论，也不与 AppWorld 合并估计 prevalence。

**标注｜我们的设计更优：**40 条分析集比候选报告的 18 条配额池更有机会覆盖多种 memory/failure family，并支持分组统计和失败分析；80→40 的冻结筛选还能保留排除原因，减少只挑成功案例的风险。候选报告的 18 条×2任务×3 seed×5臂虽然运行次数达到 540，但独立 memory 单位仍只有 18，增加重复 rollout 不能替代增加研究单位和语义多样性。

### 5.4 对比方法与公平性

计划对比：

- LRU/recency；
- LFU/frequency；
- relevance/semantic importance；
- realized utility 或 learn-to-evict 类方法；
- random retention；
- severity-only 或 generic risk prompting；
- explicit pinning/guard；
- Full-memory 上界；
- PREEMPT-Mem。

所有方法使用相同 memory pool、存储成本、memory budget、counterfactual-testing budget、模型、工具调用预算和评估任务。不能通过让 PREEMPT 保留更多 memory 获得不公平优势。

**标注｜吸收候选报告：**加入 explicit pinning/guard 强基线。对于具有明确 authority 和可程序化执行的治理规则，直接 pin 或 tool guard 可能比生成式风险发现更可靠；PREEMPT 应重点证明它对隐式约束、状态更新、gotcha 和 workflow prerequisite 的额外价值。

## 6. 评价指标与预期证据链

### 6.1 现象证据

- eligible Need rate 与置信区间；
- bottom-q memory 在基线拟删除集中的覆盖率；
- low-Need memory 的条件删除损失；
- 不同 memory/failure family 的 severe-event rate。

### 6.2 Witness 证据

- generation rate；
- executable validity；
- hidden-trigger precision/recall 或方向一致性；
- false positive、false negative；
- failure-mode duplication；
- 相对模板、随机场景和 generic risk prompting 的增量。

### 6.3 系统证据

- average task success/utility；
- severe failure 和 hard violation；
- P90/P95 conditional loss；
- storage 与审计成本；
- average utility–severe/tail loss Pareto curve；
- Full/Restore 一致率和独立 replay 完整性。

**标注｜吸收候选报告：**采用平均效用、severe-event、worst-group/tail loss 和审计成本的多维报告方式，避免只报告一个合成总分。

**标注｜我们的设计更优：**当前主指标直接围绕“witness 是否转移到 hidden trigger”和“相同双预算下是否减少严重失败”组织。候选报告的审计发现率、propensity 校正、residual unaudited risk、risk-head regret 和 stress-CVaR 会产生第二套方法目标，容易使主结果表无法清楚回答 PREEMPT 的核心假设。

## 7. 论文预期贡献与新颖性边界

如果实验通过预注册门禁，论文可形成三项核心贡献：

1. **现象贡献：**操作化并实证识别低 eligible-conditioned Need、但高 Need-conditioned deletion loss 的 external agent memory；证明常用历史 retention 信号可能遗漏这类记忆。
2. **方法贡献：**提出 deletion-sensitive Future Decision Witness，在自然 trigger 出现前生成可执行风险证据，并通过独立 hidden trigger 验证其 prospective predictive value。
3. **系统贡献：**在相同存储和 counterfactual-testing 预算下，降低 severe failure 和尾部损失，同时基本保持平均任务效用。

Restore counterfactual、decision consequence、importance/recency、CVaR 和显式 constraint pinning 都已有相关研究思路，不能单独声称为主要原创点。论文最应守住的新颖性是：

> **pre-eviction witness generation + generator-hidden future-task transfer + budgeted severe-risk retention。**

**标注｜我们的设计更优：**当前贡献只有三项，并共享同一条证据链。候选报告提出五项贡献，其中五臂 audit、三轨审计和 stress-CVaR 都可能分别需要独立论文级实验，而且与近邻工作存在更直接的碰撞。收缩贡献不是降低论文含金量，而是把最独特、最可证伪的部分做深。

## 8. 从候选报告正式吸收的内容

以下内容在不改变当前主线的前提下值得吸收：

| 吸收内容 | 在本论文中的用途 | 吸收原因 |
|---|---|---|
| storage/retrieval/active-context 三类失败 | 问题定义、错误归因和实验日志 | 防止把不同干预面混为一谈 |
| 命题级 Need | rarity 分母、任务 oracle、证据标注 | 避免用 Agent 行为或删除结果循环定义 Need |
| Eligible-conditioned rarity | held-out workload 评价 | 避免人为稀释分母、制造虚假 rare |
| rarity evaluation-only | 数据隔离与泄漏门禁 | 防止方法直接读取 rare 标签 |
| proposition/equivalent carriers | effective eviction | 封锁 summary、重复条目、guard 等信息旁路 |
| Witness compiler | witness 预检 | 提高可执行性、oracle 质量和 failure-mode 多样性 |
| 多维 criticality | 主评价指标 | ordinal 单分数无法表达实际后果 |
| Full-Oracle | 关键子集诊断 | 分离信息能力上界与正常 retrieval gap |
| Decoy-Control | 关键子集诊断 | 排除非特异性删除和环境扰动 |
| explicit pinning/guard | 强基线 | 证明 PREEMPT 不是读取显式安全词面 |
| 不估计自然 prevalence | claim 边界 | 受控池不能代表真实部署总体 |
| 证据门控与 claim 收缩 | Go/Stop 规则 | 防止无增量模块仅因形式复杂被保留 |

## 9. 候选报告未采用的内容及原因

下表中的“不采用”并不意味着这些思想在所有研究中都不好，而是指它们**不适合当前论文阶段、核心问题、数据规模和投稿时限**。

| 未采用内容 | 为什么当前不采用／哪里不好 | 后续可能位置 |
|---|---|---|
| 固定 \(S/U/R/F\) importance 公式并在开发集学习权重 | 需要额外开发集和权重学习，容易把论文变成 importance 建模；主方法应能接在多种冻结 retention baseline 之后，而不应被一个未经验证的自定义公式绑定 | 基线实现或敏感性分析 |
| 独立历史五臂审计风险头 | 当前没有足够、时间隔离的历史五臂标签；少量标签训练风险头容易过拟合，并可能让收益来自 supervised risk classifier 而不是 Future Witness | 数据规模足够后的扩展 |
| 60/20/20 三轨主动审计及 80/10/10、40/30/30 敏感性 | 同时引入风险搜索、不确定性、多样性、随机哨兵和 acquisition tuning，形成新的 active-search 研究问题；需要大量隐藏全标签才能公平评估 | 第二篇工作或大规模消融 |
| propensity logging 与总体风险校正作为核心贡献 | 只有在自适应抽样并试图估计总体 prevalence/总体风险时才是核心；本论文明确不从受控池推断自然 prevalence | 若未来研究 deployment prevalence 时采用 |
| 硬风险层＋残余风险层＋普通效用层 | 需要可靠的硬风险标签、替代 guard 成本和预算不可行性分析；当前正例数量未知，分层优化可能退化成规则 pinning | 主结果足够后作为可选策略 |
| stress-CVaR 优化目标 | witness 概率未经部署校准，损失分布在小样本下可能退化；复杂风险目标可能没有超过 severe-event rate/P90/P95 的实证增量 | 只在非退化结果中作为消融 |
| 把五臂作为全部案例、全部 seed 的强制主协议 | Full-Oracle 和 Decoy 有诊断价值，但全量五臂显著提高成本；且仍不能替代 generator-hidden trigger transfer | 关键子集或审稿补充实验 |
| 18 memory×2任务×3 seed×5臂的 540-run Pilot | rollout 数量看似很大，但只有 18 个独立 memory，统计与语义多样性有限；并且会在真实语义通道尚未通过前投入大量计算 | 不能替代 8–12 Mini-Pilot 与 80→40 主 Pilot |
| 用 18 条固定三机制配额替换 80→40 | 容易被质疑为人工平衡、模板化和挑选案例，也难支持多个 memory family 的分组分析 | 可作为最小机制验证集 |
| LongMemEval 与 LoCoMo 同时设为强制辅轨 | 两个自然 benchmark 会增加适配、Need 标注和统计负担；当前 LongMemEval-V2 已足以先承担自然性辅证 | 时间充足时再加入 LoCoMo |
| 一般双项依赖、冗余与 workflow prerequisite 组合消融 | 多 memory minimal cut/dependency 是另一个完整问题；在单 item 因果链尚未建立时加入会扩大识别难度 | 后续高阶依赖研究 |
| 五项并列论文贡献 | 会让 novelty 分散到已有近邻较多的 restore audit、active search 和 CVaR，审稿人难以识别最核心创新 | 保留三项共享证据链的贡献 |
| 将 witness 自身的五臂通过视为主要 pre-trigger 证据 | 生成器可以人为构造一个“缺失该 memory 必然失败”的任务，只能证明自洽，不能证明预测未知未来 | 必须被独立 hidden trigger transfer 替代 |
| 以 Full-Oracle 差值作为唯一 criticality | 强制注入绕过正常 retrieval，可能高估真实 retention 收益 | 仅作为能力上界和 retrieval gap 诊断 |
| `USER_CONFIRMED`、D1–D18 和“统一依据”表述 | 这些状态没有经过本项目当前决策流程确认；直接采用会把候选作者的设想写成用户决定，并污染项目事实边界 | 仅作为候选报告内部记录，不进入项目状态 |
| 直接按候选报告 12 步行动清单实现全部模块 | 跳过 A-S 真实语义门禁，可能在 selector/hard-code、witness 无 transfer 或 evaluator 泄漏尚未解决时扩大错误实验 | 必须按 A-S→fresh audit→主 Pilot 顺序推进 |

## 10. 推荐的最终论文结构

1. **Introduction**：rare-but-critical 现象、历史 importance 的盲区、PREEMPT 核心直觉和三项贡献。
2. **Related Work**：Agent memory retention、eviction/restore audit、prospective trigger、风险敏感选择；明确哪些能力借鉴已有工作。
3. **Problem Setup**：external memory 边界、Need、Eligible rarity、criticality、双预算和等价载体。
4. **Method**：Future Decision Witness、compiler、hidden-trigger protocol、Full/Evicted/Restore 和预算化保留。
5. **Experimental Setup**：AppWorld 主轨、LongMemEval-V2 辅轨、80→40 数据形成、基线、泄漏控制和统计协议。
6. **Results**：rare-critical 现象、hidden-trigger transfer、基线比较、平均效用—严重风险 Pareto。
7. **Analysis**：Full-Oracle/Decoy 诊断、retrieval gap、memory family、失败案例、成本和消融。
8. **Limitations and Ethics**：受控/半合成场景、无 prevalence claim、oracle 依赖、模型与任务外推边界。
9. **Conclusion**：删除前主动预见未来风险的价值与适用范围。

## 11. 最终取舍判断

候选《统一设计文档》在定义严谨性、变量隔离和诊断控制方面有明显帮助，尤其是命题级 Need、Eligible rarity、等价载体、Witness compiler、多维 criticality、Full-Oracle/Decoy 诊断和 explicit guard 基线。

但它作为整套论文方案存在三个主要问题：

1. **范围过大：**同时建设 witness、五臂 audit、风险头、三轨主动审计和分层 CVaR，等于把多个研究课题装进一篇论文；
2. **核心创新被稀释：**它强化了因果审计，却没有把 generator-hidden future-task transfer 放在绝对中心，容易退化为“生成一个测试，再证明该测试成立”；
3. **与当前证据阶段不匹配：**项目刚完成 selector-channel 的机制级修复，真实语义通道尚未通过；此时直接扩展到 540 runs 和完整方法栈会放大尚未识别的科学风险。

因此最终建议是：

> **保持当前 PREEMPT-Mem 主线不变，将候选报告降级为定义与实验控制素材库；吸收其约束性、诊断性内容，排除会新增独立研究问题或削弱 hidden-trigger 核心证据的模块。**

当前最重要的下一步仍是完成 8–12 条真实语义 Mini-Pilot。只有它证明 Agent 确实使用 memory content、删除会造成语义性损失、Restore 能恢复、Witness 能预测独立 hidden trigger，后续 40-memory 正式 Pilot 和论文三项核心贡献才有可靠基础。
