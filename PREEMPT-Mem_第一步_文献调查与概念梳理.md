# PREEMPT-Mem：第一步文献调查与概念梳理

> 调研日期：2026-08-27  
> 研究范围：Agent Memory、长期记忆、上下文管理/压缩、retention、forgetting 与 eviction  
> 本轮边界：只做文献调查与概念梳理；不构造数据集，不设计 FMEA 模块，不实现代码  
> 证据标记：**[文献事实]** 表示论文原文可直接支持；**[综合判断]** 表示跨论文归纳；**[待验证]** 表示需要后续代码、数据或实验确认

## 0. 执行摘要

本轮得到六项主要结论。

1. **[文献事实] Agent Memory 已从“存储并检索历史”发展到“主动写入、更新、压缩、删除和学习管理策略”，但大量论文仍只优化检索或上下文裁剪，并未执行持久记忆删除。** 经典系统通常围绕 recency、relevance、LLM importance、访问频率、成功/失败、冗余度和后验任务效用组织记忆。2026 年的工作已经开始直接学习 ADD/UPDATE/DELETE、在固定容量下做 value-aware retention，或用下游结果反馈管理策略。

2. **[文献事实] “rare but important”这一现象级表述已经出现，不能再宣称该观察从未被提出。** 近期综述明确指出，LRU 等启发式遗忘可能删除“很少访问但对正确决策必不可少”的长尾知识；TraceRetain 也直接使用 “rare but important memories” 描述 memory pollution 的后果。然而，已核验论文通常没有把 rarity 和 criticality 分开定义、联合标注并专门评测这一尾部区域。

3. **[综合判断] rare 至少有三种不等价含义：低访问/低需求频率、低事件基率、以及高信息惊奇度。** 现有研究经常用访问次数、近期查询相似度或 token surprisal 作为代理，但三者不能互换。低访问可能只是检索器失灵；高 surprisal 只是语言模型难预测；事件罕见也不意味着未来不会关键地再发生。

4. **[文献事实] importance/value 已有多种量化，但 criticality 几乎没有成熟的 Agent Memory 定义。** 现有量化从 LLM 的 poignancy 评分、时间衰减与访问强化、未来效用预测、已实现的平均 downstream utility、任务级强化学习奖励，到条目级反事实影响都有。它们大多衡量“通常是否有用”或“当前是否相关”，很少衡量“未来一旦需要而缺失时，最坏后果有多严重”。

5. **[综合判断] PREEMPT-Mem 最适合把主研究对象限定为可寻址、可删除、可恢复的外部持久记忆条目。** 参数记忆和隐状态难以对应单条可逆删除；KV/token 级内部记忆虽然可淘汰，但其单位、恢复语义和任务后果都与外部 episodic/semantic records 不同。工作上下文可以作为边界条件或对照，而不宜与主问题混为一体。

6. **[综合判断] 当前仍有可防守的创新空间，但表述必须收窄。** 最接近的碰撞来自 Learning What to Remember、TraceRetain、How Memory Management Impacts LLM Agents、CURATOR、MemAudit、ACON、Memory-R1/AgeMem。PREEMPT-Mem 不应宣称首次研究 memory importance、future utility、deletion 或 counterfactual；更稳妥的方向是：**面向低频但高后果的有益外部记忆，在实际删除前，对少量候选做选择性、条目级、可恢复的后果验证，并以严重任务失败而非平均 QA 分数作为核心风险语义。** 这一表述仍是研究假设，尚未被本轮证明。

## 1. 调研范围、方法与证据边界

### 1.1 检索与筛选

本轮以 2023–2026 年工作为主，补充必要经典文献。检索主题覆盖：

- agent memory、long-term memory、episodic/semantic/procedural memory；
- memory retention、forgetting、eviction、pruning、admission；
- context management、context compression、working-memory/KV eviction；
- importance、utility、value、criticality、rarity、surprisal；
- deletion impact、counterfactual influence、causal attribution；
- memory poisoning、safety memory 与高后果工具行为。

机器检索阶段从 OpenAlex 获得 500 条宽检索记录，去重后 296 条；随后以关键题名和近邻概念做定向检索，得到 206 条去重候选。Semantic Scholar 接口发生 429 限流，因此没有把单一 API 的结果当作完整性保证。最终结论来自对核心论文的官方 proceedings、ACL Anthology、OpenReview、PMLR、AAAI、ACM 页面或 arXiv 全文逐条核验，而不是仅依赖检索摘要。

### 1.2 本轮没有使用的材料

- 没有依赖项目中的旧版 Idea 报告或其中结论。
- 没有进入公开数据集筛选或构造。
- 没有设计 FMEA 的评分、RPN 或筛选模块。
- 没有实现 PREEMPT、训练模型或运行 Agent 实验。
- 本轮未系统审计各项目源代码；论文已经足以确认大多数概念与算法语义。需要用代码确认的实现细节列在第 10 节。

### 1.3 重要术语边界

**[综合判断] 必须区分四种经常被论文共同称为“遗忘/删除”的操作：**

| 操作 | 对象与后果 | 是否等同 PREEMPT-Mem 的 deletion |
|---|---|---|
| Retrieval filtering | 条目仍在库中，只是不进入当前查询上下文 | 否 |
| Context eviction | token/message 被移出当前上下文，原文可能仍在 recall/archive | 通常否 |
| Compression/consolidation | 细节变成摘要或高层表示；可能可回查原文，也可能有损 | 视可恢复性而定 |
| Persistent deletion/invalidation | 条目从可用持久状态中移除或失效，未来不能正常恢复 | 是主要研究对象 |

这一区分很重要。例如 Generative Agents 的 recency 只影响检索分数；MemGPT 会把旧消息移出主上下文但仍保存在 recall storage；Mem0 的 DELETE 主要解决新旧事实冲突；这些都不能直接当作“容量压力下不可逆删除有益记忆”的同一问题。

## 2. 文献综述：Agent Memory 的概念与整体脉络

### 2.1 文献如何划分 Agent Memory

**[文献事实] CoALA 将语言代理记忆划分为：**

- working memory：当前决策中活跃的信息；
- episodic memory：具体经历、轨迹和事件；
- semantic memory：事实、概念和一般知识；
- procedural memory：如何行动的知识，既可存在模型权重，也可存在显式代码或技能。

来源：[Cognitive Architectures for Language Agents（TMLR 2024）](https://openreview.net/forum?id=1i6ZCyf1QJ)。

**[文献事实] Agent Memory 综述还可从“载体”和“生命周期”两条轴线组织：**

- 载体：token-level、parametric、latent，或更实用地分为 external 与 internal；
- 功能：factual、experiential、working；
- 生命周期：formation/writing、evolution/management、retrieval/reading；
- 遗忘信号：time-based、frequency-based、importance-driven。

来源：[Memory in the Age of AI Agents（2025/2026 综述预印本）](https://arxiv.org/html/2512.13564)、[A Survey on the Memory Mechanism of Large Language Model-based Agents（TOIS 2025）](https://doi.org/10.1145/3748302)。

### 2.2 研究脉络

#### 阶段 A：记忆流、检索与反思（2023–2024）

**[文献事实]** Generative Agents 将观察写入自然语言 memory stream，并用 recency、relevance 和 LLM 给出的 1–10 importance/poignancy 排序；累计 importance 达阈值后生成 reflection。它保存完整事件记录，主要解决“何时想起什么”，不是持久删除。[论文](https://dl.acm.org/doi/10.1145/3586183.3606763)

**[文献事实]** Reflexion 把失败反馈压缩为语言反思，并以固定容量 sliding window 保存；它提供了早期的容量边界，但淘汰主要是窗口式，而非价值或严重后果驱动。[论文](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)

**[文献事实]** MemGPT 用操作系统虚拟内存类比分离 main context 与 recall/archival storage：上下文压力触发 FIFO 移出与摘要，但原始消息可在外部层恢复。这说明 context eviction 不等于 persistent deletion。[论文](https://arxiv.org/abs/2310.08560)

**[文献事实]** MemoryBank 引入简化 Ebbinghaus 曲线：保留率随距上次访问时间下降，召回会增强 memory strength。该设计使“常访问”天然更容易被保留，也暴露了低频高后果条目的风险。[论文](https://ojs.aaai.org/index.php/AAAI/article/view/29946)

#### 阶段 B：结构化、压缩与动态更新（2024–2025）

**[文献事实]** ReadAgent 把长文分成 episodes，生成 gist，并允许回查原页；RAPTOR、HippoRAG 分别用层级摘要树和知识图关联改善长程检索。它们重点是压缩与读取，而非在线删除。[ReadAgent](https://proceedings.mlr.press/v235/lee24c.html)、[RAPTOR](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8a2acd174940dbca361a6398a4f9df91-Abstract-Conference.html)、[HippoRAG](https://proceedings.neurips.cc/paper_files/paper/2024/hash/6ddc001d07ca4f319af96a3024f6dbd1-Abstract-Conference.html)

**[文献事实]** A-MEM 以 Zettelkasten 式 notes、链接和邻居演化组织外部记忆；Mem0 从对话抽取 salient facts，并对相似旧记忆执行 ADD/UPDATE/DELETE/NOOP。A-MEM 没有容量淘汰，Mem0 的删除主要表示矛盾或过时，而不是删除后的未来风险。[A-MEM](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html)、[Mem0](https://arxiv.org/abs/2504.19413)

**[文献事实]** HiAgent 对单次长程任务中的 working memory 按子目标分块和摘要；LongLLMLingua 做 query-aware prompt compression。二者更接近内部/上下文压缩，不等同于跨会话外部记忆治理。[HiAgent](https://aclanthology.org/2025.acl-long.1575/)、[LongLLMLingua](https://aclanthology.org/2024.acl-long.91/)

#### 阶段 C：可学习管理、预算淘汰与因果审计（2025–2026）

**[文献事实]** Memory-R1 和 AgeMem 把 ADD、UPDATE、DELETE、NOOP、SUMMARY、FILTER 等操作学习为策略，并由下游 QA 或任务奖励训练。它们突破了固定启发式，但信用主要分配给整段管理轨迹，尚未显式分解单条记忆的未来需求概率和失败严重度。[Memory-R1](https://aclanthology.org/2026.acl-long.583/)、[AgeMem](https://aclanthology.org/2026.acl-long.981/)

**[文献事实]** Xiong 等直接研究 experience addition/deletion：周期策略删除低检索频率记录，history-based 策略删除已被多次检索且平均 downstream utility 较低的记录。它把真实后续效用引入删除，但对从未或很少被召回的条目缺乏可靠效用标签。[论文](https://aclanthology.org/2026.acl-long.27/)

**[文献事实]** TraceRetain 在固定容量 episodic memory 中结合访问、成功、冗余、specificity 和 observed downstream utility 等特征，超限时淘汰最低分；在 75% 合成失败干扰流中优于简单策略，但在干净 ALFWorld 上不同有界策略的差异较小。论文提到 rare-but-important，却没有独立定义或分层评测。[论文](https://arxiv.org/abs/2606.29178)

**[文献事实]** Learning What to Remember 提出多因素 memory value，用一个值控制编码、遗忘和检索；LongMemEval 上以“金证据保留率”训练/评价，盲未来查询条件下优于 recency 和单因素，但论文明确承认该代理指标不等于完整任务准确率。其实验中的七个理论因素只有四个实际启用，task utility 与 usage history 为零值占位。[论文](https://arxiv.org/abs/2606.12945)

**[文献事实]** CURATOR 用单位字节净价值控制 KEEP/SHARE/TRUST，其中 value 包含基于近期查询分布的 retrieval propensity 和加入检索集的平均边际效用。它是直接的 value-aware budget eviction，但近期查询 propensity 会天然降低低频未来需求的权重，self-consistency utility 也不等于真实失败严重度。[论文](https://arxiv.org/abs/2606.25115)

**[文献事实]** MemAudit 对已观察到的有害事件执行 remove-one-memory replay，计算移除一条记忆后 harmfulness 的下降，即真正的条目级删除反事实。它是本轮发现的最直接因果近邻，但目标是事后定位并删除有害/投毒记忆；PREEMPT-Mem 关心的是在失败发生前避免误删有益但关键的记忆。[论文](https://arxiv.org/abs/2605.23723)

## 3. 代表性论文对比

| 工作 | 状态 | 记忆范围 | 主要操作 | 保留/删除信号 | 与 PREEMPT-Mem 的关系 |
|---|---|---|---|---|---|
| [Generative Agents](https://dl.acm.org/doi/10.1145/3586183.3606763) | UIST 2023 | 外部 episodic | write、retrieve、reflect | recency + relevance + LLM importance | importance 是显著性，不是删除严重度；无持久淘汰 |
| [Reflexion](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html) | NeurIPS 2023 | 外部反思 | write、compress、reuse、window eviction | 失败反馈 + 固定滑窗 | failure-aware，但事后反思且按窗口淘汰 |
| [MemGPT](https://arxiv.org/abs/2310.08560) | arXiv 2023 | 混合 | page、summarize、archive、retrieve | token pressure + FIFO | 可恢复层级最相关；context eviction 非持久删除 |
| [MemoryBank](https://ojs.aaai.org/index.php/AAAI/article/view/29946) | AAAI 2024 | 外部长期对话 | write、retrieve、forget、reinforce | 时间衰减 + 召回强化 | 低频项容易衰减；无后果验证 |
| [CoALA](https://openreview.net/forum?id=1i6ZCyf1QJ) | TMLR 2024 | 概念/混合 | read、write、reason、learn | 不提出淘汰规则 | 提供 working/episodic/semantic/procedural taxonomy |
| [ExpeL](https://ojs.aaai.org/index.php/AAAI/article/view/29936) | AAAI 2024 | 外部经验 | retrieve、ADD/EDIT、UP/DOWNVOTE、delete | insight 计数降到 0 | 有显式删除，但效用投票来自已见经验 |
| [A-MEM](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html) | NeurIPS 2025 | 外部结构化 | note、link、evolve、retrieve | 语义关系和邻域演化 | 自组织而不做容量淘汰 |
| [Mem0](https://arxiv.org/abs/2504.19413) | 2025 预印本 | 外部事实/图 | extract、ADD/UPDATE/DELETE/NOOP | 新旧事实的矛盾/失效 | DELETE 语义不同：维护一致性，不是预算风险 |
| [LUFY](https://aclanthology.org/2025.dnd-16.12/) | Dialogue & Discourse 2025 | 外部对话 | score、retrieve、forget | 情绪、perplexity、LLM importance、检索次数、时间 | 明确显示 surprisal 不等同经验 rarity |
| [ACON](https://arxiv.org/abs/2510.00615) | ICLR 2026 workshop | 工作上下文 | compress、failure-pair guideline update | 全上下文成功而压缩失败的配对轨迹 | 用失败对修复压缩规则；非逐条、非在线删除前验证 |
| [A-MAC](https://arxiv.org/abs/2603.04549) | ICLR 2026 workshop | 外部写入 | admission | future utility、confidence、novelty、recency、type prior | 未来效用近邻；发生在写入准入，且是预测代理 |
| [FadeMem](https://arxiv.org/abs/2601.18642) | ICASSP 2026 | 外部长期 | score、decay、prune | 相关性、访问频率、recency | 以偏好/约束称 critical facts，但无严重度分级 |
| [Learning What to Remember](https://arxiv.org/abs/2606.12945) | 2026 预印本 | 外部记忆 | value、retain、forget、retrieve | 多因素 learned value | 与“未来值”最接近；评价是证据保留而非实际严重损失 |
| [TraceRetain](https://arxiv.org/abs/2606.29178) | 2026 预印本/workshop | 外部 episodic | bounded retention、evict | 访问、成功、冗余、observed utility 等 | 直接写 rare-but-important；未定义 rarity/criticality 或尾部后果 |
| [How Memory Management Impacts LLM Agents](https://aclanthology.org/2026.acl-long.27/) | ACL 2026 | 外部经验 | add、periodic/history delete | 访问频率 + 已实现平均效用 | 直接研究删除；回顾性均值而非低频高严重度 |
| [Memory-R1](https://aclanthology.org/2026.acl-long.583/) | ACL 2026 | 外部 | ADD/UPDATE/DELETE/NOOP | QA exact-match 的 RL reward | 学习删除，但奖励是任务轨迹级和平均正确性 |
| [AgeMem](https://aclanthology.org/2026.acl-long.981/) | ACL 2026 | 混合 LTM/STM | store、retrieve、update、summarize、discard | step-wise/task reward | 统一管理近邻；无单条未来风险分解 |
| [Memory as Action](https://aclanthology.org/2026.findings-acl.956/) | Findings ACL 2026 | 工作上下文 | in-place insert/delete | RL task reward | 直接学习上下文删除；不是可寻址跨会话持久记忆 |
| [RecMem](https://aclanthology.org/2026.findings-acl.1619/) | Findings ACL 2026 | 外部长期 | buffer、recurrence consolidation、refine | 持续语义复现 | recurrence 与 rare 方向相反；原始层仍在，非容量删除 |
| [CURATOR](https://arxiv.org/abs/2606.25115) | 2026 预印本 | 外部 experience | keep、share、trust、evict | 净价值/字节，含近期需求 propensity 与边际效用 | value-aware eviction 强近邻；可能系统性低估 rare need |
| [MemAudit](https://arxiv.org/abs/2605.23723) | 2026 预印本 | 外部持久 | remove-one replay、audit、delete | 删除后 harmfulness 的反事实下降 | 条目级因果最近；事后删除有害项，而非事前保护有益项 |
| [MAGE](https://arxiv.org/abs/2605.03228) | 2026 预印本 | 外部 shadow memory | retain critical context、pre-action risk check | 安全相关上下文与待执行动作风险 | 风险与关键上下文近邻；不管理普通记忆池的容量淘汰 |

## 4. rare、importance、value 与 criticality 的已有定义

### 4.1 rare：至少三种不兼容定义

| 定义族 | 常用代理 | 代表工作 | 能说明什么 | 不能说明什么 |
|---|---|---|---|---|
| 访问/需求稀有 | retrieval count、last-access gap、近期查询 propensity | MemoryBank、TraceRetain、Xiong、CURATOR | 过去被系统使用得少 | 可能是检索失败；不能推出未来不重要 |
| 事件/语义基率低 | 相似事件簇的频率、重复/recurrence | RecMem、去冗余 retention | 经验流中同类事件少 | 需要稳定的事件单位与分布；低基率不等于高 surprisal |
| 信息惊奇高 | −log probability、perplexity、entropy | EM-LLM、SirLLM、InfiniPot、LUFY | 模型对 token/文本难预测 | 语言难预测不等于事件在现实中罕见，更不等于后果严重 |

**[文献事实]** LUFY 明确指出 perplexity 衡量 linguistic predictability，而非 experiential rarity 或 semantic impact；一个罕见事件仍可能用常见语言表述，因此 perplexity 很低。[论文](https://aclanthology.org/2025.dnd-16.12/)

**[综合判断] PREEMPT-Mem 当前最合适的工作定义应优先使用“未来任务分布中的需求低频”或“事件族在可观测经验流中的低基率”，而不是 token surprisal。** 但二者都需要在下一阶段确定观测窗口、事件单位和分母；本轮不固定阈值。

### 4.2 importance/value：从主观显著性到因果影响

| 定义族 | 具体含义 | 优点 | 对 PREEMPT-Mem 的局限 |
|---|---|---|---|
| LLM salience/poignancy | 让 LLM 按“平凡—重要”打分 | 便宜、可解释 | 易受措辞影响；未由真实删除损失校准 |
| recency/frequency/relevance composite | 新、常用、与当前查询相似者得分高 | 工程简单 | 对 rare-but-critical 有结构性偏差 |
| future utility prediction | 写入或保留时预测未来可操作性、持久约束、需求 | 直接面向未来 | 仍是模型预测；未知未来分布下易失真 |
| observed downstream utility | 记录被取回后对后续任务的平均效果 | 使用真实反馈 | 极少取回的条目无标签；均值掩盖尾部严重失败 |
| task-outcome RL | 以最终答案/任务奖励学习 memory actions | 可端到端优化 | 信用分配通常是轨迹级；安全严重度可能被平均准确率淹没 |
| causal counterfactual influence | 删除或加入单条记忆后重放，比较输出或 harm | 因果语义最直接 | 成本高；依赖可重放任务和可靠评价器 |

代表性来源包括 [Generative Agents](https://dl.acm.org/doi/10.1145/3586183.3606763)、[A-MAC](https://arxiv.org/abs/2603.04549)、[How Memory Management Impacts LLM Agents](https://aclanthology.org/2026.acl-long.27/)、[Memory-R1](https://aclanthology.org/2026.acl-long.583/)、[CURATOR](https://arxiv.org/abs/2606.25115) 和 [MemAudit](https://arxiv.org/abs/2605.23723)。

### 4.3 criticality：现有文献最薄弱的部分

**[文献事实]** FadeMem 在合成长程 benchmark 中把用户偏好和约束称为 critical facts，并报告其保留情况，但没有把 criticality 分为不同严重度，也没有证明删除每条 critical fact 会导致何种等级的任务后果。[论文](https://arxiv.org/abs/2601.18642)

**[文献事实]** 安全记忆工作 MAGE 保留 security-critical context，并在动作执行前评估风险；MemAudit 直接用 harmfulness scorer 衡量已发生有害行为；它们说明“高后果”可以成为 Agent Memory 的评价轴，但研究目标分别是长程攻击防御和事后投毒审计。[MAGE](https://arxiv.org/abs/2605.03228)、[MemAudit](https://arxiv.org/abs/2605.23723)

**[综合判断] criticality 不应与 relevance 或一般 importance 同义。** 对 PREEMPT-Mem，一个较稳妥、仍保持概念层面的表述是：

> criticality 表示：在未来确实需要某条记忆的任务条件下，该记忆缺失相对于可用状态所造成的后果幅度，尤其关注任务完全失败、不可逆错误、错误工具操作或安全损害。

这一定义刻意把“需要发生的概率”和“发生后的损失幅度”分开：前者对应 rarity/occurrence，后者对应 criticality/severity。**[待验证]** 如何量化幅度、是否使用最大值/分位数/分级 rubric，以及如何处理多个记忆共同作用，均留待后续。

## 5. rare-but-critical 是否已被研究

### 5.1 已经出现的直接表述

**[文献事实]**

- 2025/2026 Agent Memory 综述明确指出，LRU 等启发式遗忘可能清除“seldom accessed but essential for correct decisions”的 long-tail knowledge。[来源](https://arxiv.org/html/2512.13564)
- TraceRetain 指出，冗余和失败轨迹会挤出 “rare but important” memories。[来源](https://arxiv.org/abs/2606.29178)
- FadeMem 直接评估 “critical facts”，但其 critical 主要是预设的偏好/约束类别。[来源](https://arxiv.org/abs/2601.18642)

因此，**“低频条目可能很重要”本身不是足够的新颖观察。**

### 5.2 尚未闭合的部分

在本轮核验的核心论文中，没有发现一项工作同时满足以下全部条件：

1. 将 rarity 与 criticality 明确分成两条轴；
2. rarity 指向未来需求低频或事件基率，而不只是 token surprisal；
3. criticality 指向缺失后的后果严重度，而不只是 relevance、平均 utility 或 LLM salience；
4. 对可删除的外部有益记忆条目，在实际删除前做条目级验证；
5. 专门评估低频 × 高严重度的尾部，而非只报告平均 QA/F1/成功率；
6. 保留、删除与恢复具有明确、可执行的系统语义。

**[综合判断] 初步结论：rare-but-critical 已作为风险现象被认识，但还没有形成成熟、统一的操作定义和专门问题设定。** PREEMPT-Mem 的可能空间不是“发现 rare-but-critical”，而是把这一已知风险转化为可验证的 deletion-governance 问题。

### 5.3 是否必须先证明其存在

**[综合判断] 是。** 如果论文的主要价值建立在 rare-but-critical 造成现有 eviction 失效，那么至少要证明：

- 自然或合理公开任务流中确实有非零、非个例的低频高后果记忆；
- 常见 recency/frequency/relevance/value 方法会把其中一部分排到淘汰端；
- 删除这些条目造成的损失显著高于普通低分条目；
- 结论不是先按 PREEMPT 规则人工构造样本、再用同一规则证明自己。

本轮只给出文献层面的必要性判断，没有构造样本或提出具体实验方案。

## 6. 内部记忆与外部记忆

### 6.1 操作性定义

**[文献事实]** 近期综述把 external memory 定义为模型参数/内部状态之外、可显式读写和跨会话更新的存储；internal memory 则直接编码在模型架构中，包括参数知识以及推理时工作状态。[A Survey of Agent Memory in the Second Half](https://arxiv.org/abs/2602.06052)

在本项目中可进一步采用下列操作性边界：

| 类型 | 典型载体 | 条目可寻址 | 明确删除 | 明确恢复 | 主要难点 |
|---|---|---:|---:|---:|---|
| 参数记忆 | 模型权重、adapter | 弱 | 难 | 难 | 与 unlearning/持续学习混杂 |
| latent/recurrent memory | learned state、neural memory | 弱 | 局部可控 | 难 | 缺少语义条目和可解释后果 |
| working/context memory | prompt tokens、消息、KV cache | 中 | 可 | 若有外部副本则可 | token 不是稳定的语义 memory unit |
| 外部持久记忆 | 文本、向量库、图、SQL、skills/notes | 强 | 可 | 可设计为可逆 | 最容易做条目级干预与审计 |

### 6.2 对 PREEMPT-Mem 的建议

**[综合判断] 主研究对象建议限定为外部持久 episodic/semantic memory records；工作上下文只作为对照或下游读取层。**

理由：

- 可为每条记忆赋稳定 ID，执行 retain/delete/recover 并记录 provenance；
- 容量、字节数、条目数和恢复成本可直接测量；
- Mem0、A-MEM、MemoryBank、TraceRetain、Xiong 等提供可复用的外部记忆接口和基线；
- 条目级 remove-one replay 的因果语义更清晰；
- 避免把参数 unlearning、KV compression 和 Agent Memory governance 三个问题混合；
- 公开长期对话、Agent 轨迹和 memory benchmarks 多数可以被转换为外部记录。

**[待验证]** 是否纳入 procedural memories（技能、工作流、反思）应在数据/系统调查后决定。它们可能比简单事实更容易造成高后果，但条目间依赖更强，删除归因也更难。

## 7. 与 PREEMPT-Mem 最接近的工作及差异

| 近邻 | 已覆盖的核心能力 | 与 PREEMPT-Mem 的实质差异 | 碰撞风险 |
|---|---|---|---|
| [Learning What to Remember](https://arxiv.org/abs/2606.12945) | 多因素 learned value；未来盲查询下 retention | gold-evidence retention 代理，不是删除后任务严重度；未专门定义 rare-critical | 很高 |
| [TraceRetain](https://arxiv.org/abs/2606.29178) | 固定容量、特征化 retention、最低分 eviction；明确提 rare-important | observed utility/访问特征；无两轴定义、尾部评测或条目反事实 | 很高 |
| [How Memory Management Impacts LLM Agents](https://aclanthology.org/2026.acl-long.27/) | 直接 deletion；用真实后续 utility | 回顾性多次使用均值；低频条目缺标签，periodic rule 仍可能删除 | 很高 |
| [CURATOR](https://arxiv.org/abs/2606.25115) | 净价值/字节、预算淘汰、平均边际 inclusion utility | value 乘近期查询 propensity，可能压低罕见需求；不是严重度尾部 | 很高 |
| [MemAudit](https://arxiv.org/abs/2605.23723) | 单条 remove-and-replay 的因果影响；harm scorer | 有害行为发生后定位并删除有害记忆；不是删除前保护有益记忆 | 很高但方向互补 |
| [ACON](https://arxiv.org/abs/2510.00615) | 用“完整上下文成功、压缩上下文失败”的轨迹对修复压缩策略 | 全局/离线 guideline 更新，不对候选记忆在线逐条验证 | 中高 |
| [Memory-R1](https://aclanthology.org/2026.acl-long.583/) / [AgeMem](https://aclanthology.org/2026.acl-long.981/) | 学习显式 DELETE/SUMMARY 等动作；任务 reward | 轨迹级/平均任务奖励；无 future-need × severity 分解 | 中高 |
| [A-MAC](https://arxiv.org/abs/2603.04549) | 写入时预测 future utility、confidence、novelty | admission 而非 eviction；主观预测而非删除反事实 | 中 |
| [FadeMem](https://arxiv.org/abs/2601.18642) | 访问、相关性、近期性的自适应遗忘；critical-fact retention | critical 类别预设，低访问仍被压分，无严重后果验证 | 中 |
| [MAGE](https://arxiv.org/abs/2605.03228) | security-critical context 与动作前风险评估 | shadow memory 安全防护，不做普通记忆池预算删除 | 中 |

最需要避免的错误 novelty 表述：

- “首次研究 memory importance/value”——错误；
- “首次用未来效用决定记忆保留”——高度危险；
- “首次学习 memory deletion”——错误；
- “首次对记忆做 counterfactual removal”——MemAudit 已直接做到；
- “首次提出 rare but important memory”——错误。

## 8. 当前可能的创新空间（暂定，不是已证实贡献）

### 8.1 从一般效用转向条件严重度

**[综合判断]** 多数方法估计平均有用性或相关性。PREEMPT-Mem 可以专注于：当该记忆真正被需要时，缺失会导致多严重的后果。这样可解释为什么低需求概率不应自动抵消极高严重度。

### 8.2 从事后归因转向删除前保护

**[综合判断]** MemAudit 已经建立了条目级反事实删除，但它从“有害事件已发生、找出有害记忆并删除”出发。PREEMPT-Mem 可以研究相反方向：“在删除有益记忆前，识别缺失会不会造成严重失败”。两者可共享 replay 思想，但问题目标、候选集和错误代价不同。

### 8.3 专门评估 rare × critical 尾部

**[综合判断]** 现有工作大多报告平均 F1、QA accuracy、success rate 或 memory size。PREEMPT-Mem 若能在自然/合理任务流中单独报告低频高后果区域，并证明常用策略在该区域失效，会比再提出一个 composite importance score 更有区分度。

### 8.4 可恢复删除与严重工具后果

**[综合判断]** 外部条目可以引入 tombstone/archive 恢复语义，比较 retain、delete 和 recover。评价也可从一般回答错误扩展到不可逆操作、错误权限使用或严重任务失败。此处只是研究空间；本轮没有设计机制或 benchmark。

### 8.5 选择性验证而非全量昂贵评估

**[综合判断]** A-MAC 已证明便宜、可解释的代理信号可用于 admission；MemAudit 证明 replay 可做条目级因果审计。PREEMPT-Mem 可能把两者组合为“少量候选上的删除前验证”，但不能把“分两阶段”本身当作 novelty，必须证明候选筛选对 rare-critical 的召回和成本收益。

## 9. 尚未确定的问题

### 9.1 概念问题

- **[待验证] memory unit 是单条事实、一次事件、轨迹、反思还是 procedural skill？** 单元不同会改变 rarity、删除和反事实归因。
- **[待验证] rarity 的分母是什么？** 单个用户、单个 Agent 生命周期、同类任务流还是总体 benchmark。
- **[待验证] 低访问来自真实低需求，还是检索器漏召回？** 若不拆开，会把 retrieval failure 错当 rarity。
- **[待验证] criticality 使用最坏后果、条件期望、上分位数还是等级 rubric？**
- **[待验证] 多条记忆互补、冗余或协同导致的交互效应如何处理？** remove-one 可能低估组合依赖。
- **[待验证] “恢复”是立即从 archive 回滚、重新检索原文，还是在失败后补救？** 三者风险语义不同。

### 9.2 实证与评价问题

- **[待验证]** 公开数据中 rare-critical 是否自然存在，比例是否足以支持统计比较。
- **[待验证]** 高后果事件能否用可复现、不会造成真实外部伤害的模拟环境评价。
- **[待验证]** LLM judge/self-consistency 是否能可靠区分一般错误和严重失败。
- **[待验证]** 如何同时测量 false protection（保留过多）与 catastrophic deletion（误删关键条目）。
- **[待验证]** 面对新分布、长时间未出现的需求和个体化约束，过去访问统计能否外推。

### 9.3 Novelty 风险

- 2026 年 Agent Memory 发展很快，多个核心近邻仍是预印本或 workshop 论文；正式投稿前必须持续更新检索。
- 当前最危险的重合是 learned future value、budgeted eviction 和 counterfactual memory influence，而不是传统 recency/LRU。
- 若最终只做一个 LLM importance prompt 加权或简单 risk score，差异不足。

## 10. 下一阶段建议：只列调查任务，不在本轮执行

建议下一阶段仍以“确认问题和证据载体”为主，按以下顺序推进：

1. **官方代码核验。** 优先检查 MemGPT/Letta 的 paging 与恢复语义、Mem0 的 DELETE/invalidation、Xiong 等的 deletion 实现、Memory-R1/AgeMem 的动作与 reward、MemAudit 的 replay/harm scorer、TraceRetain 和 Learning What to Remember 的特征/评价代码、ACON 的 failure-pair 构造。
2. **公开数据与 benchmark 适用性审计。** 对 LongMemEval、LoCoMo、ALFWorld、AppWorld/OfficeBench、WebShop、memory poisoning/long-horizon safety 数据逐项判断：memory unit、可删除性、可恢复性、未来任务、后果严重度和自然 rare-critical 证据。
3. **现象存在性证据方案。** 比较文献证据、真实公开轨迹统计、案例审计和 delete/retain 对照分别能提供什么；先避免人为定义和筛选同源的循环论证。
4. **收紧最终研究问题。** 在外部 episodic/semantic records 范围内，决定是否把工具操作/安全任务作为主要高后果场景，是否包含 procedural memories。
5. **持续查新。** 对 “prospective memory deletion risk”“counterfactual retention”“tail-risk memory eviction”“safety-critical agent memory” 做月度更新，重点关注 2026 下半年和 ICLR 2027 投稿前公开工作。

本报告到此停止。没有进入数据集构造、FMEA 方法设计或代码实现。

## 11. 核验过的主要来源

### 综述与概念

- [Cognitive Architectures for Language Agents（TMLR 2024）](https://openreview.net/forum?id=1i6ZCyf1QJ)
- [A Survey on the Memory Mechanism of Large Language Model-based Agents（TOIS 2025）](https://doi.org/10.1145/3748302)
- [Memory in the Age of AI Agents（arXiv:2512.13564）](https://arxiv.org/html/2512.13564)
- [A Survey of Agent Memory in the Second Half（arXiv:2602.06052；TMLR Survey Certification）](https://arxiv.org/abs/2602.06052)

### 代表性系统与 benchmark

- [Generative Agents（UIST 2023）](https://dl.acm.org/doi/10.1145/3586183.3606763)
- [Reflexion（NeurIPS 2023）](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)
- [MemGPT（arXiv:2310.08560）](https://arxiv.org/abs/2310.08560)
- [MemoryBank（AAAI 2024）](https://ojs.aaai.org/index.php/AAAI/article/view/29946)
- [ExpeL（AAAI 2024）](https://ojs.aaai.org/index.php/AAAI/article/view/29936)
- [ReadAgent（ICML 2024）](https://proceedings.mlr.press/v235/lee24c.html)
- [LoCoMo（ACL 2024）](https://aclanthology.org/2024.acl-long.747/)
- [LongMemEval（ICLR 2025）](https://openreview.net/forum?id=pZiyCaVuti)
- [A-MEM（NeurIPS 2025）](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html)
- [Mem0（arXiv:2504.19413）](https://arxiv.org/abs/2504.19413)
- [LUFY（Dialogue & Discourse 2025）](https://aclanthology.org/2025.dnd-16.12/)
- [HiAgent（ACL 2025）](https://aclanthology.org/2025.acl-long.1575/)

### 保留、删除、未来价值与反事实近邻

- [ACON（arXiv:2510.00615）](https://arxiv.org/abs/2510.00615)
- [Adaptive Memory Admission Control / A-MAC（arXiv:2603.04549）](https://arxiv.org/abs/2603.04549)
- [FadeMem（arXiv:2601.18642）](https://arxiv.org/abs/2601.18642)
- [Learning What to Remember（arXiv:2606.12945）](https://arxiv.org/abs/2606.12945)
- [Selective Memory Retention / TraceRetain（arXiv:2606.29178）](https://arxiv.org/abs/2606.29178)
- [How Memory Management Impacts LLM Agents（ACL 2026）](https://aclanthology.org/2026.acl-long.27/)
- [Memory-R1（ACL 2026）](https://aclanthology.org/2026.acl-long.583/)
- [Agentic Memory / AgeMem（ACL 2026）](https://aclanthology.org/2026.acl-long.981/)
- [Memory as Action（Findings ACL 2026）](https://aclanthology.org/2026.findings-acl.956/)
- [RecMem（Findings ACL 2026）](https://aclanthology.org/2026.findings-acl.1619/)
- [Forget to Improve / CURATOR（arXiv:2606.25115）](https://arxiv.org/abs/2606.25115)
- [MemAudit（arXiv:2605.23723）](https://arxiv.org/abs/2605.23723)
- [MAGE（arXiv:2605.03228）](https://arxiv.org/abs/2605.03228)
