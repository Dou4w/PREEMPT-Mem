# PREEMPT-Mem：第二步数据、源码与现象验证审计

> 审计日期：2026-08-27  
> 对应指令：`ICLR2027-PREEMPT-Mem_新项目续研指令_v1.2.md`  
> 前置材料：`PREEMPT-Mem_第一步_文献调查与概念梳理.md`、`preempt可行性报告_v1.1.md`、`论文完整story_v1.1.md`  
> 本报告边界：只完成第二步审计与下一阶段 Pilot 设计；未下载大规模数据、未实现 PREEMPT-Mem、未运行 GPU 或正式实验。

## 0. 结论先行

1. **未发现核心碰撞。** 在本轮能够直接核验的论文与官方源码中，没有工作同时完成：**未见真实 trigger 时主动生成 Future Decision Witness、对单条外部 memory 做可执行 Full/Evicted/Restore 干预、并把验证结果用于真实容量约束下的 retention 决策**。这是当前仍可 defend 的核心组合。[综合判断]
2. **多个宽泛 claim 必须收窄。** “未来风险预测”“删除/恢复反事实”“罕见但重要记忆”“主动安全审计”“FMEA 辅助风险分析”都已有直接近邻，不能分别声称首次。PREEMPT-Mem 的贡献必须写成上述闭环组合，而不是其中任一单件。[论文直接支持][综合判断]
3. **公开资源足以做最小可行 Pilot，但不存在一套现成 benchmark 同时承担四个角色。** 推荐用 AppWorld 的 state checkpoint、可执行 API 与数据库状态测试构成因果/严重后果主轨；用 LongMemEval-V2 的真实感 trajectory、workflow、gotcha 与 premise 记录构成自然记忆与外部有效性辅轨；ConstraintRot 只作为失败类型和确定性违规判定模板。[源码直接支持][数据卡直接支持][综合判断]
4. **rare 与 critical 必须独立测量。** rarity 用冻结的未来任务流中“gold dependency/真实需求”的基率，而不是历史 retrieval 次数；criticality 用需求发生条件下、由 Full→Evicted 且 Restore 可救回的严重损失。这样可避免把 retrieval failure 当 rarity，也避免用同一 importance 规则定义并证明 rare-critical。[综合判断]
5. **FMEA 结论：修改。** 保留 failure mode、effect/severity、可检测性/证据缺口与 witness-feasibility 结构；删除传统 `Occurrence × Severity × Detectability` 的 RPN 乘积和 FMEA novelty 表述。低 occurrence 正是本项目要保护的对象，直接相乘会系统性压低 rare-critical 候选。[论文直接支持][综合判断][待 Pilot 验证]
6. **Pilot 应先形成 80 条候选、冻结未来任务流，再按测得标签抽取 40 条（四象限各 10 条），而不是先按人工规则写 40 个“正确答案”。** 这一步是避免循环论证的关键。[综合判断]

### 0.1 证据标签

- **[论文直接支持]**：论文正文、附录或官方出版页直接陈述。
- **[源码直接支持]**：官方仓库中的接口、脚本、README 或许可证直接支持。
- **[数据卡直接支持]**：官方数据卡/数据文件说明直接支持。
- **[指定材料转述]**：仅来自本项目指定的前置报告，本轮未能独立访问原文。
- **[综合判断]**：由多个直接证据和本项目约束推出，不冒充论文原话。
- **[待 Pilot 验证]**：当前只是可检验假设，不写成已证实结论。

---

## 1. 六个原始问题的最新状态

| 原始问题 | 第二步后的状态 | 本轮完成的实质工作 | 仍未完成/证据边界 |
|---|---|---|---|
| 1. Agent Memory 文献、rare、importance、criticality 与源码 | **源码与操作定义审计基本完成** | 核验 10 组最强近邻的对象、删除语义、trigger、干预、目标和公开实现；给出 rarity、criticality、effective eviction、CF loss、witness 的可执行定义 | `What Eviction Destroys` 的 OpenReview 原文/API 被挑战验证阻断；CURATOR、DeMem、TraceRetain 等未定位到官方实现；阈值仍需 Pilot 校准 |
| 2. 是否需要证明 rare-but-critical memory | **问题成立，实证方案就绪，尚无结果** | 形成独立分母、四象限、冻结任务流、remove-one/group intervention、Full/Evicted/Restore 与反循环论证协议 | 未运行 30–50 条 Pilot，不能声称现象比例、显著性或基线失败率 |
| 3. 研究内部还是外部记忆 | **完成** | 主对象固定为显式、可寻址、可干预的外部 episodic/semantic record；定义 active context、production store 与隔离 audit archive；规定 effective eviction 和 restore | Pilot 需用代码验证不存在 prompt、summary、cache、duplicate 等旁路泄漏 |
| 4. 没有公司日志时的数据与 benchmark | **可进入 Pilot** | 审计 LongMemEval-V2、ConstraintRot、LongMemEval、LoCoMo、MemoryAgentBench、AppWorld、ALFWorld、WebShop；拆分四种资源角色；确定主/备组合 | 没有单一现成 benchmark 同时满足自然历史、未见 trigger、真实执行、单条干预、严重后果；仍需小型适配器和人工盲标 |
| 5. 寻找细微视角差异、避免过度否定 | **核心组合保留，claim 已收窄** | 未发现完整三件套；明确 CURATOR/Learning/TraceRetain 覆盖 retention，MemAudit/指定材料覆盖反事实，Governance Decay 与主动安全工作覆盖风险/删除后果 | 不能声称“首个 proactive risk prediction”“首个 counterfactual memory audit”“首个 rare-critical 观察”或“首个用 FMEA 的 LLM 方法” |
| 6. FMEA 能否用于 Agent Memory | **修改** | 核验 LLM 辅助 FMEA 和 Agent 主动风险预测已有工作；确定只保留结构化 failure-mode/severity/evidence-gap/witness-feasibility，不用传统 RPN | 是否优于简单 severity-aware triage、是否提高有效 witness 率与同预算命中率，必须做消融 |

总体门控结论：**可以进入第三步 Pilot 实现，但不能跳过冻结数据 manifest、泄漏检查和 AppWorld 三分支 smoke test。**[综合判断]

---

## 2. 最强近邻论文与源码比较

### 2.1 比较口径

本节只回答续研指令要求的八个问题：memory unit；是否真实 deletion/effective eviction；价值证据来源；trigger 是否给定；是否运行 Agent/工具；是否单条 remove/restore；结果用于何种时点和目标；是否同时考虑 memory budget 与 counterfactual testing cost。

记号：`D`=真实删除/有效淘汰，`F`=仅检索/压缩/分区，`R1`=逐条 remove，`RS`=restore，`Exec`=真实或沙箱工具执行。

### 2.2 核心比较表

| 工作 | Memory unit 与操作 | 价值证据/trigger | Exec 与单条干预 | 决策时点和用途 | Budget / CF cost | 官方实现审计 | 与 PREEMPT-Mem 的结论 |
|---|---|---|---|---|---|---|---|
| [CURATOR](https://arxiv.org/html/2606.25115) | 外部 experience entry；按 `(预测价值−写入/共享成本)/bytes` 形成受预算 resident set，属于 `D/effective eviction`，不是单纯 query filtering | retrieval propensity 来自近期 query sketch，helpfulness 来自 self-consistency 边际效用；未来真实 trigger 未给定，也未主动生成任务 | 有 Agent 执行；未见 `R1+RS` 的逐条三分支 | 删除前、预算化保留有益经验 | 明确 byte/RAM/energy budget；未优化逐条 CF testing budget | [论文直接支持]；截至审计日未定位到论文链接的官方 repo，复现状态记为“论文可读、实现未核” | 强 retention 邻居；近期 propensity 可能压低 rare need，但无主动 witness 与可执行 remove/restore |
| [DeMem](https://arxiv.org/html/2605.10870) | history+当前 query 被映射到 K 个 runtime memory state/slot；主要是上下文分区/聚类与按冲突细化，属 `F`，不是持久记录逐条删除 | 当前 query 已观察；决策冲突由已发生 reward/certification 触发 | 运行任务/QA流程；无外部 record 的 `R1+RS` | query-time contextual decision abstraction | 有 K-state 压缩预算；无 CF testing budget | [论文直接支持]；未定位官方 repo | 当前 query 与动态分区邻居，不是 pre-trigger retention |
| [What Eviction Destroys](https://openreview.net/forum?id=8rOh73WoJh) | 指定材料称：针对给定问题做 per-item restore-counterfactual eviction audit | trigger 已给定 | 指定材料称有逐条 remove/restore | 事后/给定任务的 eviction audit | 未能独立核验 | OpenReview 页面、PDF 与 API 均触发 challenge，标题也未被公共索引；本轮不得给出“论文直证” | **证据待补**。按指定材料仍是最接近 Restore 的邻居，但差异暂定为“given trigger vs. unseen future witness”[指定材料转述] |
| [Governance Decay / ConstraintRot](https://arxiv.org/html/2606.22528) | session 内一条 policy/constraint 经 context compaction 被删除；是 active-context eviction，不是外部 persistent store 的逐条容量管理 | 同一个 prohibited trigger 明确给定；比较 full policy、compacted、absent、pinned | 输出 `send_email/db_exec/read_file/disclose/purchase` 终端工具调用并用参数解析判违规；不是完整外部环境执行；无逐条 archive restore | 证明 compaction 后治理约束丢失，并提出 pinning | 有 token compaction budget；无候选 CF testing budget | 论文称 scenarios/prompts/conditions/grader code 已发布，但正文无 repo 链接，本轮未定位发布位置；因此“发布声明已核、代码位置未核” | 删除后严重后果和确定性 evaluator 模板很强；trigger 已给定、对象和干预层不同 |
| [MemAudit](https://arxiv.org/html/2605.23723) | 外部文本 memory item；对已检索条目逐条 remove-and-replay，计算 causal memory influence，再删除疑似投毒项 | harmful event 已发生且 `(q*, y*, R*)` 已知；证据是删除后 harm 是否下降 | 有 Agent replay 与 `R1`；未见 restore rescue leg | 事后定位并删除有害 memory | 无容量 retention budget；CF cost 是审计开销但非联立优化 | [论文直接支持]；论文 checklist 表示无公开代码/数据匿名发布 | 条目级因果最强近邻；方向相反：事后删有害项，而非事前保护有益项 |
| [Learning What to Remember](https://arxiv.org/html/2606.12945) / [repo](https://github.com/zhibao-dev/Learning-Multi-Factor-Memory) | 外部 evidence item；学习多因素 scalar，固定 keep fraction 下 retain/forget | blind retention 中未来 query 隐藏；监督目标是 LongMemEval gold-evidence retention | 不执行严重工具行为；无 `R1+RS`，repo 的 forget list 是选择结果/审计输出 | 删除前 learned retention | 固定 memory budget；无可执行 CF cost | MIT；CPU-only；无 API；479-case blind experiment、keep fraction 0.30，可直接复现[源码直接支持] | **最适合 Pilot 的 learned retention baseline**；但标签是 evidence retention，不是条件严重损失 |
| [TraceRetain](https://arxiv.org/abs/2606.29178) | 外部 trajectory summary；容量超过 K 时淘汰最低多特征得分项，属真实 bounded retention | 历史成功/失败、年龄、访问、冗余、observed utility、相似度；ALFWorld 当前任务已给定 | 有 ALFWorld 执行；无 `R1+RS` | 删除前、保留有用经验 | 有 K；无 counterfactual testing cost | [论文直接支持]；截至审计日未定位官方维护 repo | 直接覆盖 rare-but-important 措辞和多因素淘汰；未给 rarity×conditional severity 或 future witness |
| [Memory-R1](https://aclanthology.org/2026.acl-long.583/) / [repo](https://github.com/yansikuan/memory-r1) | 外部 bank；Manager 选择 ADD/UPDATE/DELETE/NOOP，DELETE 是真实 memory action | 当前 QA/任务 reward；未来 query 已进入轨迹后给 outcome signal | 概念上运行 memory agent；无候选 `R1+RS` | 用 RL 学管理操作，优化平均 QA outcome | 有 memory 管理但无显式 CF testing budget | Apache-2.0；官方 repo 当前 README 明示 “Code coming soon”，主体实现不可复现[源码直接支持] | 学习删除动作近邻，非预触发条目级风险验证 |
| [AgeMem](https://aclanthology.org/2026.acl-long.981/) / [repo](https://github.com/y1y5/AgeMem) | LTM/STM；工具含 add/update/delete_memory、summary/filter，按 ID 可删除 | 当前 HotpotQA/任务 reward 与多阶段 GRPO | 运行 memory tools；无 `R1+RS` | 端到端学习记忆管理 | 训练成本高；未联立 CF test cost | 训练/eval 与 AgentScope demo 已公开；需 Python 3.10、Qwen2.5-7B、HotpotQA、DashScope；仓库未识别到明确 LICENSE 文件[源码直接支持] | 工程接口可借鉴，但不适合首个小 Pilot 的公平 baseline |
| [LongMemEval-V2 / AgentRunbook](https://arxiv.org/html/2605.12493) / [repo](https://github.com/xiaowu0162/LongMemEval-V2) | 完整 web/enterprise trajectory 输入，memory backend 产出 evidence context；query 阶段有 token cap，但不是源条目删除 | 451 个独立人工问题；query 已给定；backend 不接收 question ID/gold/evaluator metadata | 无原环境 reset/replay；固定 reader 回答，结构化答案或 LLM judge | 评估经验记忆与 accuracy-latency frontier | 有 query context token budget/latency；无删除 CF cost | 代码/数据 Apache-2.0；官方 harness、schema、下载/校验和 baselines 完整[源码直接支持][数据卡直接支持] | 最好的自然 trajectory/memory-pool 与 blind-query资源；不是可执行因果环境 |

### 2.3 是否构成核心碰撞

**答案：在本轮可直接核验的证据范围内，没有。**[综合判断]

已有能力是分散的：

- CURATOR、Learning What to Remember、TraceRetain、Memory-R1/AgeMem 做预算 retention 或 memory action；
- MemAudit 和本轮受阻的 `What Eviction Destroys` 做条目反事实或 restore 邻近操作；
- Governance Decay 证明删掉/压掉一条约束可产生严重工具后果；
- LongMemEval-V2 提供独立未来 query 与真实感经验轨迹；
- [TRACES](https://arxiv.org/abs/2605.27690)、[Pro2Guard/ProbGuard](https://arxiv.org/abs/2508.00500)、[Recast](https://arxiv.org/abs/2607.26820) 和 [SafeMCP](https://aclanthology.org/2026.acl-long.522/) 已覆盖不同形式的 proactive trajectory-risk prediction、future unsafe-state estimation 或 pre-action tool filtering。[论文直接支持]

但尚未发现一项工作把它们闭合成：

> `unseen-trigger witness generation → executable item-level Full/Evicted/Restore → verified forgetting risk → actual budgeted retention`。

### 2.4 问题分类，而不是把所有相似都视为 Idea 失败

| 分类 | 本轮发现 | 对项目的处理 |
|---|---|---|
| **核心碰撞** | 未发现完整闭环 | 保留核心 Idea；对 `What Eviction Destroys` 保留证据待补标记 |
| **Claim 收窄** | proactive risk、future unsafe state、value-aware retention、remove-one audit、rare-important 都已有 | novelty 只写闭环组合；相关工作中分别承认这些邻居 |
| **实验缺口** | 公开 benchmark 没有独立 rarity×conditional severity 标签；FMEA triage 尚无优势证据；自然记忆与严重工具后果难在同一数据中兼得 | 双轨 Pilot；冻结任务流；加入 random/full CF、simple severity-aware triage 和独立 future trigger |
| **工程风险** | AppWorld 受保护 bundle 与环境安装；LME-V2 全量 7.12 GB；部分 repo 缺失/未发布；模型随机性与三分支成本 | 只用 train/dev 小切片；不下载 screenshot 全量；先做 3-task smoke；记录版本与成本 |
| **措辞风险** | “首次 rare-critical/FMEA/counterfactual/proactive”均不可用 | 使用“pre-trigger executable counterfactual supervision for retention”限定语，并写成审计范围内结论 |

---

## 3. 推荐操作定义

### 3.1 Memory unit

一条可审计 memory record 定义为：

```text
m = {
  memory_id, content, memory_type,
  source_episode, provenance, timestamp, validity_interval,
  permissions, canonical_fact_id, dependency_ids,
  size_tokens, embedding/index_version
}
```

要求：

1. `memory_id` 稳定且可按 ID 删除/恢复；
2. 一条记录尽量只表达一个可判定的事实、约束、workflow step 或 gotcha；原始 trajectory slice 可以作为 provenance，但不可把多个独立事实揉成不可归因的大摘要；
3. agent-visible 字段与 evaluator-only 字段分离，`gold_dependency`、criticality、future trigger ID、答案和 severity 标签不得进入生产索引；
4. 同义副本通过 `canonical_fact_id` 标记，依赖/协同通过 `dependency_ids` 标记；
5. 本项目主对象只包括显式、非参数化、跨回合可持久、可寻址、可干预的 episodic/semantic records，不把模型权重、KV cache 或纯 prompt token 当主对象。[综合判断]

### 3.2 Effective eviction

对生产 memory set `M`，在固定检索预算、索引版本、权限和 agent prompt 下，`Evict(m)` 必须使 `m`：

- 不在 production store、active prompt、summary、retrieval cache、tool cache 和可访问 archive 中；
- 不能通过同义副本或派生摘要泄漏其决策性内容；
- 仍可存在于**与 agent 隔离**的 immutable audit archive 中，仅供实验控制器 Restore；
- 除 `m` 的可用性外，不改变环境初始状态、其他 memories、模型、工具权限和随机种子。

因此 retrieval top-k 未命中不等于 eviction；把记录移到 agent 仍可查询的 archive 也不等于 eviction。[综合判断]

### 3.3 Rarity

设冻结的未来任务流为 `T={t_1,...,t_N}`，对应一个具体 agent 生命周期/用户/定制环境。定义与系统检索无关的需求指示：

```math
Need(m,t)=1
```

当且仅当独立 gold dependency 标注或环境任务规范表明：完成 `t` 的正确决策需要 `m` 所表达的信息，而不是因为某个 baseline 恰好检索了它。

```math
RarityRate(m;T)=\frac{\sum_t Need(m,t)}{|T|}.
```

推荐分母：**单个 agent 在一个冻结、可复现的用户/环境任务流中的未来机会数**；跨用户结果先按生命周期计算，再报告宏平均，不把所有 benchmark 样本直接混成一个分母。[综合判断]

Pilot 预注册阈值：

- `rare`：在 `N=40` 个隐藏 future tasks 中需要次数 `≤2`（`≤5%`）；
- `frequent`：需要次数 `≥6`（`≥15%`）；
- 中间区域只用于连续分析，不强塞入四象限。

若实际任务 bank 不是 40 条，保持 5%/15% 比例并向保守方向取整。阈值在查看 retention 结果前冻结。[综合判断]

### 3.4 历史低 retrieval 与真实低需求的分离

同时记录两个量：

```math
NeedRate(m)=\Pr[Need(m,t)=1],\qquad RetrievalRate(m)=\Pr[Retrieved(m,t)=1].
```

并报告 `retrieval miss = Need=1 ∧ Retrieved=0`。rarity 只由 `NeedRate` 决定；历史 retrieval count 只能作为 baseline feature。若没有 gold dependency，就只能标为“observed-demand proxy”，不得写成真实 rarity。[综合判断]

### 3.5 Conditional criticality

先给每个 executable task 定义与 memory 内容无关的后果等级 `S(t,outcome)`：

| 等级 | 操作定义 |
|---:|---|
| 0 | 行为与 Full 等价，无 evaluator 差异 |
| 1 | 仅效率、token、冗余调用或可忽略格式损失 |
| 2 | 可恢复的部分任务失败/普通错误答案，无禁止状态改变 |
| 3 | 完整任务失败、关键约束违反、或本 episode 内不可自行恢复的错误状态改变 |
| 4 | 模拟的隐私泄漏、越权发送/购买、破坏性数据库操作、安全控制关闭等预定义 severe effect |

对 `Need(m,t)=1` 的任务，用配对 reset/replay 定义：

```math
\Delta_F(m,t,s)=L(Y_{Evicted})-L(Y_{Full}),
```

其中 `L` 不强制压成单一任意加权分数；至少分开保存 `severe_violation`、task-goal completion/测试通过率、普通成功率和成本。定义：

```math
Critical(m)=1
```

当 `Need=1` 的任务上，`Evicted` 相对 `Full` 在至少 2/3 配对运行中新增等级 `S≥3` 的后果，且 Restore 通过下述 rescue gate。连续量同时报告 `Pr(severe failure | Need=1, Evicted)`、中位数 `Δ task score` 与上尾损失；不只报告平均准确率。[综合判断]

### 3.6 Rare-but-critical region

```math
RBC(m)=\mathbb{1}[RarityRate(m)\le 0.05]\cdot\mathbb{1}[Critical(m)=1].
```

四象限标签由冻结 future task stream 与独立 evaluator **事后计算**，不作为构造 memory 文本或生成 future witness 的输入。主分析同时保留连续 rarity 与 severity/effect，避免阈值挑选造成结论依赖。[综合判断]

### 3.7 Counterfactual forgetting loss 与 Restore

每次试验从同一个环境 checkpoint、同一个 memory snapshot 和同一个 seed 派生：

- `Full`：完整 production store；
- `Evicted`：只让目标 `m` effective-evicted；
- `Restore`：从隔离 audit archive 恢复同一 `memory_id`、原文、metadata 和索引配置。

主要 effect estimate 是配对 `Full−Evicted`；Restore 是**干预特异性和环境漂移的 rescue/negative control**，不是为了制造第三个独立“效果”。有效 run 需满足：

1. `Full` 与 `Restore` 的 severe flag 完全一致；
2. 对确定性 evaluator，任务测试向量一致；对 stochastic agent，分数差在预注册容差内；
3. `Evicted` 的目标内容在 retrieval trace、prompt trace、summary/cache 中均不可见；
4. 若 `Full` 与 `Restore` 不一致，该 run 记为环境/索引不稳定，不进入主因果估计。[综合判断]

### 3.8 冗余、依赖和协同

remove-one 只估计 `m` 在当前 `M\{m}` 条件下的**边际影响**。若存在同义备份，单条效果为零并不代表信息不重要。Pilot 采用三层处理：

1. 先以 `canonical_fact_id` 合并显式同义副本；
2. 对已知 `dependency_ids` 同时记录单条删除与最小 group deletion；
3. 将条目标为 `solo-identifiable`、`redundant` 或 `synergistic`，主 rare-critical recall 先在 `solo-identifiable` 上报告，后两类做单独错误分析。

不在 40 条 Pilot 中引入全量 Shapley 估计；只有单条结果与任务依赖冲突时才做最小二阶 group test。[综合判断]

### 3.9 有效的 Future Decision Witness

一个 witness `w(m)` 必须包含：

```text
{instruction, initial_state/checkpoint, allowed_tools,
 expected decision boundary, executable evaluator,
 predicted failure mode, severity hypothesis}
```

并同时满足：

1. 在真实 hidden future trigger 到达前，由 `m + 环境/API schema + 历史非未来信息` 生成；
2. 生成器看不到 hidden task、question ID、gold answer、gold dependency、criticality 和 evaluator 私有标签；
3. 能在同一 checkpoint 上执行 Full/Evicted/Restore；
4. evaluator 优先确定性，能够判任务完成和 prohibited effect；
5. Full/Restore 可完成或安全，Evicted 出现预期方向差异，才称为 `validated witness`；
6. witness 上的结果只用于 retention；最终 claim 必须在**独立 hidden future task** 上复现，不能把生成 witness 本身当最终测试集。[综合判断]

---

## 4. Rare-critical 现象存在性实验方案

### 4.1 要证明的最小命题

本阶段不证明 rare-critical 在所有真实 Agent 中普遍存在，只检验四个有界命题：

1. 冻结、可复现的任务流中，至少存在多个、跨 failure mode 的 `RBC(m)=1` records；
2. LRU/LFU、generic LLM importance 和 learned multi-factor retention 会把其中一部分排入淘汰端；
3. 对这些 records 做 effective eviction 后，severe failure/任务损失显著高于同样低基率但 non-critical 的 records；
4. 标签不是由 PREEMPT/FMEA 规则生成后再用同一规则“验证”。

### 4.2 数据形成顺序：先候选、后冻结、再测标签

1. 从 AppWorld train/dev 的既有任务、初始状态、历史执行轨迹/官方可下载 baseline outputs 中抽取 **80 条候选 records**，覆盖 constraint、workflow、gotcha、dynamic state、preference/permission 和普通事实；不查看 future task 的依赖标签。
2. 独立建立 **40 条 hidden future task bank**。优先使用 disjoint task variation/不同 task ID；必要的新任务只由不了解 retention scorer 的构造者编写，并在任何 witness generation 前冻结 hash。
3. 两名独立标注者只依据 task specification、state tests 与 provenance 标 `Need(m,t)`；分歧由第三人裁决。标注者看不到各 retention baseline 分数。
4. 用 Full/Evicted/Restore 执行确定 criticality；先形成真实标签，再按四象限各选 10 条组成 40-memory Pilot。若某象限不足 8 条，不人工改标签，直接判为“样本形成方案需修改”。
5. 另从 LongMemEval-V2 Small 抽取 16–20 条 trajectory-derived workflow/gotcha/premise records，做自然性和 QA-loss 辅轨；这些不与 AppWorld severe outcome 混成一个比例。[综合判断]

### 4.3 防循环论证与泄漏控制

- 候选来源不是 FMEA/PREEMPT 生成；FMEA 只能排序已有 candidates。
- hidden task bank 在 witness 生成前冻结并保存 hash；generator、triage 和 baselines 均不可读。
- `Need`、severity、gold answer、answer-bearing trajectory label 放在 evaluator-only manifest。
- LongMemEval-V2 官方 harness 已使 backend query 看不到 question ID/gold/evaluator config；PREEMPT 适配器继续额外屏蔽 hidden task 文本。[源码直接支持]
- witness-dev 与 future-test 按 task family 分组拆分，避免同一模板的改写泄漏。
- semantic/LLM importance、learned baseline 和 PREEMPT 使用完全相同的 agent-visible metadata、retention budget 与最终 retrieval top-k。

### 4.4 统计与判定

Pilot 是现象 gate，不做夸张总体推断。报告：

- 四象限实际数量及 95% Wilson interval；
- 每个 baseline 的 RBC retention recall、false protection rate、token budget 使用量；
- `rare-critical` 与 `rare/non-critical` 的 paired eviction severe-failure rate 和 task-test loss；
- 每条 memory 的 Full/Evicted/Restore 原始测试向量与 seed；
- 按 failure-mode family 的 leave-one-family-out 分析，防止结果由单一“外发邮件”模板支配。

最小现象通过条件：

1. 至少 `8` 条 restore-confirmed rare-critical records，且覆盖至少 `3` 个 failure-mode families；
2. 至少一个常见 baseline 在固定 50% token budget 下漏掉 `≥25%` 的 RBC records；
3. RBC 的 Evicted severe-failure rate 比 rare/non-critical 高至少 `20` 个百分点，方向在 leave-one-family-out 中不反转；
4. Full↔Restore 一致率 `≥90%`，且无 memory leakage；
5. 若只满足 1–3 但 Restore 稳定性不足，结论是“环境/实现需修改”，不是现象不存在。

这些阈值是第三步的 go/modify gate，不是最终论文显著性标准。[综合判断]

---

## 5. 数据集、环境、代码与 evaluator 可用性

### 5.1 资源角色必须分开

| 角色 | 本项目需要的内容 | 推荐首选 |
|---|---|---|
| 自然 memory pool | 来自历史交互的事实、workflow、gotcha、动态状态、约束与 provenance | LongMemEval-V2；AppWorld 既有历史轨迹作为同环境候选 |
| Future trigger tasks | 与候选 memory 分离、在 witness 生成时不可见的未来任务 | 冻结的 AppWorld dev/task-variation bank；LME-V2 questions 仅用于 QA 辅轨 |
| 可执行 Agent 环境 | 可 reset/checkpoint/replay，同一任务可跑 Full/Evicted/Restore | AppWorld；备选 ALFWorld text |
| Severe-outcome evaluator | 确定性识别任务失败、越权/违规或错误状态改变 | AppWorld database-state tests + ConstraintRot 风格 prohibited-effect assertions |

### 5.2 逐项可用性表

| 资源 | Memory 来源 | Trigger | 可执行/reset/replay | 删除/恢复 | 严重后果与 evaluator | 可获取性、license、成本 | 30–50 条适配判断 |
|---|---|---|---|---|---|---|---|
| [LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2) / [data](https://huggingface.co/datasets/xiaowu0162/longmemeval-v2) | 1,870 条 web/enterprise task trajectories；含 state、workflow、gotcha、premise；451 人工问题 | 独立 QA query，但在正式 query 时已给定 | 无原 WebArena/WorkArena reset/replay；固定 reader | 可在自建 store 单条删/恢复，但官方 benchmark 不提供环境因果干预 | structured answer 可规范化匹配，free-form 依赖 LLM judge；无严重工具效果 | Apache-2.0；官方代码/数据；数据卡约 7.12 GB，最大 115M tokens，Small 可局部使用[源码直接支持][数据卡直接支持] | **自然记忆首选，执行主轨不够**；不下载截图全量，只取 schema/JSON 与小切片 |
| [Governance Decay / ConstraintRot](https://arxiv.org/html/2606.22528) | 一条 in-context policy + benign turns | 9 个给定 prohibited triggers | 生成 terminal tool call，非完整外部环境；prompt 可完全重放 | full/compacted/absent/pinned，不是外部 record archive restore | 解析 tool arguments 的确定性 violation；secondary constraint survival 用 LLM judge | 论文称所有 scenario/prompt/grader 已发布，但未给 repo 链接且本轮未定位；许可证/下载位置不明 | **只用作 severe failure taxonomy/evaluator 模板**；若源码仍不可得则小规模 clean-room 实现并明确非官方复现 |
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) / [data](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned) | 多 session 对话事实、时间与偏好；500 questions | 给定 QA query，evidence session label 可见于数据 | 无工具环境/reset | 自建 store 可删/恢复 | 多数依赖 GPT-4o LLM judge，非 severe outcome | repo/data MIT；中小规模；API 成本 | 适合事实/时间 control 和 baseline 调试，不作为 severe 主轨 |
| [LoCoMo](https://github.com/snap-research/locomo) / [paper](https://aclanthology.org/2024.acl-long.747/) | 10 个长对话，QA、event summary | 给定 QA query | 无执行环境 | 自建 store 可删/恢复 | QA/摘要评价，无严重工具效果 | CC BY-NC 4.0；规模小、易取 | 适合低成本 conversational control；样本仅 10 个且许可非商业，非主轨 |
| [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench) / [data](https://huggingface.co/datasets/ai-hyz/MemoryAgentBench) | incremental multi-turn chunks；覆盖 accurate retrieval、TTL、long-range understanding、conflict resolution | 给定 query/任务 | memory-agent harness，但主要是文本任务，不是 resettable tool world | 可适配 store，官方不做逐条 restore CF | 多数 exact/substring match，LongMemEval/InfBench 部分 LLM judge；无 severe tool effect | code/data MIT；HF 约 76.6 MB；需多种 API/memory 方法依赖[源码直接支持][数据卡直接支持] | 适合能力分层与 evaluator 对照；不是第一 Pilot 必需项 |
| [AppWorld](https://github.com/StonyBrookNLP/appworld) / [paper](https://aclanthology.org/2024.acl-long.850/) | 9 个日常 app、457 APIs、约 100 个模拟用户、750 tasks；可从历史任务/轨迹抽取 workflow、state、permission、gotcha | train/dev task 和 task variations；可冻结独立 future bank | `AppWorld(task_id)` 加载独立初始 DB；`save_state/load_state` 可 checkpoint/revert；API 真正改变沙箱数据库 | 外部 memory adapter 可按 ID effective-evict/restore；环境本身支持状态 rescue | robust database-state unit tests 检查 goal 和 collateral damage；可加 forbidden-effect assertions；online/offline evaluation | 公共部分 Apache-2.0；受保护 bundle 亦为 Apache-2.0 加密再分发条件；Python 3.11、Git LFS/数据安装，主要推理可走 API，无需训练 GPU[源码直接支持] | **执行/严重后果主选**；首轮只用 train/dev 与少量 task IDs，先做 3-task smoke |
| [ALFWorld](https://github.com/alfworld/alfworld) | ALFRED/TextWorld 家务轨迹与经验 | held-out game/task instruction | 标准 `env.reset/step`；text-only 可 CPU | 外部 store 可适配 remove/restore | deterministic task score/success；通常只有任务失败，缺少越权/隐私等 severe effect | MIT；Python 3.9+；需下载 PDDL/game files；text-only 成本低[源码直接支持] | **执行备选**；适合复现、但 criticality 只能先定义为关键任务失败 |
| [WebShop](https://github.com/princeton-nlp/WebShop) | 1.18M products、12,087 instructions、少量人类 trajectories | 给定购物 instruction | Gym text env，可 reset/step；small setup 仅 1,000 products | 外部 store 可适配 | scalar reward/goal attribute match；“购买错误”是模拟损失但缺少治理严重度 | MIT；Python 3.8、Java、搜索索引与数据下载；small mode 可用[源码直接支持] | 可做跨环境 robustness；首轮安装成本高于 ALFWorld，列为第二备选 |
| [Learning-Multi-Factor-Memory](https://github.com/zhibao-dev/Learning-Multi-Factor-Memory) | LongMemEval evidence records | blind future query | 非工具环境 | retention selection，无 restore | gold-evidence retention | MIT、CPU、无 API，479 cases | **learned baseline 首选**；移植 scorer 而非把其结果当 PREEMPT 标签 |

### 5.3 数据数量审计中的一个不一致

LongMemEval-V2 论文的 trajectory collection 部分和当前公开数据卡的数量口径并不完全一致：公开数据卡明确写 `1,870 task trajectories`，论文部分描述可对应到较小的最终采集计数。Pilot 应以下载后的 `trajectories.jsonl`、checksums 和 release version 为准，在 manifest 中记录实际条数，不从论文摘要口径反推文件内容。[论文直接支持][数据卡直接支持][综合判断]

---

## 6. 推荐主数据组合与备选组合

### 6.1 主组合：AppWorld 因果主轨 + LongMemEval-V2 自然性辅轨 + ConstraintRot 判定模板

**因果主轨（论文核心证据的最小来源）**

- memory pool：从 AppWorld train/dev 既有任务状态、历史轨迹和 baseline outputs 抽取 80 条外部 records；
- future triggers：冻结且与来源 episode/task family 分离的 40 个 AppWorld dev/task-variation tasks；
- environment：AppWorld `save_state/load_state` 与独立 task initial DB；
- evaluator：AppWorld database-state tests；对 constraint/privacy/spend/destructive classes 增加由 ConstraintRot failure taxonomy 启发的 forbidden-effect assertion；
- intervention：自建 production store、隔离 audit archive 和索引重建，实现单条 Full/Evicted/Restore。

**自然性辅轨（防止主轨变成纯手工规则游戏）**

- 从 LongMemEval-V2 Small 的 trajectory text/notes 抽取 workflow、gotcha、premise、dynamic-state records；
- 用其独立人工 questions 做 blind-query forgetting-loss 与 witness plausibility 检查；
- 只报告 QA/证据损失，不把它称为 severe tool consequence；
- 比较 AppWorld 与 LME-V2 上 risk triage 的候选排序和 witness-valid rate 是否一致。

**为何不是把两轨硬合成一个比例：** LME-V2 的公开 benchmark 不提供原环境 replay，AppWorld 的模拟历史又不等于自然企业日志。将两者分别支撑“真实感 memory pool”和“可执行因果/严重后果”比伪装成单一统一数据更可信。[综合判断]

### 6.2 备选组合：ALFWorld text 因果轨 + LongMemEval/LoCoMo 辅轨

当 AppWorld bundle、许可证解释、安装或 task-state evaluator 在第三步 smoke test 中失败时：

- 用 ALFWorld text-only train trajectories 形成 episodic/workflow records；
- 用 held-out game instances 做 hidden future tasks；
- 通过 `env.reset` 做三分支 replay，task success 作为 criticality；
- 用 LongMemEval 或 LoCoMo 做事实/对话 natural-memory control；
- severe claim 收窄为“关键任务失败”，不声称隐私、财务或治理违规。

该备选的可复现性更好，但论文故事的 severe-outcome 强度更弱；因此只在 AppWorld 主轨不可用时启动。[综合判断]

### 6.3 不推荐的组合

- **仅 LongMemEval-V2：** 有自然 trajectory 和独立问题，但无原环境 execution/reset，无法支撑可执行 severe causal claim。
- **仅 ConstraintRot：** failure/evaluator 清楚，但 trigger 给定、memory 是 in-context constraint、工具调用多为终端输出解析，且代码位置未核。
- **仅 LoCoMo/LongMemEval：** 只能证明 QA forgetting，不足以支持 severe agent failure。
- **直接训练 AgeMem/Memory-R1：** 首个 Pilot 不需要 RL；前者依赖较重且代码许可未明，后者正式代码尚未发布。

---

## 7. 30–50 条 memory Pilot 设计

### 7.1 样本规模与组成

目标是 **40 条主分析 records**，四象限各 10 条；允许最小 32 条（各象限至少 8）和扩展到 48 条（各 12）。

形成流程不是“人为各写 10 条”，而是：

1. 初始 80 条候选；
2. 冻结 40-task future stream；
3. 独立标 `Need` 并执行因果标签；
4. 排除灰区、泄漏和 Restore 不稳定项；
5. 分层抽取 40 条。

建议类型配额只约束候选覆盖，不决定四象限：constraint/permission 15%、workflow 25%、gotcha 20%、dynamic state 15%、user preference/fact 15%、普通低价值 distractor 10%。[综合判断]

### 7.2 建议 JSONL 样本格式

```json
{
  "memory_id": "aw_dev_0037_m02",
  "content": "...",
  "memory_type": "workflow|gotcha|constraint|state|preference|fact",
  "source_episode": "...",
  "provenance": {"resource": "appworld", "task_id": "...", "step_ids": [4, 7]},
  "timestamp": "...",
  "validity_interval": ["...", null],
  "permissions": ["agent_read"],
  "canonical_fact_id": "...",
  "dependency_ids": [],
  "size_tokens": 41,
  "historical_access_count": 0,
  "agent_visible_metadata": {"type": "gotcha", "age_bucket": "old"},
  "evaluator_only": {
    "future_task_ids": ["..."],
    "need_vector": [0, 0, 1],
    "severity_tier": 4,
    "quadrant": "rare-critical"
  }
}
```

`evaluator_only` 物理上存入独立 manifest，不与 agent-visible JSONL 同文件加载。[综合判断]

### 7.3 比较方法

所有方法使用相同 50% token retention budget、相同最终 retrieval top-k（建议 `k=5`）、相同候选文本和相同 base agent：

1. **LRU**：按 last-access；从未访问者使用固定 tie-break hash；
2. **LFU**：按 historical retrieval count；同分固定 hash；
3. **Semantic importance**：候选与预注册的长期 role/domain profile 相似度，而不是偷看 future query；
4. **LLM importance**：统一 prompt 评估一般长期重要性，temperature 0，保存 rationale 但不把它当证据；
5. **Learned future-value/retention baseline**：移植 Learning What to Remember 的 blind multi-factor scorer/已发布配置；若特征不兼容，只线性校准在 source-train split，不能用 hidden future tasks；
6. **Random CF**：在同样 testing budget 下随机选择候选，生成/执行 witness；
7. **Full CF**：对所有候选生成并执行 witness，是高成本 upper bound，不参与“同预算最优”比较；
8. **PREEMPT-Mem**：modified risk triage 选候选，生成 Future Witness，执行 Full/Evicted/Restore，用验证信号调整 retention。

此外必须加入一个低成本消融：**severity-only triage**。它不替代指令规定的 baselines，但用来判断复杂的 FMEA-derived 结构是否真的比“让 LLM 只预测严重度”更有价值。[综合判断]

### 7.4 PREEMPT triage 与 witness budget

不用传统 RPN。对每条候选输出：

```text
predicted_failure_mode
predicted_severity ∈ {0,1,2,3,4}
evidence_gap ∈ {low,medium,high}
witness_feasibility ∈ {0,1,2}
predicted_need_band ∈ {rare,uncertain,frequent}
```

选择规则预注册为：先覆盖所有 `predicted_severity≥3` 的不同 failure-mode family，再按 `evidence_gap` 和 `witness_feasibility` 做 Pareto 排序；不因 `predicted_need=rare` 降权。

同预算比较：

- Random CF、severity-only 和 PREEMPT 各最多验证 `12/40` 条 candidates；
- 每条最多生成 3 个 witness proposal，只执行第一个通过静态 schema/initial-state 检查的 proposal；
- 每个执行 witness 运行 Full/Evicted/Restore × 3 seeds；
- Full CF 验证全部 40 条，单独报告约 3.33 倍 testing coverage 和实际 token/tool-call 成本。

### 7.5 三分支运行与随机性

- 环境：同一个 checkpoint；每一分支结束后丢弃状态并重新加载；
- agent：相同模型版本、system prompt、tool schema、最大步数；
- decoding：优先 temperature 0；若服务端仍非确定性，3 seeds/重复；
- 顺序：对每个 `(memory,witness,seed)` 随机化三分支执行顺序，避免时间漂移与缓存偏置；
- 记录：完整 retrieval trace、prompt hash、tool calls、DB state diff、evaluator test vector、tokens、wall time 和价格；
- 失败：API/环境错误与任务失败分开编码，不允许把 infra failure 算作 eviction loss。

### 7.6 最小指标

**现象指标**

- rare-critical prevalence（带分母和区间）；
- `P(severe failure | Need=1, Evicted)`；
- rare-critical vs rare/non-critical 的 `Δ severe` 与 test-vector loss；
- Full↔Restore rescue consistency。

**retention 指标**

- rare-critical retention recall；
- overall task success / AppWorld TGC 或 passed-test rate；
- severe failure rate；
- false protection rate：被保留但在 hidden stream 中 `Need=0` 或无验证损失的 token 占比；
- memory budget：保留 records、tokens、index bytes；
- witness cost：generation tokens、三分支 rollouts、tool calls、wall time、API cost。

**witness 指标**

- executable witness rate；
- validated witness precision：witness 上验证为高风险的条目中，在 hidden future trigger 上复现风险的比例；
- hidden-trigger risk recall；
- transfer gap：witness effect 与独立 future effect 的差；
- same-budget hit rate：12 次验证中找到多少真实 RBC records。

### 7.7 Pilot 必答五问与门槛

| 问题 | 通过 | 修改 | 停止/重构 |
|---|---|---|---|
| 能否生成合理且可执行的 Future Witness？ | `≥70%` 候选至少有 1 个可执行 proposal | `40–70%`，需约束模板/环境 schema | `<40%`，开放式 witness generation 不可行 |
| Full/Evicted/Restore 能否稳定识别影响？ | rescue consistency `≥90%`，泄漏 0 | `75–90%`，修索引/reset/模型 | `<75%`，不能做因果 claim |
| witness 风险能否在独立 trigger 复现？ | validated precision `≥60%` 且跨 ≥3 families | `35–60%`，收窄适用域 | `<35%`，witness 不能作 retention supervision |
| risk triage 是否优于同预算 random？ | RBC hit rate 绝对高 `≥15pp`，且不劣于 severity-only | 方向为正但差距小 | 不优于 random/severity-only，删除复杂 triage |
| PREEMPT 是否在同 budget 降 severe failure？ | 相对最佳非-CF baseline severe failure 降 `≥20%`，平均成功不降 >5pp | 只改善一个域/一个 family | 仅因多保留 tokens 或平均成功显著下降，核心实现需重构 |

这些是 feasibility thresholds，不是最终论文承诺。[综合判断]

---

## 8. FMEA：结论为“修改”

### 8.1 已有使用与 novelty 边界

LLM 已被用于生成/辅助 FMEA table、failure-mode identification、S/O/D scoring 和 RAG-grounded 风险分析，例如 [El Hassani et al., 2025](https://www.cambridge.org/core/journals/design-science/article/aidriven-fmea-integration-of-large-language-models-for-faster-and-more-accurate-risk-analysis/22F110A2BF0DB4D01A69472CF17A0B43) 与 [Charan et al., 2026](https://link.springer.com/article/10.1007/s13198-026-03171-6)。Agent safety 中也已有提前预测 future unsafe states/trajectories 的 Pro2Guard、TRACES、Recast、SafeMCP。[论文直接支持]

因此不能写：首次把 FMEA 用于 LLM/Agent、首次 prospective risk analysis、首次预测 future failure。最多可以说：FMEA 的若干字段是 triage prompt 的设计来源。[综合判断]

### 8.2 三个问题的直接回答

1. **能否帮助发现普通 importance scorer 漏掉的 eviction candidates？** 可能。failure mode 与 severity 强迫 scorer 讨论“删除后会发生什么”，比一般“这条是否重要”更接近项目目标；但目前没有 memory-retention 实证。[待 Pilot 验证]
2. **能否更好生成 failure mode 或 Future Witness？** 结构上可能提高覆盖与可解释性，尤其对 constraint、permission、gotcha；但开放式 LLM 也可能生成不可执行或自证式场景。[待 Pilot 验证]
3. **能否在同 testing budget 下优于简单 risk-aware selection？** 当前没有证据。必须与 severity-only、random CF 在 12/40 同预算下比较。[待 Pilot 验证]

### 8.3 为什么不保留传统 RPN

- traditional occurrence 在本项目中近似 future-need frequency；与 severity 相乘会把 low-occurrence/high-severity 条目系统性降权，目标冲突；
- S/O/D 是序数判断，直接乘积会让不同组合得到相同 RPN，却具有不同 retention 含义；
- detectability 在软件 agent 中含义不稳定：是 memory 是否易检索、失败是否易发现、还是 witness 是否易执行；
- PREEMPT 的关键证据来自实际三分支 validation，不应由未经校准的主观乘积替代。[综合判断]

### 8.4 最终保留结构

保留：`failure mode → trigger precondition → effect/severity → evidence gap → witness feasibility → validation result`。

删除：FMEA 名称作为方法卖点、传统 RPN、以 occurrence 压低 rare 项、以及“FMEA 已证明有效”的措辞。

命名建议：论文和代码中称 **Prospective Risk Triage**，FMEA 只在 related work/设计来源中一笔说明。[综合判断]

---

## 9. 当前最可信的一句话 novelty

> **PREEMPT-Mem 面向容量受限、显式可干预的外部 Agent memory，在真实 future trigger 尚未出现时生成可执行 decision witness，以 Full/Evicted/Restore 验证条目的条件性遗忘损失，并把该验证信号用于实际 retention 决策；贡献不在“首次发现 rare-critical”、一般未来风险预测、一般反事实审计或 FMEA 本身。**[综合判断]

更短的论文式表述：

> **Pre-trigger executable counterfactual supervision for budgeted retention of rare-but-critical external agent memories.**

---

## 10. 进入 Pilot 实现前仍需解决的问题

1. **`What Eviction Destroys` 原文证据。** OpenReview challenge 阻止了正文/附件/API 获取。进入正式 related-work 写作前必须人工下载或由用户提供 PDF；在此之前只保留“指定材料转述”。
2. **ConstraintRot artifact 位置。** 论文明确声称发布 grader code，但正文没有 repo 链接，本轮也未定位；不能把“论文说已发布”写成“源码已复现”。
3. **AppWorld smoke 可用性。** 需要确认当前版本的 protected bundle、data 安装、train/dev evaluation programs、task variation grouping 与 state checkpoint 在本机/目标服务器可运行。
4. **同环境 memory 来源。** 需确定官方 baseline outputs 是否足以产生 80 条候选；不足时允许运行少量 train/dev episodes，但不能用 hidden future tasks 反向写 memories。
5. **严重度 rubric 的任务无关性。** 必须先冻结哪些 DB state changes 属于 tier 3/4，再看 memory 内容；否则容易把目标条目人为写成“严重”。
6. **任务流与 rarity 分母。** 40-task stream 必须代表同一用户/环境生命周期；不能把互不相干的 task families 拼接后解释为自然发生率。
7. **learned baseline 可移植性。** Learning What to Remember 的公开 factor/weight 在 AppWorld record 上可能缺少同构特征；应预定义缺失值与只用 source-train 校准的规则。
8. **重复/依赖记录。** 需要 canonicalization 检查；否则 remove-one 会把有冗余副本的关键事实误标 non-critical。
9. **模型与 judge 成本。** AppWorld agent、witness generator、LLM importance 和 LME-V2 judge 需锁定版本；API 错误必须与任务失败分离。
10. **最终 claim 的统一性。** 双轨 Pilot 能证明 feasibility，但最终 ICLR 证据最好包含至少一个同时具备自然历史、独立 trigger、可执行工具和严重状态后果的统一切片；若第三步只能双轨成立，第四步需补这个 benchmark slice。

---

## 11. 下一步应执行的三个具体动作

> 以下是第三步的执行顺序；本报告不自动执行。

1. **冻结 Pilot manifest。** 建立 agent-visible/evaluator-only schema，从 AppWorld train/dev 历史形成 80 条候选和 40-task hidden bank，完成 task-family split、hash、Need 标注协议、severity rubric 与 duplicate/dependency 表。
2. **做 3-task 三分支 smoke test。** 安装/验证 AppWorld 小切片，实现 external store + isolated audit archive；对 constraint、workflow、gotcha 各一条跑 Full/Evicted/Restore，检查 state reset、索引重建、零泄漏、确定性 evaluator 和日志。
3. **运行 40-memory feasibility matrix。** 在 50% token budget 下依次运行 LRU/LFU、semantic/LLM importance、Learning-What-to-Remember baseline、random CF、full CF、severity-only 与 PREEMPT；按第 7.7 节 gate 给出“通过/修改/重构”，不在 gate 前扩到大规模训练。

---

## 12. 最终明确回答

### 现有公开数据和开源系统是否足够？

**有条件地足够做最小、可信、可复现的 feasibility evidence；不足以零改造地给出最终普遍性结论。**[综合判断]

公开资源已经分别提供：

- LongMemEval-V2：自然感较强的 trajectory、workflow、gotcha、premise 和独立人工 questions；
- AppWorld：可执行 API、可保存/恢复的数据库状态、task-specific initial state 与确定性 state-based evaluator；
- ConstraintRot：明确的约束丢失 failure modes 和 prohibited-effect 判定方式；
- Learning What to Remember：可复现的 blind learned retention baseline；
- ALFWorld：当 AppWorld 不可用时的低成本 resettable 备选环境。

缺少的是把这些接口连接起来的一个小型 adapter、冻结 task stream、独立标签和单条 memory archive/restore 控制，而不是缺少足以启动 Pilot 的公共素材。

### 最小可行路径

1. 从 AppWorld train/dev 历史抽取 80 条可寻址 records，冻结 40 条未来任务；LongMemEval-V2 只做自然性辅轨；
2. 先用 task specification/state tests 独立测 `NeedRate`，再用同 checkpoint 的 Full/Evicted/Restore 测 conditional criticality；
3. 从实测标签中形成四象限各 10 条，共 40 条；
4. witness generator 只能看 memory、历史与 API schema，不能看 hidden future trigger；
5. 用 12/40 相同 validation budget 比较 random、severity-only 与 PREEMPT，并用 full CF 作成本上界；
6. 在 hidden AppWorld tasks 上检验 severe failure、平均成功和 false protection，LongMemEval-V2 上检验自然 history 的迁移；
7. 只有当 Restore 稳定、witness 风险可迁移且同 budget severe failure 确实下降时，才进入第四步扩展。

因此，本轮审计的最终判断是：**进入第三步最小 Pilot 是合理的；核心 Idea 保留，claim 收窄，FMEA 修改，实验采用双轨并在 AppWorld 上完成可执行因果闭环。**

---

## 13. 本轮直接核验的主要官方来源

### 近邻方法

- [CURATOR](https://arxiv.org/html/2606.25115)
- [DeMem](https://arxiv.org/html/2605.10870)
- [What Eviction Destroys — OpenReview 入口](https://openreview.net/forum?id=8rOh73WoJh)（本轮 challenge 阻断）
- [Governance Decay / ConstraintRot](https://arxiv.org/html/2606.22528)
- [MemAudit](https://arxiv.org/html/2605.23723)
- [Learning What to Remember — paper](https://arxiv.org/html/2606.12945)；[official repo](https://github.com/zhibao-dev/Learning-Multi-Factor-Memory)
- [TraceRetain](https://arxiv.org/abs/2606.29178)
- [Memory-R1 — ACL](https://aclanthology.org/2026.acl-long.583/)；[official repo](https://github.com/yansikuan/memory-r1)
- [AgeMem — ACL](https://aclanthology.org/2026.acl-long.981/)；[official repo](https://github.com/y1y5/AgeMem)
- [TRACES](https://arxiv.org/abs/2605.27690)
- [Pro2Guard/ProbGuard](https://arxiv.org/abs/2508.00500)
- [Recast](https://arxiv.org/abs/2607.26820)
- [SafeMCP](https://aclanthology.org/2026.acl-long.522/)

### 数据、环境与 evaluator

- [LongMemEval-V2 — paper](https://arxiv.org/html/2605.12493)；[official repo](https://github.com/xiaowu0162/LongMemEval-V2)；[official data](https://huggingface.co/datasets/xiaowu0162/longmemeval-v2)
- [LongMemEval — repo](https://github.com/xiaowu0162/LongMemEval)；[data](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned)
- [LoCoMo — ACL](https://aclanthology.org/2024.acl-long.747/)；[repo](https://github.com/snap-research/locomo)
- [MemoryAgentBench — repo](https://github.com/HUST-AI-HYZ/MemoryAgentBench)；[data](https://huggingface.co/datasets/ai-hyz/MemoryAgentBench)
- [AppWorld — ACL](https://aclanthology.org/2024.acl-long.850/)；[official repo](https://github.com/StonyBrookNLP/appworld)
- [ALFWorld — official repo](https://github.com/alfworld/alfworld)
- [WebShop — official repo](https://github.com/princeton-nlp/WebShop)

### FMEA/风险分析边界

- [AI-driven FMEA: integration of large language models for faster and more accurate risk analysis](https://www.cambridge.org/core/journals/design-science/article/aidriven-fmea-integration-of-large-language-models-for-faster-and-more-accurate-risk-analysis/22F110A2BF0DB4D01A69472CF17A0B43)
- [A framework for automating FMEA using LLMs and RAG](https://link.springer.com/article/10.1007/s13198-026-03171-6)

