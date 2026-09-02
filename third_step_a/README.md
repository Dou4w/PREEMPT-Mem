# PREEMPT-Mem 第三步 A-R：隔离修复与可复现入口

本目录同时保留两条证据链：既有 `artifacts/smoke/run_reproduction_001/` 原样不动；A-R 的新主证据为 `artifacts/smoke/run_isolated_001/`。A-R 只支持 **constructed deterministic selector-channel mechanism smoke**，不支持语义记忆效用、自然生命周期、发生率或 Pilot 结论。

## A-R 隔离边界

- controller 持有 memory store、restore vault、branch 与审计私有信息；Agent 不接触这些对象。
- Agent 是复制到全新临时目录后以外部 Python `-I` 启动的结构化 JSONL tool-call worker。其初始化线严格只有 `type`、`protocol_version`、`target_instruction`、`retrieval_results` 四个字段。
- 每案只开放冻结的 AppWorld public `app.api` allowlist；没有任意模型代码执行，也不声称提供通用 Windows 文件系统/任意代码沙箱。
- Agent world 不加载 ground truth。三分支 Agent 全部退出、DB 复制冻结后，两个独立 evaluator 进程才加载 GT 并调用 `appworld.evaluator.evaluate_task`。
- 每分支强制执行 10 个负向 capability probes：caller secret、inspect stack、branch、project file、world、memory store、controller vault、GT、evaluation code、controller directory；必须全部被拒绝。
- raw pre-redaction RPC/final payload 只在冻结 controller 内存中扫描，随后删除；共享 artifacts 保存零匹配 attestation 与 virtual SHA-256。该项不能表述为 sealed artifacts 对已删除 raw payload 的独立重放。
- evaluator 重复性比较精确覆盖 outcome、difficulty、count、label、requirement multiset；两份 raw vectors 与 worker envelopes 全量保留并绑定。仅 `failures[*].trace` 中 Python set repr 顺序不进入语义相等判定。

## 冻结环境

- AppWorld source：`vendor/appworld_source`，commit `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`
- AppWorld data：`appworld_root/data`，version `0.2.0`
- Python：`.venv`，3.12.13
- A-R config：`config/cases_isolated_v1.json`（叠加 `config/cases_v3.json`）
- A-R environment：`env-spec-isolated-v1.json`
- Agent prompt：`prompts/agent_prompt_isolated_v1.txt`

当前 Codex Python runtime 会错误解码中文绝对工作区路径。以下命令用 `subst R:` 指向同一物理项目；三案与 aggregate 必须保持同一逻辑盘符，以便严格核验 controller executable path。没有复制或移动项目。

## 从全新 snapshot 复现 `run_isolated_001`

在 PowerShell 中逐行执行；所有写入函数均拒绝覆盖已有文件：

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

`aggregate_smoke.py` 不读取 `case_summary.json` 的判定布尔值；它从 checkpoint、branch artifacts、DB snapshots、两份 evaluator vectors/envelopes、effective-eviction manifests、capability transcripts、firewall attestations 与 target+distractor probe 重算结果，再生成 `aggregate_gate.json` 和覆盖全 run 的 `artifact_manifest.json`。

## target-scoped eviction

`AuditMemoryStore.delete(target)` 只清理 target 及其唯一派生依赖，并覆盖 canonical record、aliases/near-duplicates、ANN/keyword/graph、reranker、retrieval/tool/summary cache、active prompt/scratchpad/session/KV、runtime variables、derived summary/rule/skill/plan/edge/tag/cached answer、agent-accessible archive/log/debug surfaces。双记录探针要求 distractor 在删除 target 前后逐 surface canonical 等价；Restore 只恢复同一 target item。

失败开发运行（`dev_isolated_gate_20260901_01` 至 `_09`）保留用于错误复现与修复追踪，不是最终证据。不得启动 40-memory Pilot，直到新的独立复核完成。
