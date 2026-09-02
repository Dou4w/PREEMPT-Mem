# ICLR 2027 PREEMPT-Mem：新项目续研指令 v1.1

## 0. 开始前必须阅读

请先完整阅读项目根目录中的：

1. `preempt可行性报告_v1.1.md`
2. `论文完整story_v1.1.md`

这两份文件给出了当前已经确定的研究 Story、核心方法与 novelty 判断。不要重新寻找论文方向，也不要把本轮变成一次泛化的 Agent Memory 文献综述。

本轮需要实际开展分析和核验，而不是只给出计划。完成规定报告后停止，等待我确认下一步。

---

## 1. 已经确定的研究主线

当前首选题目：

> **Remember Before It Matters: Preemptive Counterfactual Retention for Rare-but-Critical Agent Memory**

当前方法名：

> **PREEMPT-Mem**

如果有实质更准确、更好记且不与已有工作冲突的名称，可以在报告中提出建议；不要未经确认直接重命名项目。

论文核心问题固定为：

> 长期 Agent 必须在有限记忆预算下遗忘信息。当某条外部 memory 在历史中很少被使用、但在特定未来任务中一旦缺失就会造成严重决策损失时，Agent 能否在真实 trigger 出现前，主动生成未来测试并通过可执行反事实干预获得风险证据，从而避免误删 rare-but-critical memory？

最重要的 Story 是：

> **An agent should not have to suffer a rare failure before learning what it must remember.**

最重要的技术差异是：

> **pre-trigger future-witness generation + executable validation + actual retention decision。**

不要把 PREEMPT-Mem 改写成普通 importance scorer、纯 benchmark、事后 memory audit 或一般检索增强。

---

## 2. 当前方法主线

继续沿下面一条主线分析，不要同时展开多套平行论文方案：

1. **Eviction Candidate**：现有 retention policy 提出准备淘汰的 external memory items；
2. **Prospective Risk Triage**：用低成本信号选择最值得验证的候选；
3. **Future Decision Witness Generation**：主动生成尚未发生、合理且可执行的未来任务；
4. **Full/Evicted/Restore Validation**：运行 Agent，验证目标 memory 缺失是否造成决策损失及恢复效果；
5. **Risk-aware Retention**：在固定 memory budget 下保护经验证的高风险 memory。

主研究对象暂定为：

> **非参数化、显式、可寻址、可干预的外部长期 episodic/semantic memory。**

这里的 deletion 优先使用 **effective eviction**：目标 memory 在正常 budget、检索接口和 Agent 权限下不再可用；可以保留 Agent 无法访问的审计副本用于 Restore。

---

## 3. FMEA 的位置

FMEA 不是论文必须使用的组件，也不单独作为 novelty。

它当前只是 `Prospective Risk Triage` 的候选设计来源，可以帮助分解：

- failure mode；
- severity；
- occurrence；
- detectability / baseline blind spot。

不能机械采用传统 `Severity × Occurrence × Detection`，因为 occurrence 较低可能继续压低 rare-but-critical memory 的排序。

本轮只需要判断：

> **FMEA-inspired decomposition 是否能让候选筛选更有效、更可解释或更容易形成实验贡献？**

如果能，保留为 risk triage 的具体实现；如果不能，换成更一般的 risk-aware candidate selection。不要因为 FMEA 的去留重构整篇论文，也不要让它抢走 Future Witness 的 spotlight。

---

## 4. 必须遵守的 Novelty 边界

不能单独宣称：

- 首次提出 rare-but-important / rare-but-critical memory；
- 首次研究 memory importance、future utility 或 budgeted eviction；
- 首次使用 downstream decision loss；
- 首次做 memory removal counterfactual；
- Full/Evicted/Restore 本身是 novelty；
- 首次把 FMEA 用于 Agent。

必须区分：

- **pre-deletion**：删除尚未发生；
- **pre-trigger**：真实需要该 memory 的未来任务尚未发生，系统主动生成测试情境。

发现近邻工作时，重点判断它是否已经同时具备：

> **未见 trigger 的主动 witness generation、真实 Agent 执行、memory intervention，以及把结果用于预算化 retention。**

局部相似只用于收窄 claim，不要轻易推翻整个 Idea。

---

## 5. 本轮需要完成的分析

### A. 核验最接近的工作

至少核验：

- CURATOR；
- DeMem；
- What Eviction Destroys；
- Governance Decay / ConstraintRot；
- MemAudit；
- Learning What to Remember；
- TraceRetain；
- Memory-R1、AgeMem；
- LongMemEval-V2。

对每项工作回答：

- 价值证据来自历史、当前 query、已发生失败，还是主动生成的未来任务？
- trigger 是否已经给定？
- 是否真实执行 remove/restore 和 Agent 工具行为？
- 优化的是平均 utility 还是条件性严重后果？
- 结果用于解释、审计、删除有害记忆，还是保护有益记忆？
- 与 PREEMPT-Mem 的最小、准确差异是什么？

最后给出一句经过核验的核心 novelty，不要堆叠大量防御性描述。

### B. 收敛定义和实验范围

给出可以直接进入实验的推荐定义：

- memory unit；
- effective eviction；
- rarity；
- conditional criticality；
- rare-critical region；
-有效的 Future Decision Witness；
- Full/Evicted/Restore 分别提供什么证据。

重点解决：

- 低 retrieval count 是真实低需求还是 retrieval failure；
- witness 是否只是 memory 原文的机械改写；
- 多 memory 冗余或依赖如何影响 remove-one attribution；
- 如何避免把真实 test trigger 泄漏给 witness generator。

不追求复杂理论，优先给出最简单、清楚、可实现的操作定义。

### C. 审计公开数据与代码

重点检查：

- LongMemEval-V2 是否适合提供自然 memory 和 Web Agent trajectory；
- ConstraintRot / Governance Decay 是否适合提供确定性高后果工具场景；
- LongMemEval、LoCoMo、MemoryAgentBench、AppWorld、ALFWorld、WebShop 等是否真的适用；
- 对应数据、代码、license、规模、下载方式、环境 reset 和 evaluator 是否公开可用。

不要假设一个 benchmark 能同时提供 memory、future trigger、可执行环境和严重后果 evaluator。给出一个推荐数据组合和一个备选组合。

### D. 设计最小端到端 Pilot

设计一个 30–50 条 memory 的 Pilot，但本轮不实现代码。

Pilot 应回答：

1. 能否生成合理、可执行的 Future Witness；
2. Full/Evicted/Restore 是否能稳定识别目标 memory 的影响；
3. witness 上发现的风险能否在独立 future trigger 上复现；
4. risk triage 是否比相同预算的 random testing 找到更多 rare-critical memory；
5. PREEMPT 是否在相同 memory budget 下减少 severe failure，而不是仅仅保留更多内容。

至少比较：

- LRU/LFU；
- semantic/LLM importance；
- 最接近的 learned future-value baseline；
- random counterfactual testing；
- full counterfactual testing；
- PREEMPT-Mem。

FMEA-inspired 与 generic risk triage 只作为同一筛选模块的消融，不要发展成两套论文主线。

核心指标：

- rare-critical retention recall；
- severe failure rate；
- 平均任务成功率；
- false protection；
- memory budget；
- counterfactual rollout/token/tool cost。

---

## 6. 证据和写作要求

- 优先使用正式 proceedings、OpenReview、ACL Anthology、官方 arXiv、官方 GitHub 和数据页面；
- 对删除、恢复、reward、数据构造和 evaluator 语义，必要时检查源码；
- 区分论文直接支持、源码直接支持、综合判断和待实验验证；
- 减少防御性描述，不要重复大段 Agent Memory 常识；
- 每个未定问题都给出一个推荐选择；
- 始终把篇幅集中在 PREEMPT-Mem 的亮点、可实现性和最小实验上。

---

## 7. 本轮交付物

请生成：

> `research/PREEMPT-Mem_第二阶段_核心可行性收敛.md`

报告应包含：

1. 执行结论；
2. 最近邻比较与最终一句话 novelty；
3. 推荐操作定义；
4. 数据、代码和环境可用性表；
5. 推荐数据组合；
6. 30–50 条 memory 的 Pilot；
7. FMEA 保留、降级或删除的建议；
8. 当前最可信的三至四项论文贡献；
9. 题目和方法名是否需要优化；
10. 下一步应立刻执行的三项工作。

报告最后明确回答：

> **PREEMPT-Mem 是否仍能以 pre-trigger counterfactual supervision 形成清楚、可实现且有辨识度的 ICLR 2027 贡献？当前最简、最亮眼的实现路径是什么？**

完成报告后停止。不要自动构造完整 benchmark、实现代码、运行大规模模型或重新寻找其他论文 Idea，等待我确认下一步。
