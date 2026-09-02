# PREEMPT-Mem 第三步 A 独立复核报告

- 日期：2026-09-01
- 复核性质：独立、只读、证据优先；未修改被审查的报告、源码、配置或 `run_reproduction_001`
- 主证据运行：`third_step_a/artifacts/smoke/run_reproduction_001`
- 结论适用范围：仅限 **constructed deterministic selector-channel mechanism smoke**
- 复核独立性：`same-family`，语义判断按技能规范标记为 `provisional`；文件哈希、JSON/JSONL、数据库状态、evaluator vector 与 gate 另作确定性复算
- Pilot 状态：未启动 40-memory Pilot

## 一、判决摘要

第三步 A 的**数值证据链和原始 artifact 完整性通过复算**：377 项 manifest 全部匹配；三个案例均得到稳定的 Full/Evicted/Restore = `T/F/T`；两次官方 evaluator 在每个分支内一致；Full 与 Restore 的最终数据库逐字节相同；三个分支从同一 case checkpoint 启动；`run_reproduction_001` 有充分证据支持为一次新的确定性重跑，而非直接复用旧输出。

但是，第三步 A 的**agent-visible 因果隔离不成立**。`world.execute()` 在与 runner 相同的 Python/IPython 进程中执行，AppWorld 安全层允许 `inspect` 和 `pathlib.Path.read_text`。本轮新建的最小只读 capability probe 实际证明，执行代码能够：

1. 读取 `world.execute()` 调用者的局部 secret；
2. 读取在 agent 执行前写盘的 `target_relationship.json`，其中包含 `need_label`、`gold_state_evaluator` 和 `severity_application`；
3. 从调用栈取得 runner 的 `world` 对象，并访问已用 `ground_truth_mode="full"` 加载的官方 ground truth/evaluation code。

因此，在 capability 层，Full/Evicted/Restore 并非只有目标 memory 可达性不同；branch、Need、severity、gold/evaluator 私有状态均可被执行代码取得。虽然现有九份 frozen generated code **没有实际利用**这些通道，数值结果也没有被发现伪造，但这仍直接命中本轮规定的“信息泄漏/非唯一处理差异”阻断条件。第三步 B 必须等待隔离修复并重新运行第三步 A Smoke。

## 二、完整读取范围与方法

### 2.1 指定输入

已完整读取：

1. `research/PREEMPT-Mem_第二步交叉复核与第三步A准入意见.md`
2. `research/PREEMPT-Mem_第二步结论修订附录.md`
3. `research/PREEMPT-Mem_第三步A_AppWorld结构与三分支Smoke审计.md`
4. `research/PREEMPT-Mem_第三步A_复现实证补充_2026-09-01.md`
5. `third_step_a/src/audit_memory_store.py`
6. `third_step_a/src/run_smoke_case.py`
7. `third_step_a/config/cases_v3.json`
8. `third_step_a/env-spec.json`
9. `.aris/compute/local.md`
10. `third_step_a/artifacts/smoke/run_reproduction_001` 下全部 378 个文件。

为核查真实执行边界，还只读检查了冻结依赖中的 `protocol_executor.py`、`aggregate_smoke.py`、三案官方 `specs.json`、`test_data.json`、`evaluation.py`、source/target `solution.py`，以及 AppWorld 的 `environment.py`、`safety_guard.py`、`ground_truth.py`。

### 2.2 原始证据读取与独立复算

- 全目录：378 文件，1,539,594 bytes。
- 结构化证据：90/90 JSON 可解析；225/225 JSONL 可解析，共 2,186 行；9/9 Python 文件可作 AST 解析。
- `artifact_manifest.json` 声明 377 项，正好覆盖除 manifest 自身外的全部文件；缺失、额外、重复、size 错误、SHA-256 错误均为 0。
- manifest 自身 SHA-256：`3499cd4ac64f6ca663945a6ece6167240b643354eb9a94680c0c32fbd075fa52`。它未被外部签名或可信时间戳锚定，因此只能证明证据包内部闭合，不能单独证明外部真实性。
- reproduction execution freeze SHA-256：`7c4e7ed2996cbace47ef1ac9625531368cf1bb695704ee8d63f62ee57e5f5efa`；21 个冻结文件及三案各 41 项 freeze validation 均匹配。
- 数据库复算采用原始 JSONL 行多重集和逐文件字节比较；evaluator vector 从原始 report/trace/branch result 三方交叉重建；aggregate gate 从三个 case summary 重建，不信任已有总表布尔值。

## 三、核心证据复算结果

### 3.1 九分支 evaluator、API 和 severity

| Case | Branch | Official success | Passed/Failed | API calls | Severity | Eviction checks |
|---|---|---:|---:|---:|---:|---:|
| workflow | Full | true | 8/0 | 67 | 0 | n/a |
| workflow | Evicted | false | 2/6 | 1 | 3 | 15/15 PASS |
| workflow | Restore | true | 8/0 | 67 | 0 | 11/11 restore-delete PASS |
| gotcha | Full | true | 5/0 | 125 | 0 | n/a |
| gotcha | Evicted | false | 2/3 | 1 | 3 | 15/15 PASS |
| gotcha | Restore | true | 5/0 | 125 | 0 | 11/11 restore-delete PASS |
| constraint_permission | Full | true | 10/0 | 27 | 0 | n/a |
| constraint_permission | Evicted | false | 2/8 | 1 | 3 | 15/15 PASS |
| constraint_permission | Restore | true | 10/0 | 27 | 0 | 11/11 restore-delete PASS |

每个分支的两次 evaluator 调用逐结构一致，三个 case 的成功向量均为 `[true, false, true]`。Evicted 的一次 API call 是 fail-closed `complete_task(status="fail")`；`task_completed_flag=true` 只表示任务进入终态，不等于成功，现有 gate 正确使用 `official_success`。

### 3.2 同 snapshot 与 DB diff

- 同一 case 的三个分支 checkpoint tree SHA-256 完全相同，prompt 逻辑哈希完全相同；分支 checkpoint 均由同一 base checkpoint 字节复制并在执行前校验。
- workflow：checkpoint→Full/Restore 各增加 32 条状态记录，checkpoint→Evicted 增加 1 条；Full↔Restore 全 DB 文件逐字节相同。
- gotcha：对应为 126、1、126；Full↔Restore 全 DB 文件逐字节相同。
- constraint_permission：对应为 11、1、11；Full↔Restore 全 DB 文件逐字节相同。
- 三份 `database_state_diff.json` 的 15 个 comparison 中，左右文件 SHA、`byte_equal`、removed/added 计数和完整 record 数组均可从原始快照重算，15/15 匹配。

### 3.3 Restore 的对象同一性

`AuditMemoryStore.restore()` 只按同一 `memory_id` 从 controller vault 取回一个冻结对象，并校验恢复后的 `record_sha256`（`audit_memory_store.py:210-219`）。三案均满足：

`Full.memory_put.record_sha256 == Restore.memory_restore.record_sha256 == source candidate_record_sha256`

同时，Full/Restore 的 retrieval result、generated code、API call 数、两次 evaluator 和最终 DB 全部相同。就本次单记录 frozen harness 而言，没有发现 Restore 注入第二条记录、额外 prompt 或额外任务状态。

### 3.4 Aggregate gate

三个 `case_summary.json` 均可从对应三分支原始结果重建；由此独立得到 `passing_cases=3`、`total_cases=3`、`pass_3a_gate=true`，与 `aggregate_gate.json` 一致。现有 aggregator 自身仍过度信任 summary 中若干布尔字段，见第六节 required fixes。

### 3.5 官方 evaluator 真实性

三个 target 分别使用 AppWorld 官方任务 `6c2c621_2`、`68ee2c9_2`、`530b157_2` 的状态型 `evaluation.py` 和 `test_data.json`。未发现 fake GT、self-normalization、phantom result 或把自造分数当官方成功的情形。Need=1 是 constructed protocol label，witness 是 frozen protocol fixture，二者没有作为当前 generated code 或 evaluator 的显式参数。

## 四、runner / selector / config / evaluator 硬编码审计

### 4.1 未发现的硬编码

- `protocol_executor.compile_agent_code()` 不接收 branch 名；未发现 `if Full/Evicted/Restore`、按 memory ID 选择预期结果、按 evaluator label 选择成功/失败代码。
- target 官方 `specs/test_data/evaluation` 未出现本实验 memory ID、policy ID、alias、retrieval key 或 sentinel。
- runner 的 branch 条件位于 `run_smoke_case.py:495-500`，用于执行规定的 delete/restore 干预；官方 evaluator 在 `world.execute()` 后调用。未发现 evaluator 根据 branch 改写结果。
- 实际九份 `generated_code.py` 均未读取 witness、Need、severity、GT 或 evaluator 私有文件。

### 4.2 明确存在但已披露的 selector 硬编码

`cases_v3.json:4-7` 明示 mechanism claim 与禁止的 semantic-memory-utility claim；三条 memory 的 `metadata.policy_id` 在 `protocol_executor.py:186-221` 中直接选择三个冻结任务族编译器，无 retrieval 或未知 policy 必定 fail-closed。三个 source/target 官方 `solution.py` 对还分别字节相同。

因此，`Full−Evicted` 只证明“外部 selector record 的可达性能够门控冻结执行器”，不能证明 content 的语义解释、学习、自然记忆生命周期或一般 Agent utility。这一硬编码在当前窄 claim 下不单独构成 BLOCK；任何更宽解释都会构成不可接受的过度外推。

Prompt 也未被模型消费：runner 保存相同 prompt，但编译器直接接收 target instruction 和 retrieval result 后输出冻结代码。因此 prompt equality 只是形式控制，不是 LLM-agent 控制。

## 五、阻断性发现：agent-visible firewall 可实际绕过

### 5.1 静态因果链

1. runner 以 `ground_truth_mode="full"` 创建执行 world（`run_smoke_case.py:412`）。AppWorld `GroundTruth` 对象包含 `private_data`、`answer`、`evaluation_code`、`solution_code`、`compiled_solution_code`、`test_data`（`ground_truth.py:38-61,297-375`）。
2. runner 在 `world.execute(generated_code)`（`run_smoke_case.py:533`）之前，写出：
   - `target_relationship.json`，含 Need、gold evaluator 摘要与 severity（`run_smoke_case.py:447-455`）；
   - `witness.json`（`:457`）；
   - branch 目录、eviction manifest 和其他 controller artifacts（`:468-531`）。
3. AppWorld 将代码交给同进程 IPython shell（`environment.py:945-965,1039`）。
4. safety guard 明确允许导入 `inspect`（`safety_guard.py:177-217`），并把 `pathlib.Path.read_text` 留在允许状态（`:80-84`）；只读 `open` 也被允许。`controller_vault_disclosed_to_agent=false` 只是 manifest 中的声明（`audit_memory_store.py:349-356`），不是进程或 capability 隔离。

### 5.2 新鲜 capability probe

本轮未修改旧证据；在新的 AppWorld experiment 输出目录运行最小探针：

`third_step_a/appworld_root/experiments/outputs/preempt3a_independent_audit_capability_probe_31aad86d`

原始交互日志：

`tasks/6c2c621_2/logs/environment_io.md`

该日志 SHA-256：

`af9b757c8ea5be7465e73927b6a3b7317c0c1ebe4ab761dccbc1d080b05104e6`

探针使用与 frozen runner 相同的 `ground_truth_mode="full"` 和 `timeout_seconds=null`，仅运行 `inspect.stack()`、`Path.read_text()` 与只读属性访问。原始输出为：

```text
CALLER_SECRET=PREEMPT_CALLER_SECRET_7F2C
REL_KEYS=gold_state_evaluator,need_definition,need_label,severity_application,source_to_target_dependency,target
CALLER_WORLD=True
GT_PRESENT=True
GT_EVAL_CHARS=3516
```

这证明 agent execution code 可实际取得调用者局部变量、审计文件中的 Need/severity/gold 标签以及完整 GT 对象，不是纯静态猜测。runner 的局部 `branch`、`case`、`record`、`store`、`witness`、`world` 也处在同一可遍历调用栈上；branch-specific experiment/output path 同样可观察。

### 5.3 对当前结果与判决的含义

- 当前九份冻结代码没有利用上述路径；因此不能据此断言现有 `T/F/T` 是伪造结果。
- 但本轮协议要求的是“只有目标 memory 可达性不同”和“agent-visible 私有标签不泄漏”。这两个要求是 capability/causal isolation 要求，而不是“恰好没有调用泄漏 API”的行为观察。
- 一个自由代码 Agent 可直接读取 branch 或官方 evaluator 私有信息，绕过 memory treatment。Full/Evicted/Restore 由此存在目标 memory 以外的可观察差异和结果捷径。
- 该缺陷同时命中用户给定的 information leakage 与 non-unique treatment difference BLOCK 条件，不能降格为日志组织或措辞问题。

## 六、effective eviction 的覆盖与其他 required fixes

以下问题不改变第五节的阻断判决，但隔离修复后也必须处理。

### RF-1：在独立进程/RPC 边界重建 agent firewall（解除 BLOCK 的必要条件）

- agent 进程只获得：相同 target instruction/prompt、最小 memory retrieval RPC、AppWorld public API gateway；不得挂载项目、GT、controller artifacts 或 runner 调用栈。
- agent 执行 world 使用 `load_ground_truth=false` 或等价最小模式；官方 evaluator 在 agent 退出并冻结 DB 后，于另一进程加载 GT。
- `target_relationship.json`、witness、severity、eviction manifest 等私有审计材料只能写入 agent 不可访问的位置，或在 agent 完成后生成。
- 加入强制负探针：`inspect.stack`、`Path.read_text`、目录枚举、caller/world/store/vault/GT 访问均必须失败；失败日志须入新 manifest。
- 完成后从同一新冻结 snapshot 重跑三案 Full/Evicted/Restore，不能沿用本轮九分支结果解除 BLOCK。

### RF-2：15 项检查目前没有覆盖真实 agent capability surface

Evicted 的 15 项由 2 个 retrieval probe、9 个 in-memory store payload 类别以及 4 个实际 prompt/code/retrieval/decision payload 检查构成。它们对 frozen exact ID/content/hash/alias/key/policy/provenance/sentinel 和规范化 8-gram 的复算结果确为 15/15 PASS。

但是：

- near-duplicate、真实 embedding、非空 graph edge、tool cache、active prompt/scratchpad/session/KV、runtime、多数 derived artifacts、archive/log/debug 在本次 fixture 中为空或仅为模拟字典，很多 PASS 是 vacuous absence；
- 扫描不覆盖真实 Python locals、caller frame、controller vault、项目文件、AppWorld logs/GT；
- exact/8-gram needle 不能检测语义改写或未经建模的派生依赖；
- artifact 主要保存 hash/PASS 标签，没有保存可安全复核的脱敏 payload/provenance closure。

修复后应为每类 surface 提供正向污染 fixture，证明 put 会填充、delete 会只清目标依赖；并把真实 capability surface 纳入 manifest。

### RF-3：多 memory 下的唯一处理性尚不成立

独立双记录动态探针发现：

- 删除 target 时，`delete()` 在 `audit_memory_store.py:195-207` 全量清空 retrieval/tool/summary cache、active context、runtime、archive/log/debug，而不只移除 target 的派生依赖；这会同时改变 distractor/non-target 状态。
- 保留第二条 `MemoryRecord` 后调用 `effective_eviction_manifest()`，`canonical_json()` 会因 `MemoryRecord`（以及非空 set）不可 JSON 序列化而抛出 `TypeError`；本轮单记录删除后容器为空，因而没有触发。

所以当前实现只验证了“一案只挂载一个 record”的 3A fixture，不能直接进入多 memory 3B/Pilot。需实现 target-scoped dependency invalidation、稳定 canonical serializer，并加入至少 target+distractor 的非目标 surface 全等断言。

### RF-4：aggregate gate 应从原始证据重算

`aggregate_smoke.py` 目前信任 case summary 中若干 Full/Restore DB equality 与 pass 布尔值，也未自行要求 Restore 删除阶段的全部 manifest。本轮人工重算结果正确，但 gate 本身应直接读取快照、branch artifacts、evaluator vectors 和 manifest 后再判定。

### RF-5：哈希字段语义需修正

`branch_result.json` 的 `prompt_sha256` 和 `generated_code_sha256` 是写盘前 LF 逻辑字符串哈希，不是 Windows 磁盘文件字节哈希。例如 workflow Full：逻辑 prompt 为 `309164...`，文件字节为 `bdbcd8...`。artifact manifest 的真实文件 SHA 是正确的。应将字段重命名为 `*_logical_lf_sha256`，并新增 post-write `*_file_sha256`。

### RF-6：证据包敏感字段必须脱敏

六个 Full/Restore `api_calls.jsonl` 合计可检出 410 个 bearer/JWT occurrence，并含 password、用户名、电话、收款邮箱、金额及 message/content。它不是本次 Evicted memory 泄漏的因果来源，但证据共享前必须做确定性脱敏，同时保存受控原件或结构化 hash 以便复核。

### RF-7：freeze 与 fresh-run attestation 加强

当前 freeze 足以重算本轮引用文件，但尚未以完整树清单冻结 vendor 源、target DB 输入树和全部 GT 输入；manifest 也未签名。新运行应绑定 precommitted nonce、argv、开始/结束事件、源码/数据/环境完整树 hash 和最终 artifact Merkle/root hash。固定 `PYTHONHASHSEED` 或规范化 evaluator 的 set/dict trace，以消除跨进程失败 trace 的字节漂移。

## 七、fresh reproduction 独立性判断

`run_reproduction_001` 与 `run_005` 相对路径集合完全相同，351/378 文件逐字节相同，27 个文件不同。差异集中在 run/freeze/path 元数据、manifest，以及三个 Evicted evaluator 的无序 set 诊断；稳定语义字段、DB、evaluator vector 和 severity 相同。

时间与现场目录证据显示：

- reproduction freeze 先于新 run；
- `run_005` 文件时间窗为 2026-08-27；`run_reproduction_001` 为 2026-09-01，呈 workflow→gotcha→constraint、各自 Full→Evicted→Restore 的连续创建波次；
- AppWorld outputs 下存在 12 个新的 `preempt3a_run_reproduction_001_*` experiment 目录；
- Evicted trace 的无序诊断与旧 run 不同，而稳定结果相同。

最合理结论是：它是**独立于旧输出的一次 fresh deterministic re-execution**。但它使用同一实现、同一 harness 和同一数据，不是独立重实现；未签名时间戳也不能排除精心 copy-and-rewrite。报告不得把它表述为跨实现或密码学证明的独立复现。

## 八、允许与禁止的科学结论

若修复第五节隔离缺陷并重跑，现有设计最多可支持：

> 在三个 adapted/constructed AppWorld 案例、一个冻结 deterministic policy-ID selector harness 中，单个外部 selector record 的可达性门控了 frozen executor；删除导致 fail-closed 与官方状态失败，恢复同一 record 恢复原结果。

本轮证据不支持：

- semantic memory understanding/utility；
- 学习型或自由代码 Agent 的记忆收益；
- witness validity 或自然生命周期；
- PREEMPT 完整方法优越性；
- prevalence/rarity；
- 跨任务、跨模型、跨 seed 泛化；
- 进入完整 40-memory Pilot。

## 九、最终判决

BLOCK_3B
