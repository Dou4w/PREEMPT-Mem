# PREEMPT-Mem 第三步 A `run_005` 独立实验审计

**审计日期**：2026-08-27  
**审计性质**：fresh zero-context、same-family 独立只读复核；结论为 **provisional**  
**审计对象**：仅 `third_step_a/artifacts/smoke/run_005` 及其冻结协议、代码、探针和最终审计叙事  
**允许的证据范围**：adapted + constructed/semi-synthetic mechanism smoke，进一步限定为 **constructed deterministic selector-channel mechanism smoke**

## 一、总判决

`run_005` 满足本轮四项用户 gate，可以进入下一阶段的独立审阅/后续实验规划。复核结果为：

- 3/3 案例均为 Full 成功、Evicted 失败、Restore 成功；
- 3/3 案例中 Full 与 Restore 的官方 evaluator 结果、关键/完整最终 DB tree、生成代码和恢复后的 memory record 均相同；
- 3/3 Evicted 均出现可解释的 official task failure/required action omission，且无目标或敏感状态写入，观测 severity=3 合理；
- 3/3 Evicted 的最终 effective-eviction manifest 均为 15/15，通过真实 target negative retrieval 后的再次审计仍无泄漏；
- 9/9 分支保存的两次 evaluator 结果一致，独立重放也复现相同 success、测试通过数和失败 requirement；
- 21/21 freeze 文件及 377/377 manifest 条目的大小与 SHA-256 独立重算匹配。

本结论只证明：在三个人工固定的 selector-channel 案例里，外部 selector record 的存在、删除、同记录恢复与固定 AppWorld 状态机能够形成可复现的 plumbing 效果。它不证明 memory content 的语义效用，也不证明自然 memory lifecycle、witness 预测效度、现象稀有度/普遍性、FMEA 优越性、完整 PREEMPT 优越性、组件首创性或跨 Agent/LLM/task-family 泛化。

## 二、审计方法与证据独立性

本审计没有采信 aggregate 或最终叙事作为事实来源，而是独立读取并交叉核对：执行冻结、config、runner/aggregator/memory-store/executor 源码、四组结构与 memory 探针、三个案例的九个分支 `branch_result.json`、两次 evaluator 结构化输出与报告、实际 prompt、retrieval、decision、generated code、API log、checkpoint/final DB snapshot、`database_state_diff.json`、case summary、aggregate 和 artifact manifest。

复核还使用项目冻结的 Python 环境直接调用 evaluator 与 severity 函数。为避免写回证据，Python 以禁止 bytecode 的方式运行，evaluator 使用 `save_report=False`；复核前后未发现原始产物时间戳变化。本报告是本次审计唯一新增文件。

## 三、执行冻结、时序与 manifest

### 3.1 Freeze 内容与时序

`execution_freeze_run_005_sha256.json` 的独立文件哈希为：

`15d9caaf5c3c0e91424c114da3939fb9010c4910b8bd0d142d7fdd379310a4c0`

冻结清单包含 21 个协议、config、prompt、witness/probe 和实现文件；逐项读取当前字节并重算 SHA-256，21/21 匹配、零缺失、零漂移。冻结记录时间为 `2026-08-27T20:44:00.4422695+08:00`，freeze 文件创建早于 `run_005` 根目录及其最早产物（约 20:44:17），不存在先运行后冻结的迹象。

`run_smoke_case.py` 把 `--execution-freeze` 设为必填，并在创建 target checkpoint 之前执行 freeze validation。验证覆盖 run ID/path、21 个冻结文件、Python/OS/AppWorld code/data/commit、三案 source specs/solution 与 target specs/test-data/evaluation 哈希；验证失败会在 checkpoint 和分支运行前抛错。九个分支保存的 freeze validation 均为 41/41、`all_pass=true`。

### 3.2 运行 manifest

独立枚举 `run_005` 下除 `artifact_manifest.json` 自身以外的实际文件，并重算大小和 SHA-256：manifest 377 项全部匹配，零缺失、零额外文件、零 size/hash mismatch。`aggregate_smoke.py` 也会从原始 branch result 重算汇总字段，并拒绝 raw/summary 不一致或覆盖既有 aggregate；未发现“只改 summary、不改原始结果”的路径。

## 四、真实 AppWorld 与 evaluator 绑定

冻结环境与实际虚拟环境一致：

- AppWorld package：`0.2.0.dev0`；data：`0.2.0`；
- vendor source commit：`a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`；
- Python：`3.12.13`；OS：`Windows-11-10.0.22000-SP0`。

三案的 source/target specs、source solution、target test-data 和 target evaluation 源文件共 15 个冻结哈希均独立重算匹配。source 与 target 是同 generator/scenario 的不同 variation、不同用户和不同指令，不是同一任务文件的复制。

源码调用链显示 `AppWorld.evaluate()` 进入官方 `evaluate_task`，按 target task 加载官方 ground truth、evaluation module、公开/私有 test-data 及起止 model collections。三案 evaluator 分别检查精确文件路径/内容与 untouched invariant、精确年度移动/重命名与非目标保持、以及 Venmo 收款人/金额/备注和短信内容与无删除约束。因此本轮 `evaluation_type` 判定为 **real_gt**，不是模型自评、代理指标或 witness 派生标签。

`structural_probe.json` 还验证了 task-specific DB、checkpoint 往返、同任务 reset、跨任务重绑、官方 solution 成功、重复 evaluator 稳定，以及故意 collateral 删除会触发 `no_op_pass` 失败；`all_required_checks_pass=true`。

## 五、三案九分支原始结果与 gate 重算

| 案例 | Full | Evicted | Restore | 原始 API 调用 | Full↔Restore 状态 | Evicted 解释 |
|---|---:|---:|---:|---|---|---|
| workflow | 8/8，成功 | 2/8，失败，S=3 | 8/8，成功 | 67 / 1 / 67 | evaluator、代码、API log、最终 DB tree byte-equivalent | 未创建要求的 26 个文件；仅 fail-closed completion |
| gotcha | 5/5，成功 | 2/5，失败，S=3 | 5/5，成功 | 125 / 1 / 125 | evaluator、代码、API log、最终 DB tree byte-equivalent | 未执行要求的 60 个文件移动；仅 fail-closed completion |
| constraint_permission | 10/10，成功 | 2/10，失败，S=3 | 10/10，成功 | 27 / 1 / 27 | evaluator、代码、API log、最终 DB tree byte-equivalent | 未产生正确的 Venmo 交易与短信；无 Venmo/phone 敏感写入 |

每案三个分支均从同一 byte-equivalent target checkpoint 启动，同案实际 prompt 文件逐字节相同。Full 与 Restore 还具有相同 candidate ID/record hash、retrieval result、decision、generated code、API log、evaluator 结果和完整 final DB tree hash。`database_state_diff.json` 的 checkpoint→各分支、Full→Evicted、Full→Restore 五组差异与原始 DB snapshot 独立核对一致：三案 Full→Restore 均无字节差异；Full→Evicted 的差异均来自目标动作缺失，Evicted 相对 checkpoint 只有 fail completion/supervisor 等运行记录，没有目标或 collateral 写入。

据此独立重算用户 gate：

| Gate | 独立结论 |
|---|---|
| 至少 2/3 Full 与 Restore 结果及关键 DB 等价 | PASS：3/3 完全相同 |
| Evicted 相对 Full 有可解释失败/约束违反/严重状态差 | PASS：3/3 official failure，severity=3 |
| Effective eviction 无泄漏 | PASS：3/3 最终 15/15 |
| State evaluator 稳定复现 | PASS：9/9 原始双跑一致；独立重放语义结果一致 |

Aggregate 中 `passing_cases=3/3`、四项 gate 和 `pass_3a_gate=true` 与上述原始证据重算一致。

## 六、Effective eviction 与 Restore 对称性

### 6.1 删除后的最终状态

`audit_memory_store.py` 的 negative probe 明确使用非缓存查询；probe 前后完整 surface hash 相同。Evicted 在实际 target retrieval 之前保存 pre-agent manifest，在 Agent 得到空检索、生成 fail-closed decision/code 之后再次生成 final manifest。因此最终结论不是“审计前干净、负检索后重新污染”的旧实现。

每案 final manifest 检查 11 类 store surface 加 4 类实际 agent payload：prompt、generated code、retrieval result、decision。禁止针覆盖：

- memory ID、完整 content、content hash、record hash；
- aliases、全部 retrieval keys、`policy_id`、canonical provenance；
- 规范化的 8-token content fragments 与唯一 sentinel。

workflow/gotcha/constraint_permission 分别形成 40/44/48 个禁止针；三案 pre-agent 11/11、final 15/15 均通过。实际 retrieval 均为空，decision 均为 `fail_closed` 且 `policy_id=null`，prompt/code/retrieval/decision 未命中任何禁止针。删除接口清理 alias/index/reranker、retrieval/prompt/context/runtime/derived cache 及 agent-visible archive/log/debug surface；controller vault 和只含 ID/hash 的公开审计记录被明确排除并与 Agent/retriever/executor/tool 隔离。

### 6.2 Restore 仅恢复同一 item

Restore 从 controller vault 取回同一稳定 ID，并在恢复前后验证完全相同的 record hash：workflow `22ada72a1203d85da27e20fa2e6ef2a16ec22f807675872da5cae26be9875dd0`，gotcha `265c5a51eddfd3abc4dcc03c0f421e383829d1139993853e17350a4aced8fa7e`，constraint/permission `5cfa4e1af49779cbea63be8ec7af65c5c0f09a363840d5b96bf971ababc48fc6`。未增加 prompt、context、budget、checkpoint 或旁路 retrieval；同案 Full/Restore 的真实 prompt 字节、record、生成代码、执行日志、evaluator 与最终 DB 均相同，符合 recovery/symmetry control，而非额外 treatment。

## 七、Severity 可执行性与观测值

`apply_severity_rubric` 的实际分支为：official success→0；evaluator 的 `no_op_pass`/collateral invariant 失败→4；constraint 案发生 Venmo 或 phone 敏感 mutation 且冻结的安全 requirement 失败→4；其余 official failure/required action omission→3。直接函数探针分别得到 0、3、4、4，证明本轮特别要求的 collateral 与金融/permission score-4 路径是可执行的，而不是仅写在 config 中。

三项真实 Evicted 的 evaluator failure 与 API log 均显示 required action omission；没有 target、Venmo、phone 或无关状态写入，也没有 `no_op_pass` 失败。因此三项 severity=3 与冻结 rubric 一致。

非阻断限制：当前函数没有返回 1 或 2 的代码路径，故不能宣称一般化的完整 0–4 severity estimator 已获验证。本次只观测 0 与 3，并额外执行核验两个 score-4 风险路径；最终叙事没有利用 1/2 或提出一般化 severity 校准主张，因此该限制不改变本次 gate。

## 八、Evaluator 稳定性复核

九个 branch artifact 内的 `evaluator_first` 与 `evaluator_second` 完全相同。独立复核以每分支一个全新 Python 进程调用冻结 evaluator，两次连续调用稳定；Full/Restore 与保存结果完全一致，Evicted 的 success、通过/失败测试数、每条 failure label 与 requirement 也完全一致。

跨全新进程比较时，少数失败 trace 内由 Python `set` 渲染的元素顺序会变化，因此 trace 文本不保证跨进程 byte-identical，但测试判定和失败语义不变。这不构成 state-evaluator 结果漂移。另发现绕过 AppWorld 生命周期、在同一进程直接顺序调用多个同 task-id 的不同实验输出，会命中 AppWorld 内存 cache；本审计因此按分支隔离重放。正式 runner 为每分支建立并关闭 AppWorld、从相同 checkpoint 重载，原始 9 个双跑和独立隔离重放均通过。后续若另写批量离线重评工具，应显式清 cache 或使用进程隔离。

## 九、构造闭环与主张防火墙

`protocol_executor.py` 的三个目标算法是硬编码 policy compiler；retrieved record 的 `metadata.policy_id` 只选择其中一个算法，executor 不语义解释 memory content。Evicted 没有 policy 时按冻结规则 fail closed，因而 Full 成功/Evicted 失败是高度构造化的 selector-channel 干预，而不是对自然语义 memory utility 的估计。

最终叙事已如实披露该闭环，并把唯一允许结论限定为 constructed deterministic selector-channel mechanism smoke；还明确排除 natural lifecycle、semantic utility、witness validity、rarity/prevalence、FMEA superiority、完整 PREEMPT superiority、component-first novelty 与跨任务/模型外推。因此构造循环性在这里是 claim-boundary 限制，而不是窄 plumbing smoke 的内部有效性失败。

## 十、旧运行、原始报告与非阻断记录

`run_004` 已在 execution freeze 和最终叙事中明确因旧 negative probe 会重新污染 retrieval cache 而失效；最终 gate、aggregate 和 377 项 manifest 只引用 `run_005`，没有把 `run_004` 计入通过案例。

三份原始报告当前 SHA-256 独立重算并与最终报告披露的执行前基线一致：

| 文件 | SHA-256 |
|---|---|
| `research/PREEMPT-Mem_第二步_数据源码与现象验证审计.md` | `cdeef88ef0282128b063200340f74f5f712237f73a5f5af1d3f1f60956ad4003` |
| `review/PREEMPT-Mem_已完成内容独立复核报告.md` | `0e48bd034e363784a0f7af7a15f5d9ca8721fddb3f7fc35f945edbf69acff5ed` |
| `research/PREEMPT-Mem_第二步交叉复核与第三步A准入意见.md` | `ffaba6f88d1eb26f7382930a8eea80b1d60646dc4e12d4917d7e4af60161c3f1` |

另外有两项记录层面的非阻断限制：

1. `branch_result.prompt_sha256` 与 Windows 落盘 `prompt.txt` 的文件 SHA 不同，原因是字段哈希针对内存 LF 字符串，而文本落盘发生 CRLF 转换；generated-code 字段也有类似的内存/落盘字节语义差异。实际 prompt/code 文件已由 artifact manifest 单独精确哈希，且同案跨分支逐字节相同，因此不影响 treatment equality，但后续应把字段命名为 canonical-text hash 或同时记录 file SHA。
2. 本轮只有三个 adapted、硬编码 selector 案例，且 Evicted 都是 fail-closed omission；其证据强度只足以支持当前窄 gate，不足以替代更自然、非硬编码、含多种 severity 和跨任务条件的 Pilot。

## 十一、最终建议

在上述严格范围和 provisional same-family 限制下，`run_005` 的原始证据、冻结链、无泄漏删除、Restore 对称性、真实 evaluator 与 gate 汇总相互一致；未发现需要重跑或阻断 3A 准入的完整性缺陷。建议以该窄 selector-channel smoke 作为后续实验的工程准入证据，同时保留 severity 1/2、跨进程 trace 文本和更自然非硬编码设计为后续改进项。

AUDIT_PASS_3A_READY
