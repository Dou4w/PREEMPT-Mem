# PREEMPT-Mem 第三步 A 复现实证补充

> 日期：2026-09-01  
> 复现对象：`third_step_a/artifacts/smoke/run_005` 的冻结 AppWorld 三分支 Smoke  
> 新复现：`third_step_a/artifacts/smoke/run_reproduction_001`  
> 结论边界：仅为 adapted + constructed/semi-synthetic 的 deterministic selector-channel mechanism smoke。

## 1. 本轮动作与保护边界

本轮完整读取了 2026-09-01 第三步 A 启动交接说明，并按其优先级读取第二步源码/数据审计、独立复核和交叉复核。根目录三份用户提供文件与 `research/`、`review/` 中的对应事实来源 SHA-256 完全相同。已有 `PREEMPT-Mem_第二步结论修订附录.md` 已覆盖全部 required revisions，因此没有重写原报告、重新选题或重复宽泛文献调查。

项目根目录本身不是 Git 仓库。AppWorld vendor 子仓库 HEAD 为 `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`；`git status` 报告若干 tests 文件 modified，但 `git diff` 与 `git diff --ignore-space-at-eol` 均无内容差异，表现为 Windows 行尾/索引状态。该状态在本轮前已存在，本轮没有清理、覆盖或提交它。

本轮新增本地环境契约 `third_step_a/env-spec.json` 和 `.aris/compute/local.md`。环境 spec canonical SHA-256 为 `ba7c432dc0ae9f2128af513748819f6214d6e945d5cc6d4059d5b7b5bb7aae70`。

## 2. 环境与源码核验

- Python：3.12.13；
- OS：Windows-11-10.0.22000-SP0；
- AppWorld package：0.2.0.dev0；
- AppWorld data：0.2.0；
- AppWorld source commit：`a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`；
- GPU：本机可见一张 6144 MiB GPU，检查时使用 1400 MiB；本 Smoke 是 CPU/SQLite/AppWorld 确定性执行，不分配 GPU；
- 冻结的 21 个代码、协议、配置、prompt 与 probe 文件：21/21 当前 SHA-256 匹配 `run_005` execution freeze；
- `third_step_a/src` 的 8 个 Python 文件：全部通过只读 `compile()` 语法检查；
- 新 memory-store 功能见证：`third_step_a/artifacts/memory_store_probe_20260901.json`，`all_required_checks_pass=true`；删除后 negative probe 无副作用，真实负检索后泄漏扫描仍通过，Restore 恢复相同 record hash。

实际 AppWorld 源码再次确认：task 初始化加载 task-specific DB；`save_state()` 写 checkpoint；`load_state()` 从 checkpoint 重建；`evaluate()` 调用官方 `evaluate_task`。当前 Windows/runtime 上 `load_state()` 经 `AppWorld.close_all()` 后不会自动重建 time freezer，runner 继续采用已记录的最小 `_set_datetime()` re-arm workaround；新复现未出现相关错误。

## 3. fresh agent-follows-doc 复现

按 compute environment contract，fresh agent 只接收 run-experiment 规则、`.aris/compute/local.md` 与 `third_step_a/README.md`，随后从项目根目录逐字执行 README 的复现命令。它未改源码/文档，未即兴修复，命令总退出码为 0，未发现文档与运行时偏差。

新 execution freeze：

`third_step_a/artifacts/execution_freeze_run_reproduction_001_sha256.json`

SHA-256：

`7c4e7ed2996cbace47ef1ac9625531368cf1bb695704ee8d63f62ee57e5f5efa`

## 4. 三案例复现结果

| Case | 类型 | Full | Evicted | Restore | API calls F/E/R | Evicted severity | Leakage | Full=Restore DB |
|---|---|---:|---:|---:|---:|---:|---:|---|
| workflow | adapted | 8/8 PASS | 2/8 FAIL | 8/8 PASS | 67/1/67 | 3 | 15/15 PASS | byte-identical |
| gotcha | adapted | 5/5 PASS | 2/5 FAIL | 5/5 PASS | 125/1/125 | 3 | 15/15 PASS | byte-identical |
| constraint/permission | adapted | 10/10 PASS | 2/10 FAIL | 10/10 PASS | 27/1/27 | 3 | 15/15 PASS | byte-identical |

三案均满足：

- Full 成功、Evicted 失败、Restore 成功；
- Evicted 是 fail-closed omission，没有目标写入或额外敏感写入；
- 同案例三个分支从 byte-equivalent checkpoint 启动，并使用完全相同的 prompt hash；
- Full 与 Restore 的 candidate record、generated code、API 调用数、evaluator 结果和最终 DB tree 一致；
- Evicted 在真实 target retrieval 后的最终 effective-eviction manifest 为 15/15 PASS，forbidden matches 为 0；
- 九个分支内 evaluator 连续两次调用均稳定。

新复现的最终 DB tree SHA-256 与 `run_005` 逐分支一致：

| Case | Full / Restore | Evicted |
|---|---|---|
| workflow | `f108a182afe06cecffd69729cbc5c63935c5b6886a371e3c7fa004fa94737804` | `a0c618c8e1d82f616a317743b76a7f1af0c9936f84344734367e712ff2c5e2c8` |
| gotcha | `d09499dbbf844c0d3010475a8e034d1773ea56d1a00f5a3d13919a0dbb5749e1` | `e8601b6d4779bcdbb7b5ad3398900b35027cffc6312755d8e41ad067a8f6bc33` |
| constraint/permission | `df00314c335bc910c3f45949064cc5c836e05b37602f965fd1e968d68c80e7c6` | `622aeef84ec021264d00a40598297b1884edd18c076f822e82ebb22b92ad2ee2` |

三个 Evicted evaluator 的 success、通过数、失败 label 和 requirement 与 `run_005` 语义一致；failure trace 内由 Python `set` 渲染的元素顺序可能跨进程变化，这一已知非阻断限制不影响判定或 DB state。

## 5. Evidence 完整性与位置

- 新 raw evidence：`third_step_a/artifacts/smoke/run_reproduction_001/`；
- aggregate：`third_step_a/artifacts/smoke/run_reproduction_001/aggregate_gate.json`；
- aggregate SHA-256：`5434d3e7f47263a9096ed11895c3dd2ba690b9ed128b6e194e95e0ccd76c35f7`；
- artifact manifest：`third_step_a/artifacts/smoke/run_reproduction_001/artifact_manifest.json`；
- artifact manifest SHA-256：`3499cd4ac64f6ca663945a6ece6167240b643354eb9a94680c0c32fbd075fa52`；
- manifest 独立重算：377/377 文件大小与 SHA-256 匹配，零缺失、零 mismatch；
- 每个 case 保存 source episode、memory provenance、target relationship、witness、checkpoint/freeze validation、三分支 prompt、retrieval trace、decision、generated code、API calls、DB snapshot、database state diff、两次 evaluator test vector、severity reason、pre-agent/final leakage manifest 和 case summary。

实际命令：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONWARNINGS='ignore'
$env:PYTHONHASHSEED='0'

& 'third_step_a/.venv/Scripts/python.exe' 'third_step_a/src/make_reproduction_freeze.py' --base-freeze 'third_step_a/artifacts/execution_freeze_run_005_sha256.json' --new-run-id 'run_reproduction_001' --output 'third_step_a/artifacts/execution_freeze_run_reproduction_001_sha256.json'
& 'third_step_a/.venv/Scripts/python.exe' 'third_step_a/src/run_smoke_case.py' --config 'third_step_a/config/cases_v3.json' --case 'workflow' --run-id 'run_reproduction_001' --witnesses 'third_step_a/artifacts/witnesses.json' --execution-freeze 'third_step_a/artifacts/execution_freeze_run_reproduction_001_sha256.json'
& 'third_step_a/.venv/Scripts/python.exe' 'third_step_a/src/run_smoke_case.py' --config 'third_step_a/config/cases_v3.json' --case 'gotcha' --run-id 'run_reproduction_001' --witnesses 'third_step_a/artifacts/witnesses.json' --execution-freeze 'third_step_a/artifacts/execution_freeze_run_reproduction_001_sha256.json'
& 'third_step_a/.venv/Scripts/python.exe' 'third_step_a/src/run_smoke_case.py' --config 'third_step_a/config/cases_v3.json' --case 'constraint_permission' --run-id 'run_reproduction_001' --witnesses 'third_step_a/artifacts/witnesses.json' --execution-freeze 'third_step_a/artifacts/execution_freeze_run_reproduction_001_sha256.json'
& 'third_step_a/.venv/Scripts/python.exe' 'third_step_a/src/aggregate_smoke.py' --run-root 'third_step_a/artifacts/smoke/run_reproduction_001' --execution-freeze 'third_step_a/artifacts/execution_freeze_run_reproduction_001_sha256.json'
```

## 6. 判决与严格边界

新 aggregate 的确定性判决为：

`PASS_3A_READY_FOR_INDEPENDENT_AUDIT`

因此 3A 的窄工程 gate 再次通过，建议停止在独立复核入口，不启动完整 40-memory Pilot。

本结果只证明三个人工冻结的 selector-channel case 中，external record 的存储、检索、item-level effective eviction、同记录 Restore、AppWorld 状态执行与官方 evaluator 可以形成无泄漏、可恢复、可复现的方向性 deletion effect。Executor 通过 `metadata.policy_id` 选择硬编码 policy，不语义解释 memory content。故本轮不支持 semantic memory utility、witness predictive validity、natural cross-task lifecycle、rarity/prevalence、FMEA 优越性、完整 PREEMPT-Mem 优越性或跨模型/任务族泛化。
