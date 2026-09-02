# PREEMPT-Mem 第三步 A-R：隔离修复与重跑报告

日期：2026-09-01  
阶段：第三步 A-R（agent-visible firewall / causal isolation 修复）  
状态：`PASS_3A_R_READY_FOR_INDEPENDENT_AUDIT`（项目内确定性门禁；不是独立复核判决）  
结论范围：**constructed deterministic selector-channel mechanism smoke only**  
Pilot：未启动

## 1. 执行范围与前置判决

本轮接受《PREEMPT-Mem_第三步A_独立复核报告_2026-09-01.md》的 `BLOCK_3B`，不以既有 generated code 是否实际利用泄漏为抗辩。修复对象是 capability-level 因果隔离：旧 runner 与 Agent 同进程、同调用栈、可见 controller 私有对象所造成的能力泄漏。

本轮没有重新选题、没有更换 AppWorld、没有修改或覆盖 `run_reproduction_001`，也没有启动 40-memory Pilot、3B、训练或付费扩展实验。旧审计与旧证据在 final 后复核仍保持：

| 旧锚点 | SHA-256 / 状态 |
|---|---|
| `research/PREEMPT-Mem_第三步A_独立复核报告_2026-09-01.md` | `70b10c5e689b2c6532d3dcadf57c1e429ef5dfde65c3b6ede81a7b17bd57c05c` |
| `research/PREEMPT-Mem_第三步A_AppWorld结构与三分支Smoke审计.md` | `1bce060ae041d4b6d15a1a2541805bf07e04c963e0f3ec0794311cc89f067827` |
| `research/PREEMPT-Mem_第三步A_复现实证补充_2026-09-01.md` | `8e6ab69c142bf5c4519e8df5aa12492d3260d6328f09105519d6fb3a0ac0576b` |
| `run_reproduction_001/artifact_manifest.json` | `3499cd4ac64f6ca663945a6ece6167240b643354eb9a94680c0c32fbd075fa52` |
| `run_reproduction_001` 物理文件 | 378 files，1,539,594 bytes，未改变 |

## 2. 隔离架构

### 2.1 可信面与 Agent 面

可信 controller 持有 branch、memory store、target relationship、Need、severity、witness、gold evaluator、eviction manifest、restore vault、AppWorld world 与审计 canary。Agent 不接收这些对象或其引用。

```text
controller private plane
  ├─ target-scoped memory store / restore vault
  ├─ branch assignment / canaries / audit state
  └─ AppWorld public-API gateway (exact per-case allowlist)
             │
             │ exact 4-field initialize + typed JSONL RPC
             ▼
fresh temp dir / external Python -I / copied structured Agent worker
             │
             │ only allowlisted app.api calls
             ▼
Agent AppWorld world (load_ground_truth = false)
             │ Agent exits; DB is copied and frozen
             ▼
two new evaluator processes per branch
  └─ only here load GT and call appworld.evaluator.evaluate_task
```

Agent worker 被复制到全新临时目录，以项目外的 base Python、`-I` 和 worker basename 启动；cwd 不在项目目录，argv 不含项目路径。Agent 初始化 JSON 严格只有 `type`、`protocol_version`、`target_instruction`、`retrieval_results` 四个字段。Full、Evicted、Restore 的 target instruction、prompt、checkpoint 和 allowlisted public tools 相同，唯一处理差异是目标 memory 的 retrieval 可达性：Full=1、Evicted=0、Restore=同一 item=1。

这是结构化 tool-call capability boundary，不是通用 Windows 任意代码或文件系统沙箱。任意 model-generated Python 执行被关闭；Agent 只能发 typed JSONL tool call，controller 只转发冻结的 AppWorld public `app.api` allowlist。该限定写入：

- `third_step_a/config/cases_isolated_v1.json`
- `third_step_a/env-spec-isolated-v1.json`
- `third_step_a/README.md`

### 2.2 GT 与 evaluator 进程隔离

每案先运行三分支 Agent，记录 PID/exit code 并冻结三份 DB；`case_agent_exit_barrier.json` 明确要求：三 Agent 已退出、三 DB 已冻结、私有审计 artifacts 未在 barrier 前写入。随后每个冻结 DB 启动两个独立 evaluator worker；18 个 evaluator 进程全部与 9 个 Agent PID、capability worker PID、controller PID 分离。

Evaluator worker 在设置 `APPWORLD_ROOT` 后、导入 AppWorld 前冻结 launch-environment key 集。AppWorld 导入后自行增加的 `APPWORLD_CACHE`、`TERMINAL_WIDTH` 不再被误报为 controller 启动能力。每个 worker 将 GT 加载入口、AppWorld module/file SHA、editable source、输入 DB tree before/after、PID、argv、环境键和完整 raw evaluator vector 写入 envelope；输入 DB before/after 必须完全相同。

### 2.3 私有信息写入时序

在 Agent 运行前，run 中不存在 target relationship、Need、severity、witness、gold evaluator 或 effective-eviction manifest。三 Agent 退出并经过 barrier 后，controller 才读取 witness/relationship、执行 raw in-memory firewall scan并写入私有审计 artifacts。

Raw pre-redaction transcript/final result 只存在于冻结 controller 内存：scan 后立即删除，不进入共享 run。可复核 artifact 是零匹配 attestation、private-needle 哈希与 virtual payload/transcript SHA。必须保留的证据边界是：sealed artifacts 不能独立重放已经删除的 raw payload；“raw 无泄漏”依赖冻结 controller 的内存扫描 attestation。Persisted redacted surfaces 则可由 aggregate 独立逐文件重扫。

## 3. 强制负向 capability probes

每案 × 每分支强制执行以下 10 项探针。探针返回 denied 才算 PASS；任意读取成功都会使 case fail closed。

| Probe | 预期 | final 结果（9 次/项） |
|---|---:|---:|
| caller secret | denied | 9/9 denied |
| inspect stack | denied | 9/9 denied |
| branch | denied | 9/9 denied |
| project file | denied | 9/9 denied |
| world object | denied | 9/9 denied |
| memory store | denied | 9/9 denied |
| controller vault | denied | 9/9 denied |
| ground truth | denied | 9/9 denied |
| evaluation code | denied | 9/9 denied |
| controller directory | denied | 9/9 denied |

合计 90/90 denied。每分支保存 `capability_probes.json`、`capability_probe_rpc_transcript.jsonl`、`capability_process_attestation.json`；aggregate 重新解析 transcript、校验 exact probe set、worker envelope、PID 与所有 denied 结果，不信任 `all_pass` 声明字段。

## 4. target-scoped effective eviction 与 serializer

### 4.1 双记录依赖失效

`AuditMemoryStore` 同时装入 target 与 distractor。删除 target 时，算法按显式 `depends_on_memory_ids`、target-unique identifiers/hashes/aliases/keys/provenance/sentinels 和共享所有权做 target-scoped pruning；共享内容、ANN collision、keyword/cache membership 只移除 target member，distractor member 保留。对无 scope 的 legacy summary 采用 target-unique fallback；嵌套 target declaration 不能隐藏在 distractor 外层 mapping 下。

独立 target+distractor probe 覆盖 9 个 surface groups、25 个 concrete components：

1. canonical record；
2. aliases / near-duplicates；
3. embedding / ANN / keyword / graph；
4. reranker features；
5. retrieval / tool / summary caches；
6. active prompt / scratchpad / session / KV；
7. runtime variables；
8. derived summary/rule/skill/plan/edge/tag/cached answer；
9. Agent-accessible archives/logs/debug endpoints。

结果：target 25/25 components 删除后不可达；distractor 9/9 surface groups 删除前后 canonical 等价；共享 ANN/keyword/cache collision、unscoped summary fallback、mixed nested dependency invalidation 全部通过；Restore 的 memory_id 与 record SHA 与原 target 完全相同，且没有额外 record。

证据：`third_step_a/artifacts/smoke/run_isolated_001/attestation/target_distractor_probe.json`，SHA-256=`283f14b3bdc983d5369b2410a5cf759c7555aae2f365b86332e453d386b0e136`。

### 4.2 Canonical serializer

Serializer 现支持非空 `MemoryRecord` dataclass、tuple、set、frozenset；set/frozenset 使用带 `__canonical_type__` 的排序表示，tuple 按 JSON array 表示；输入 mapping 禁止伪造保留的 `__canonical_type__`。Aggregate 的 source/candidate record 重算先转换为 canonical JSON-native mapping，避免 Python tuple 与持久化 JSON list 的假不等价。

36/36 单元测试通过，包含 reserved-tag spoof、非空 MemoryRecord/set、target+distractor、mixed nested invalidation、firewall path spoof、evaluator vector 与 artifact layout 回归测试。

## 5. Firewall、脱敏与 aggregate 重算

### 5.1 Agent-visible firewall

Firewall 同时执行 exact private-string needle scan 与 recursive forbidden-key scan。`relationship(s)` 只在实际结构路径 `raw/agent_rpc_transcript/<index>/response/result/...` 或持久化 RPC 对应路径下允许，授权判断使用 tuple path components，不解析 Agent-controlled key 文本。原 PoC `spoof.agent_rpc_transcript[0].response.result` 已加入回归测试并被 runner/aggregate 同时拒绝。

Final 重算结果：

- raw controller-memory scan：private exact matches=0，forbidden private keys=0；
- persisted Agent-visible surfaces：private exact matches=0，forbidden private keys=0；
- 3 案 × 21 persisted surfaces=63 surface scans 全通过；
- branch canary、nonce commitment 与写入时序全部一致。

### 5.2 敏感 API 日志

Raw AppWorld API log 不保留在 shareable run。RPC response 与 controller evidence 使用 `sha256(run_nonce || kind || canonical_value)[:16]` 生成确定性 redaction marker；protocol tool name 不被重写。9 分支共保留 445 行 redacted API evidence，执行 2,621 次 value redaction；aggregate 对 redaction count、row count、file SHA、nonce commitment、raw-not-retained 和 post-redaction sensitive findings 重新核验，9/9 `sensitive_logs_redacted=true`。

### 5.3 Aggregate 不信任 summary

`aggregate_smoke.py` 不读取 `case_summary.json` 的判定布尔值。它从以下来源重算：execution freeze、precommit nonce/source/data/environment attestation、exact artifact layout、checkpoint trees、Agent init/request/final/transcript、DB snapshots、两个 evaluator vectors/envelopes、capability transcripts、effective-eviction manifests、firewall manifests、redaction attestations、target+distractor fresh recomputation。

Aggregate 使用 exact-key schema 约束 controller invocation、Agent request/final、branch result、process/envelope、DB freeze、checkpoint、barrier、evaluator vectors 与 redaction rows；额外/缺失字段均 fail closed。Logical LF SHA 与 physical file SHA 分列保存和验证。

## 6. `run_isolated_001` 三案结果

| Case | Full | Evicted | Restore | Full tests | Evicted tests | Restore tests | Full=Restore DB | Full=Restore evaluator |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| workflow | PASS | FAIL | PASS | 8/8 | 2/8 | 8/8 | 是 | 是 |
| gotcha | PASS | FAIL | PASS | 5/5 | 2/5 | 5/5 | 是 | 是 |
| constraint/permission | PASS | FAIL | PASS | 10/10 | 2/10 | 10/10 | 是 | 是 |

三个 case 均满足主要效应 Full−Evicted；Restore 仅作为 recovery/symmetry control。三分支来自同一 case checkpoint；每案 Full/Restore 的 checkpoint、structured plan、RPC transcript、DB tree 与 official evaluator vector 对称。Evicted DB 与 Full 不同且 official evaluator 失败，方向与预注册 smoke contract 一致。

DB tree roots：

| Case | Full / Restore root | Evicted root |
|---|---|---|
| workflow | `f129a9ab8bbb4810edbca0fb5f781e3e6bf50a78221cf51e2e1f7cd06722f36f` | `24ede104b478c45a7d346fba841cc54ff0661744c056e935b7243816a7398c9a` |
| gotcha | `b7c5d05e754c789488ce0775e421cf83319f7b7d91db8631437d77f7a6534081` | `a53839ca64cf5da0269fdd52f839dd79d643cdd0c6e948bd3b0dbc80a46ea9d0` |
| constraint/permission | `f7faa8d0449d0462de82ec3eb05895899c3b116dd94d017eed9ced91ef634986` | `3b00d6c1a57cb0ba02a89cd478a0668f4780420ad0503a1c3ce9645608b8e9c7` |

Evaluator 每个分支运行两次，共 18 个进程。9/9 semantic vectors 相等；7/9 raw vectors 完全相等。workflow-Evicted 与 constraint/permission-Evicted 的两份 raw vector 只在 `failures[*].trace` 内 Python set repr 顺序不同；两份 raw 文件与完整 worker envelope 均保留并 hash-bound，aggregate 只从相等判定中排除此诊断字符串，仍精确比较 success、difficulty、num_tests、pass/failure label 与 requirement multiset。

六份 effective-eviction manifest（每案 Evicted + Restore intermediate delete）各含 36 项检查，共 216/216 PASS，dependency scope 均为 `target_only`。

## 7. Source、data、environment 与 artifact attestation

Final precommit 重新核验：

- harness source：18 files，452,106 bytes，tree root `aa83c891db273880446ec90f22543de1b2df5688c9c1a673968604d93b455097`；
- AppWorld source：798 files，26,791,070 bytes，commit `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`；
- AppWorld data：14,885 files，174,032,410 bytes，version `0.2.0`；
- Python 3.12.13 executable SHA-256 `560b9ef7d856608ab8da02ded2dc8a1951ad1f424c382c0ec6a698874165a18e`；
- AppWorld editable distribution/module、79 项 dependency snapshot 与 7 个 critical distribution version 均绑定；
- network dependencies=[]，Pilot=false。

关键锚点：

| Artifact | SHA-256 / root |
|---|---|
| `execution_freeze_run_isolated_001.json` | `649f86faea21c1c3c8c1fd6d4398be44cf408c96124ea99abcab4514d05e4fed` |
| `precommit_run_isolated_001.json` file SHA | `3a62639acf5e47c93249b6c799d6a17fed5be1376c810cfb5a8103d5e5e66e62` |
| precommit nonce commitment | `edea888497cbe7c10ec21999ea014c52d17e973080ea3a33ba9cab864f9ab855` |
| `pre_aggregate_artifact_manifest.json` | `38e5c841d3bb4cf70634b36ccc778e8418ab038aa1c967cd5451dc27accb7222` |
| pre-aggregate manifest root | `4b5bfc6ceef8610da8d8c6d77df657419c53d373ddb32ca87379723591f4a856` |
| `aggregate_gate.json` | `a5fc2c7b005cb76f8ccf953612a5a0ef29d1acc4a59edaf4e3f5b3bd0ae5f6c2` |
| `artifact_manifest.json` file SHA | `4988163e6774d1794e8cb4e1cbfecb0053879987ddb7fec97ff9598002f5deb7` |
| final manifest root | `d607e9f83938e0505d6d86269aa2aeb8b3d22fa840c650eefcf71d4ced819d75` |

Final manifest 覆盖 467 个 entries、2,439,465 bytes，不包含 manifest 自身；物理 run 为 468 files、2,529,502 bytes。Exact layout 重算得到 232 static files、234 snapshot files、32 static directories、0 unknown files、0 unknown directories。

## 8. 复现与排障记录

所有失败开发 run 均保留、未覆盖：

| Run | 复现错误 | 最小修复 |
|---|---|---|
| `_01` | source change 后 freeze stale | 每次 source change 强制新 freeze/run ID |
| `_02` | evaluator stdout locale decode | ASCII framed protocol + binary stdout/stderr capture |
| `_03`/`_04` | raw failure trace 中 set repr 顺序不稳定 | 保留 raw；只对明确的 trace 诊断字段做 semantic projection |
| `_05`/`_06` | Phone public response 的 `relationships` 与私有 key rule 假碰撞 | 仅在真实 public RPC result 的结构化 tuple path 白名单；加入 path-spoof regression |
| `_07` | AppWorld import 后新增 env key 被误报为 launch env | import 前冻结 evaluator launch environment |
| `_08` | 并行诊断使用 S:/T:/R: 导致严格 executable path 表示不同 | final 全流程统一 R:；不放宽路径 attestation |
| `_09` | `asdict()` tuple 与 JSON list 直接比较 | canonical JSON-native record mapping + regression test |

`third_step_a/diagnostics/continue_case_gate_after_source_change.py` 只用于开发时在 source fix 后只读继续 downstream gate，明确拒绝 `run_isolated_001`；标准 aggregate 没有 bypass 参数，并无条件先校验 freeze。Final 未使用 diagnostics bypass。

## 9. 完整 final 命令

当前 Codex runtime 会错误解码中文工作区绝对路径，因此用 `subst R:` 指向同一物理项目。三个 case 与 aggregate 全程使用相同 `R:`，没有复制、移动或覆盖项目。

```powershell
subst R: 'E:\科研\ICLR2027-PREEMPT-Mem'
Set-Location R:\
$env:PYTHONUTF8 = '1'
$env:PYTHONWARNINGS = 'ignore'
$env:PYTHONHASHSEED = '0'

& 'third_step_a/.venv/Scripts/python.exe' -m compileall -q third_step_a/src third_step_a/tests
& 'third_step_a/.venv/Scripts/python.exe' -m unittest discover -s third_step_a/tests -v

& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/make_isolated_freeze.py --run-id run_isolated_001 --case-config third_step_a/config/cases_isolated_v1.json --environment-spec third_step_a/env-spec-isolated-v1.json --output third_step_a/artifacts/execution_freeze_run_isolated_001.json
& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/make_isolated_attestation.py --run-id run_isolated_001 --case-config third_step_a/config/cases_isolated_v1.json --environment-spec third_step_a/env-spec-isolated-v1.json --execution-freeze third_step_a/artifacts/execution_freeze_run_isolated_001.json --witnesses third_step_a/artifacts/witnesses.json --output third_step_a/artifacts/precommit_run_isolated_001.json
& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/target_distractor_probe.py --output third_step_a/artifacts/smoke/run_isolated_001/attestation/target_distractor_probe.json

& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/run_isolated_smoke_case.py --config third_step_a/config/cases_isolated_v1.json --case workflow --run-id run_isolated_001 --witnesses third_step_a/artifacts/witnesses.json --execution-freeze third_step_a/artifacts/execution_freeze_run_isolated_001.json --precommit-attestation third_step_a/artifacts/precommit_run_isolated_001.json
& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/run_isolated_smoke_case.py --config third_step_a/config/cases_isolated_v1.json --case gotcha --run-id run_isolated_001 --witnesses third_step_a/artifacts/witnesses.json --execution-freeze third_step_a/artifacts/execution_freeze_run_isolated_001.json --precommit-attestation third_step_a/artifacts/precommit_run_isolated_001.json
& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/run_isolated_smoke_case.py --config third_step_a/config/cases_isolated_v1.json --case constraint_permission --run-id run_isolated_001 --witnesses third_step_a/artifacts/witnesses.json --execution-freeze third_step_a/artifacts/execution_freeze_run_isolated_001.json --precommit-attestation third_step_a/artifacts/precommit_run_isolated_001.json

& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/seal_run_evidence.py --run-root third_step_a/artifacts/smoke/run_isolated_001
& 'third_step_a/.venv/Scripts/python.exe' third_step_a/src/aggregate_smoke.py --run-root third_step_a/artifacts/smoke/run_isolated_001 --execution-freeze third_step_a/artifacts/execution_freeze_run_isolated_001.json --precommit-attestation third_step_a/artifacts/precommit_run_isolated_001.json

subst R: /D
```

实际三案可并行运行，但每条 argv 与 precommit 中的 planned argv 完全相同；seal 与 aggregate 在三案全部退出后串行执行。

## 10. 证据位置

- 总门禁：`third_step_a/artifacts/smoke/run_isolated_001/aggregate_gate.json`
- 完整 SHA-256 manifest：`third_step_a/artifacts/smoke/run_isolated_001/artifact_manifest.json`
- pre-aggregate seal：`third_step_a/artifacts/smoke/run_isolated_001/pre_aggregate_artifact_manifest.json`
- environment：`third_step_a/artifacts/smoke/run_isolated_001/environment.json`
- target+distractor：`third_step_a/artifacts/smoke/run_isolated_001/attestation/target_distractor_probe.json`
- 每案 controller/barrier/checkpoint/DB/firewall：`cases/<case>/controller_invocation.json`、`case_agent_exit_barrier.json`、`checkpoint_manifest.json`、`database_state_diff.json`、`raw_controller_firewall_scan.json`、`firewall_leakage_manifest.json`
- 每分支 Agent：`agent_initialize.json`、`agent_request.json`、`agent_final.redacted.json`、`agent_rpc_transcript.jsonl`、`agent_process_attestation.json`
- 每分支 capability：`capability_probes.json`、`capability_probe_rpc_transcript.jsonl`、`capability_process_attestation.json`
- 每分支 DB：`checkpoint_snapshot/`、`db_snapshot_frozen/`、`db_freeze_attestation.json`
- 每分支 evaluator：`evaluator_first.json`、`evaluator_second.json`、两个 `*_worker.json`、`evaluator_process_attestation.json`
- 每分支 API：`api_calls.redacted.jsonl`、`api_log_redaction_attestation.json`
- Evicted/Restore intermediate delete：`effective_eviction_manifest.json`

## 11. 本轮结论与停止条件

项目内 raw-evidence aggregate 通过 3/3 cases，得到 `PASS_3A_R_READY_FOR_INDEPENDENT_AUDIT`。该结论只说明：在冻结的 AppWorld dev snapshots、非学习的 deterministic structured-tool Agent 和 constructed selector channel 下，目标 external addressable memory 的可达性足以产生三个预注册 Full−Evicted smoke effects，Restore 恢复同一 item 并复现 Full。

它不支持“通用语义 memory 有效”、自然 lifecycle、发生率、模型泛化、完整 PREEMPT-Mem claim 或 3B/Pilot 结论。至此停止，提交新的独立复核；不启动 3B 或 40-memory Pilot。
