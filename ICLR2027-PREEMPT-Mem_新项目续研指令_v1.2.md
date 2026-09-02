# ICLR 2027 PREEMPT-Mem：基于当前完成状态的续研指令 v1.2

## 0. 开始前必须阅读

请完整阅读项目根目录中的三份研究报告：

1. `PREEMPT-Mem_第一步_文献调查与概念梳理.md`
2. `preempt可行性报告_v1.1.md`
3. `论文完整story_v1.1.md`

三份报告的作用不同：

- 第一份报告提供已经完成的文献、概念和近邻工作证据；
- 第二份报告给出当前可行性判断、方法范围和数据候选；
- 第三份报告固定论文 Story、核心贡献和最希望保留的表达。

如果第一份报告的防御性判断与后两份报告的研究主线发生冲突，不要直接推翻 Idea；应回到原论文和源码核验，然后收窄具体 claim。PREEMPT-Mem 方向已经确定，本轮不重新寻找论文 Idea。

---

## 1. 已经确定的论文主线

当前首选题目：

> **Remember Before It Matters: Preemptive Counterfactual Retention for Rare-but-Critical Agent Memory**

当前方法名：

> **PREEMPT-Mem**

如有实质更准确、更好记且不与已有工作冲突的名称，可以在报告中建议，但不要未经确认直接重命名项目。

核心问题：

> 长期 Agent 必须在有限 memory budget 下遗忘信息。当一条外部 memory 在历史中很少被真正需要、但在特定未来任务中一旦缺失就会造成严重决策损失时，Agent 能否在真实 trigger 出现前，主动生成未来测试并通过可执行反事实干预获得风险证据，从而避免误删 rare-but-critical memory？

核心 spotlight：

> **An agent should not have to suffer a rare failure before learning what it must remember.**

当前方法主线：

1. Eviction Candidate；
2. Prospective Risk Triage；
3. Future Decision Witness Generation；
4. Full/Evicted/Restore Validation；
5. Risk-aware Retention。

最重要的技术差异是：

> **pre-trigger future-witness generation + executable validation + actual retention decision。**

---

## 2. 原始六个研究问题的当前状态

| 原始问题 | 当前状态 | 已经完成 | 仍需继续推进 |
|---|---|---|---|
| 1. Agent Memory 文献、rare、importance、criticality 与源码 | **部分完成** | 已完成广义文献综述；梳理了 external/internal、retention/deletion、rare 的三种含义和多类 importance/value；识别了主要近邻 | 尚未系统核验最强近邻的官方源码；rare/critical 尚未形成可直接进入实验的最终定义和阈值；部分最新近邻需要补充 |
| 2. 是否需要证明 rare-but-critical memory | **概念结论完成，实证未完成** | 已确认现象在文献中被注意到，不能声称首次提出；已明确需要 rarity × deletion loss 的二维证据 | 尚未在公开或可信构造的任务流中证明其比例、基线失效和删除后严重损失；尚未形成最小现象实验 |
| 3. 研究内部还是外部记忆 | **基本完成** | 主对象已确定为非参数化、显式、可寻址、可干预的外部 episodic/semantic memory；参数记忆与 KV cache 不作为主问题 | 需要通过目标框架源码确认 memory unit、effective eviction、恢复接口和 active-context 边界 |
| 4. 没有公司日志时的数据与 benchmark | **只完成候选识别** | 已发现 LongMemEval-V2、ConstraintRot/Governance Decay、LongMemEval、LoCoMo、MemoryAgentBench 等候选 | 尚未逐项核验数据格式、下载、license、轨迹内容、环境 reset、工具 evaluator 和改造成本；尚未决定最终数据组合或构造方案 |
| 5. 寻找细微视角差异、避免过度否定 | **核心差异初步完成** | 已将主要 novelty 收敛为 pre-trigger Future Witness + executable counterfactual validation + retention；已区分 pre-trigger 与 pre-deletion | 需要用最强近邻的正文和源码确认差异是否真实；需要把问题分成致命碰撞、claim 收窄、实验缺口和工程问题，不能把局部相似写成 Idea 失败 |
| 6. FMEA 能否用于 Agent Memory | **概念定位完成，技术价值未验证** | 已确认 FMEA 不是必需组件，也不单独作为 novelty；可以作为 Prospective Risk Triage 的候选设计来源 | 尚未核验相关应用、确定最简筛选规则，也未证明它比 generic risk-aware selection 更有效；需要得出保留、修改或删除结论 |

此外，论文题目、完整 Story、Alice 示例、核心方法方向和 spotlight 已经形成，不需要重新编写一套完全不同的 Story。

---

## 3. 本轮阶段目标

当前已经不再处于“广泛了解 Agent Memory”的阶段。

本轮只执行：

> **第二步：源码、公开数据、操作定义与 rare-critical 现象验证方案审计。**

目标是把已完成的文献与 Story 转化成一个可以立即开始最小 Pilot 的研究方案。

本轮不下载大规模数据、不实现正式 PREEMPT-Mem、不运行大规模实验。完成分析报告后停止，等待我决定是否进入 Pilot 实现。

---

## 4. 本轮需要完成的任务

### 任务 A：只补齐最强近邻，不重做广义综述

优先核验：

- CURATOR；
- DeMem；
- What Eviction Destroys；
- Governance Decay / ConstraintRot；
- MemAudit；
- Learning What to Remember；
- TraceRetain；
- Memory-R1、AgeMem；
- LongMemEval-V2 / AgentRunbook。

需要阅读论文正文、附录和可用的官方源码，回答：

1. memory unit 是什么？
2. 系统是否执行真实 deletion/effective eviction，还是只做 retrieval filtering？
3. 价值证据来自历史访问、当前 query、已发生失败、模型预测，还是主动生成的未来任务？
4. trigger 是否已经给定？
5. 是否真实运行 Agent 和工具行为？
6. 是否进行单条 memory remove/restore？
7. 结果用于事后审计、删除有害 memory，还是删除前保护有益 memory？
8. 是否同时考虑 memory budget 与 counterfactual testing cost？

最终给出一个简洁比较表，并明确回答：是否已有工作同时实现了“未见 trigger 的主动 witness generation、可执行 memory intervention 和实际 retention”。

不要再重复 Generative Agents、MemGPT 等基础系统的长篇介绍，除非源码接口直接影响实验选择。

### 任务 B：把 rare-but-critical 从概念变成可测现象

给出一套推荐的操作定义：

- memory unit；
- effective eviction；
- rarity；
- conditional criticality；
- rare-but-critical region；
- counterfactual forgetting loss；
- 有效的 Future Decision Witness。

重点解决：

- rarity 的分母是单个 Agent 生命周期、用户任务流还是 benchmark distribution；
- 历史低 retrieval 是真实低需求还是 retrieval failure；
- criticality 用任务失败、违规工具操作、损失分级还是其他指标；
- rare 与 critical 的阈值如何设置而不循环论证；
- 多条 memory 的冗余、依赖和协同如何影响 remove-one attribution；
- Restore 是主要 effect estimate，还是用于排除随机性与环境漂移。

然后设计一个最小“现象存在性”实验，证明：

1. 数据中存在不止单个手工案例的 rare-critical memory；
2. 常见 retention baseline 会把其中一部分排到淘汰端；
3. effective eviction 后的损失显著高于普通低分 memory；
4. 结论不是使用同一套人工规则生成样本后再证明自己。

这里不要求证明 rare-critical memory 在所有真实 Agent 中普遍存在；只需要在可信、可复现的任务分布中建立问题和基线盲点。

### 任务 C：逐项审计公开数据、环境和代码

至少检查：

- LongMemEval-V2；
- ConstraintRot / Governance Decay；
- LongMemEval；
- LoCoMo；
- MemoryAgentBench；
- AppWorld、ALFWorld、WebShop 或其他真正相关的可执行环境。

每项资源都要回答：

| 方面 | 需要确认的内容 |
|---|---|
| Memory 来源 | 是否包含自然事实、经验、workflow、gotcha、动态状态或约束 |
| Trigger | 是否有独立未来任务，还是只有给定 QA query |
| 可执行性 | 是否能运行 Agent、reset 环境并重放相同任务 |
| 删除与恢复 | 是否能对单条 memory 做 effective eviction 和 Restore |
| 严重后果 | 是否有错误工具调用、违规操作或明确任务失败 |
| Evaluator | 是否确定性、可复现，还是依赖 LLM judge |
| 可获取性 | 数据、代码、license、下载方式和运行成本 |
| 改造成本 | 能否在当前时间和算力下形成 30–50 条 memory Pilot |

必须区分四种不同资源：

1. 自然 memory pool；
2. future trigger tasks；
3. 可执行 Agent 环境；
4. severe-outcome evaluator。

不要假设一个 benchmark 可以同时承担四个角色。最终选择一个主数据组合和一个备选组合，并解释如何把它们连接成 PREEMPT-Mem 实验。

### 任务 D：设计下一阶段的 30–50 条 memory Pilot

本轮只设计，不实现。

Pilot 应包含：

- rare/critical；
- rare/non-critical；
- frequent/critical；
- frequent/non-critical。

至少比较：

- LRU/LFU；
- semantic/LLM importance；
- 最接近的 learned future-value baseline；
- random counterfactual testing；
- full counterfactual testing；
- PREEMPT-Mem。

Pilot 必须回答：

1. 能否为候选 memory 生成合理且可执行的 Future Witness？
2. Full/Evicted/Restore 能否稳定识别目标 memory 的因果影响？
3. witness 上发现的 forgetting risk 能否在独立 future trigger 上复现？
4. risk triage 是否比同预算 random testing 找到更多 rare-critical memory？
5. PREEMPT 是否在相同 memory budget 下减少 severe failure，而不是仅仅保留更多内容？

给出最小指标、样本格式、运行次数、预算控制和通过/修改条件，但不要设计不必要的大型理论或训练流程。

### 任务 E：对 FMEA 给出一次明确结论

调查 FMEA 或相似 prospective risk analysis 在 Agent/LLM 中的已有使用，避免错误 novelty 表述。

然后只回答：

1. FMEA 是否能帮助发现普通 importance scorer 容易漏掉的 eviction candidates？
2. 它是否能更好地生成 failure mode 或 Future Witness？
3. 它是否能在相同 testing budget 下优于更简单的 risk-aware selection？

结论必须三选一：

- **保留**：作为 Prospective Risk Triage 的有效实现；
- **修改**：只保留 severity/detectability 等有价值结构，不使用传统 RPN 或 FMEA 名称；
- **删除**：不进入方法，仅作为早期思路来源。

无论选择哪一种，都不能改变论文的核心 novelty：pre-trigger counterfactual supervision。

---

## 5. 如何使用 AI 的严格审查

请主动寻找与 PREEMPT-Mem 的细微重合，但将问题分类：

- **核心碰撞**：已有工作已经完成完整核心组合；
- **Claim 收窄**：某个宽泛表述已被覆盖，但核心组合仍不同；
- **实验缺口**：需要额外对照或验证；
- **工程风险**：数据、环境或成本问题；
- **措辞风险**：不能声称“首次”，但不影响方法。

只有第一类才可能推翻核心 Idea。其余问题应转化成更准确的 claim、实验或实现选择，而不是追求一个没有任何相似工作的“100% 完美 Idea”。

---

## 6. 本轮交付物

请生成：

> `research/PREEMPT-Mem_第二步_数据源码与现象验证审计.md`

报告必须包含：

1. 六个原始问题的最新状态表；
2. 最强近邻的论文/源码比较；
3. 推荐操作定义；
4. rare-critical 现象存在性实验方案；
5. 数据集、环境、代码与 evaluator 可用性表；
6. 推荐主数据组合和备选组合；
7. 30–50 条 memory Pilot 设计；
8. FMEA 的保留、修改或删除结论；
9. 当前最可信的一句话 novelty；
10. 进入 Pilot 实现前仍需解决的问题；
11. 下一步应执行的三个具体动作。

报告最后明确回答：

> **现有公开数据和开源系统是否足以让我们实证 rare-but-critical memory、生成未见 Future Witness，并通过可执行 memory intervention 验证其删除风险？如果可以，最小可行路径是什么？**

完成报告后停止。不要自动下载大规模数据、构造完整 benchmark、实现 PREEMPT-Mem、运行 GPU 实验或重新寻找其他论文 Idea，等待我确认第三步。

---

## 7. 后续阶段路线图（本轮不要执行）

- **第三步：最小 Pilot 实现**——构造 30–50 条 memory，运行 Full/Evicted/Restore，检验现象和 witness 信号；
- **第四步：方法与 Benchmark 扩展**——确定 risk triage、扩大数据和基线；
- **第五步：完整实验与论文写作**——形成主表、Pareto、消融和错误分析。

本轮只完成第二步。
