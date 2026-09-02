# ICLR 2027 PREEMPT-Mem：已完成内容独立复核审查指令

## 0. 审查任务定位

你现在是 PREEMPT-Mem 项目的**独立研究审查者**，不是继续推进方法的主研究者。

本轮只复核已经完成的研究内容，目标是判断：

- 文献与引用是否真实、准确、完整；
- 概念定义和范围选择是否合理；
- novelty 是否被准确定位；
- 数据与实验可行性判断是否有依据；
- 三份报告之间是否一致；
- 哪些结论已经可以保留，哪些需要收窄、补证据或修改。

不要修改原报告，不要进入数据构造、Pilot 实现或完整方法设计，也不要重新寻找另一篇论文 Idea。完成独立审查报告后停止。

---

## 1. 必须完整阅读的文件

请完整阅读项目根目录中的：

1. `PREEMPT-Mem_第一步_文献调查与概念梳理.md`
2. `preempt可行性报告_v1.1.md`
3. `论文完整story_v1.1.md`

可以阅读 `ICLR2027-PREEMPT-Mem_新项目续研指令_v1.2.md` 了解哪些工作被标记为尚未完成，但它不是研究证据，不应替代对三份报告的审查。

三份报告不是必须维护的既定结论。请独立核验，但也不要因为单个局部问题就推翻完整 Idea。

---

## 2. 当前待审查的核心主张

论文当前首选题目：

> **Remember Before It Matters: Preemptive Counterfactual Retention for Rare-but-Critical Agent Memory**

当前方法名：

> **PREEMPT-Mem**

当前核心 Story：

> **An agent should not have to suffer a rare failure before learning what it must remember.**

当前核心 novelty 假设：

> **在真实 trigger 尚未出现时，主动生成 Future Decision Witness，通过可执行的 Full/Evicted/Restore memory intervention 获得 pre-trigger counterfactual supervision，并将结果用于实际的预算化 retention。**

当前研究对象：

> **非参数化、显式、可寻址、可干预的外部 episodic/semantic Agent memory；deletion 主要采用 effective eviction 语义。**

FMEA 的当前定位：

> **不是必需组件或独立 novelty，只是 Prospective Risk Triage 的候选设计来源。**

请逐项核验这些主张，而不是默认它们正确。

---

## 3. 审查原则

### 3.1 严格，但不要过度防御

发现问题后必须分类：

1. **核心碰撞**：已有工作已经覆盖完整核心组合，直接威胁主要 novelty；
2. **Claim 收窄**：某个宽泛表述已被覆盖，但核心组合仍有差异；
3. **缺失证据**：主张合理，但需要额外数据、实验或源码证明；
4. **工程风险**：数据、环境、成本或实现存在不确定性；
5. **措辞/引用问题**：表述不准确、引用不匹配或发表状态错误；
6. **已确认优势**：经独立核验后可以继续保留的内容。

只有第一类可以被称为核心 Idea 危机。不能把“需要实验验证”写成“novelty 已不存在”，也不能因为没有 100% 完美先例空白就否定研究方向。

### 3.2 区分事实与推断

所有重要判断标明：

- 论文正文直接支持；
- 官方源码直接支持；
- 多篇文献综合推断；
- 当前报告推测；
- 尚待实验验证。

### 3.3 使用一手来源

优先检查：

- 正式 proceedings；
- OpenReview；
- ACL Anthology / PMLR；
- 官方 arXiv；
- 官方 GitHub、数据仓库与项目页面。

不能仅根据搜索结果摘要、二手博客或报告中的转述确认技术 claim。需要记录论文真实题目、作者、时间和发表状态；预印本、workshop 和匿名在审稿件必须准确标注。

---

## 4. 具体审查任务

### 任务 A：文献与引用真实性审查

核验三份报告中支撑核心判断的主要论文，至少包括：

- Agent Memory 相关综述；
- TraceRetain；
- Learning What to Remember；
- CURATOR；
- DeMem；
- What Eviction Destroys；
- Governance Decay / ConstraintRot；
- MemAudit；
- Memory-R1、AgeMem；
- LongMemEval-V2。

逐项检查：

1. 论文是否真实存在，链接是否正确；
2. 标注的年份、venue 和发表状态是否准确；
3. 报告对论文方法的描述是否来自原文；
4. 论文是否真的支持报告所引用的结论；
5. 是否存在把 retrieval filtering、context eviction、compression 和 persistent/effective deletion 混为一谈；
6. 是否遗漏了会显著改变 novelty 判断的强近邻。

不要求重新写一篇完整综述；重点审查影响 PREEMPT-Mem 核心主张的证据。

### 任务 B：Rare、critical、importance 定义审查

检查报告是否正确区分：

- 历史 retrieval frequency；
- future need probability；
- event base rate；
- token surprisal；
- relevance；
- semantic/LLM importance；
- observed downstream utility；
- conditional forgetting loss；
- criticality / severity。

重点回答：

1. 当前对 rarity 的推荐定义是否可测，而不是依赖不可观测的真实未来；
2. 低 retrieval 是否可能只是 retrieval failure；
3. criticality 是否真正与 occurrence/rarity 解耦；
4. rare-but-critical region 是否会产生循环定义；
5. 报告是否过早把某个尚未确定的定义写成既定事实；
6. “需要先证明 rare-but-critical memory”这一判断是否合理，证明标准是否过强或过弱。

请给出“可以保留的定义”和“必须在第二阶段修正的定义”，但不要在本轮替报告设计完整数学理论。

### 任务 C：内部/外部记忆与 deletion 语义审查

核验将主研究对象限定为 external addressable memory 是否合理。

检查：

- external episodic/semantic memory 是否最适合单条干预；
- active context 是否应该作为读取层、扩展实验还是主对象；
- procedural memory 是否应暂时排除；
- `effective eviction` 是否解决了永久删除与 Restore 之间的矛盾；
- Full/Evicted/Restore 是否能在真实系统中被清楚实现；
- Restore 的作用是主要因果估计、验证控制，还是存在概念冗余。

如果范围选择合理，应明确确认，而不是仅罗列剩余问题。

### 任务 D：Novelty 与最近邻碰撞审查

按统一维度比较最强近邻：

| 维度 | 审查问题 |
|---|---|
| Trigger 是否已知 | 测试 query 已出现，还是未来 trigger 尚未出现？ |
| 证据来源 | 历史访问、当前 query、已发生失败、模型预测，还是主动生成 witness？ |
| Memory intervention | 是否真的 remove/restore 单条 memory？ |
| Agent execution | 是否运行真实 Agent/工具行为，还是只做 scorer 预测？ |
| 目标语义 | 平均 utility、decision loss，还是条件性严重后果？ |
| 时间方向 | 事后审计、当前任务适配，还是 pre-trigger protection？ |
| 最终用途 | 解释、删除有害 memory，还是保护有益 memory 并执行 retention？ |
| 预算 | 是否考虑 memory budget 与 counterfactual testing cost？ |

重点判断以下内容是否真的构成剩余空间：

> **unseen trigger + active Future Witness generation + executable memory intervention + actual budgeted retention。**

不能把以下单点误写成 novelty：rare-important 现象、decision loss、remove-one counterfactual、Full/Evicted/Restore、future utility、budgeted eviction 或 FMEA。

最终给出：

- 一句可以安全保留的 novelty；
- 一句需要收窄的 novelty；
- 是否发现核心碰撞。

### 任务 E：数据与实验可行性主张审查

审查报告对下列资源的描述是否准确：

- LongMemEval-V2；
- ConstraintRot / Governance Decay；
- LongMemEval；
- LoCoMo；
- MemoryAgentBench；
- 其他被报告提到的数据或环境。

检查报告是否把：

1. 自然 memory 来源；
2. future trigger；
3. 可执行 Agent 环境；
4. severe-outcome evaluator；

错误地假设为可由单一 benchmark 同时提供。

核验“公开数据足以支撑研究”“没有公司日志不是核心障碍”这两项判断是否证据充分。若只是有希望但未审计，应标注为可行性假设，而不是已确认事实。

### 任务 F：FMEA 定位审查

核验三份报告当前对 FMEA 的处理是否合理：

- 是否正确避免把“首次将 FMEA 用于 Agent”当作 novelty；
- traditional RPN 是否确实与 rare × high severity 存在冲突；
- FMEA 是否提供了 generic risk triage 没有的独特技术能力；
- 当前把它降为候选实现，是否比强行保留或完全删除更合适。

本轮只评价当前定位，不要求设计完整 FMEA 模块。给出：保留当前定位、进一步降级或需要恢复为核心模块三选一建议，并说明证据。

### 任务 G：三份报告内部一致性与 Story 审查

检查三份报告之间是否存在：

- 研究对象不一致；
- deletion 与 Restore 语义冲突；
- rare/critical 定义不一致；
- 把“待验证”写成“已经证明”；
- 近邻工作在不同报告中描述矛盾；
- contributions 与方法模块不对应；
- FMEA 地位反复变化；
- Story 为了突出亮点而产生过度 claim；
- 第一份报告的谨慎表述是否被后两份报告无依据地扩大。

同时明确指出哪些 Story 表达虽然简化，但在论文叙事中合理，不必因为它不是完整技术定义就删除。

---

## 5. 审查结论等级

最终必须选择一个总等级：

- **PASS**：核心文献、范围、novelty 和可行性判断基本成立，只需小修；
- **PASS WITH REVISIONS**：核心 Idea 仍成立，但若干 claims、引用或定义需要收窄；
- **MAJOR REWORK**：核心问题有价值，但当前 Story 或方法定位需要明显重构；
- **CORE COLLISION**：发现已有工作覆盖完整核心组合，当前主要 novelty 无法维持。

不要因为数据和实验尚未完成而自动给出 MAJOR REWORK；未完成实证本来就是下一阶段任务。等级主要评价“已完成内容是否为后续研究提供了可靠基础”。

---

## 6. 本轮交付物

请生成：

> `review/PREEMPT-Mem_已完成内容独立复核报告.md`

报告必须包含：

1. 一页以内的执行结论与审查等级；
2. 核心 claims 的逐项核验表；
3. 关键文献真实性、发表状态和引用适配性表；
4. 最强近邻统一比较表；
5. rare、critical、importance 与 effective eviction 定义审查；
6. 外部 memory 范围与 Full/Evicted/Restore 可行性审查；
7. 数据与 benchmark 可行性主张审查；
8. FMEA 当前定位审查；
9. 三份报告的内部矛盾或不一致；
10. 已确认、可以继续保留的优势；
11. 按严重级别排序的问题清单；
12. 建议修改的具体句子或 claims，但不要直接修改原文件；
13. 对第二阶段续研计划是否足以覆盖这些问题的判断；
14. 下一步最重要的五项修正或核验任务。

每项问题尽量包含：

- 对应文件与章节；
- 原主张；
- 核验证据；
- 问题级别；
- 推荐修正。

报告最后明确回答：

> **截至当前已完成内容，PREEMPT-Mem 的核心 Story 和 pre-trigger counterfactual retention 定位是否仍然成立？哪些部分已经可以视为可靠基础，哪些部分必须在进入 Pilot 前修正？**

完成报告后停止。不要修改三份原报告，不要自动执行第二阶段研究，不要实现代码、下载大规模数据、运行实验或重新选择论文 Idea。
