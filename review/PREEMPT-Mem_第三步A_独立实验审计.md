# PREEMPT-Mem 第三步 A 独立实验审计

**审计日期**：2026-08-27  
**审计性质**：GPT-5.6-Sol fresh same-family 独立只读复核；结论为 provisional  
**审计范围**：仅审计冻结后的 `run_004` 主证据，并把 `run_001/cases/gotcha` 作为已披露失败轨迹核对。

## 总判决：REQUIRE REPAIR

`run_004` 的原始产物真实存在、内部一致，足以支持一个很窄的结论：在三个明确 adapted/constructed 案例中，AppWorld 同检查点三分支与外部记录的删除/恢复管线能够产生可重复的方向性 selector-channel smoke。它不支持自然 lifecycle、memory semantic utility、witness 发现能力、rarity/prevalence、FMEA 优越性或任何单组件主张。

当前不能接受 `all_evictions_leak_free=true`，因此不能通过完整 3A gate。原因不是结果文件缺失或数字不匹配，而是 effective-eviction 检查本身会在判定后重新污染缓存，并存在覆盖不足。该问题可修复，故不作永久阻断。

## 1. 冻结、时序与证据完整性

**通过。** 两份 freeze record 中本轮可核验的文件 SHA-256 均与当前文件逐项一致；`cases_v1.json` 与 `cases_v2.json` 除 protocol ID 和 agent prompt path 外语义相同，target、`Need`、evaluator、severity、witness、seed、decoder 和 budget 未改变。协议 freeze 为 19:44，witness 为 19:45，v2 修订为 20:00，execution freeze 为 20:01，最早 `run_004` 产物为 20:02。`third_step_a/artifacts/smoke/run_004/artifact_manifest.json` 的 362 个条目重算后 362/362 的大小与 SHA-256 匹配。

证据：`third_step_a/artifacts/protocol_freeze_sha256.json:2-20`；`third_step_a/artifacts/execution_freeze_run_004_sha256.json:2-21`；`research/PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest_v2_精确Prompt修订.md:3-23`。

**限制。** runner 不读取 freeze record，也不强制校验 target specs、test-data、evaluator 或实际运行版本；它接受任意 `--config`、`--run-id`、`--witnesses`，运行后才记录部分哈希。aggregator 直接读取指定 run-root 的 summary。因此冻结目前由外部审计确认，而非 harness 自证。见 `third_step_a/src/run_smoke_case.py:122-153,396-407`、`third_step_a/src/aggregate_smoke.py:14-30,49-63`。

## 2. AppWorld 实体、检查点与 evaluator

**通过。** 三案均为真实 AppWorld dev task：`6c2c621_1→6c2c621_2`、`68ee2c9_1→68ee2c9_2`、`530b157_1→530b157_2`，均由 variation 1 桥接到 variation 2。逐项重算 source specs/solution、target specs/test-data/evaluation 文件哈希，全部与 `cases_v2.json` 一致；每对 source/target 的 supervisor 与任务 DB 均不同。对应冻结字段见 `third_step_a/config/cases_v2.json:41-78,81-118,121-158`。

结构探针记录了 task-specific DB、checkpoint 往返、同任务 reset、跨任务重绑、evaluator 重复稳定和 collateral detection，`all_required_checks_pass=true`；见 `third_step_a/artifacts/structural_probe.json:9-78,80-193`。实际 runner 对 base checkpoint 建 tree hash，再向每一分支复制、复算并在不等时中止，随后从同一 checkpoint load；见 `third_step_a/src/run_smoke_case.py:163-176,218-232`。

## 3. Memory 语义与 pre-fix 修复

**部分通过。** 稳定 ID、provenance、delete/restore 接口与 exact record restore 均有实现。pre-fix probe 的 `interface_after_restore.retrieval_returns_exact_id=false`、总门控 false，修复后相同字段变为 true、总门控 true；见 `third_step_a/artifacts/memory_store_probe_pre_fix.json:97-107` 与 `third_step_a/artifacts/memory_store_probe.json:97-107`。修复代码在 put/restore 时清空 negative cache，并校验恢复后的 record hash；见 `third_step_a/src/audit_memory_store.py:112-135,207-216`。

但 pre/post probe 本身没有纳入两份 freeze record，故其历史先后只能由文件时间与当前代码旁证，不能形成同等级的冻结证据链。

## 4. `run_004` 三分支原始结果

| 案例 | Full / Evicted / Restore | official evaluator | 同 checkpoint/prompt | Full=Restore |
|---|---|---|---|---|
| workflow | 成功 / 失败(3) / 成功 | 8/8、2/8、8/8 | 是 / 是 | code、record、DB 均相同 |
| gotcha | 成功 / 失败(3) / 成功 | 5/5、2/5、5/5 | 是 / 是 | code、record、DB 均相同 |
| constraint_permission | 成功 / 失败(3) / 成功 | 10/10、2/10、10/10 | 是 / 是 | code、record、DB 均相同 |

九个分支均记录相同 seed `314159`、model、decoder、1 interaction/250 API-call budget；每个分支两次 evaluator 输出完全一致。Full/Restore 的 API 日志、environment I/O、generated code、retrieval result 和最终 DB 在各案内完全一致；Evicted 仅执行 fail-closed `complete_task(status="fail")`，没有目标状态写入或 collateral。原始证据见各案 `branch_result.json`、`case_summary.json` 与 `appworld_output_snapshot/evaluation/report.md`；汇总与原始值一致，见 `third_step_a/artifacts/smoke/run_004/aggregate_gate.json:3-74`。

severity=3 对本次三个 Evicted 的“official failure + 必需动作缺失且无 collateral”结果是正确的；但 harness 实际只实现 `success→0 / failure→3`，并未实现完整 0–4 rubric，见 `third_step_a/src/run_smoke_case.py:286,325-326`。因此当前分数可接受，不能据此声称 severity evaluator 已一般化验证。

## 5. Effective eviction 与泄漏：失败，必须修复

Evicted 的实际 agent-visible 产物是干净的：三案 `prompt.txt` 在分支内 byte-identical，`retrieval_results.json=[]`，decision 为 `fail_closed/policy_id=null`，generated code 仅完成 fail-closed；每案 manifest 也记录 14/14 PASS。

然而 manifest 的 PASS 不成立于其声称的最终缓存状态：

1. `effective_eviction_manifest()` 先扫描并哈希所有 surfaces，见 `third_step_a/src/audit_memory_store.py:251-265`；
2. 随后它以原 memory 的全部 retrieval keys 和 content 执行 negative probe，见同文件 `:266-268`；
3. `retrieve()` 会把规范化 query 写回 `retrieval_cache`，即使结果为空，见同文件 `:137-150`；
4. 写回后没有再次扫描 cache。于是公开 manifest 仍为 PASS，但 store 的最终 retrieval cache 已重新包含由被删 item 内容派生的 query key。这与冻结协议对 retrieval/tool/summary cache 的清空要求冲突，见 `research/PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest.md:132-141`。

此外，storage-surface 与 actual-payload 检查都只搜索 exact memory ID 和 exact full content，见 `third_step_a/src/audit_memory_store.py:251-264`、`third_step_a/src/run_smoke_case.py:83-110`；它们没有检查 alias、retrieval keys、policy ID、content hash、provenance 或派生片段。故 `all_evictions_leak_free=true` 是检查器假阳性，不能作为完整无泄漏证据。

## 6. 主效应、失败轨迹与主张边界

**通过。** 协议和 config 明确把 `Full−Evicted` 设为唯一主要效应，Restore 仅为 recovery/symmetry control；见 `research/PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest.md:25-31,145-152`、`third_step_a/config/cases_v2.json:25-27`。`run_001/cases/gotcha/case_summary.json` 明确记录 Full/Restore 失败、无 primary deletion effect、`case_pass=false`；v2 修订也把 run_001–003 标为开发轨迹，只使用重新冻结后从零执行的 run_004，见 `research/PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest_v2_精确Prompt修订.md:25`。

没有发现主证据把三案表述为 natural lifecycle，或估计 rarity/prevalence、比较 FMEA、宣称单组件首创；边界在 `research/PREEMPT-Mem_第二步结论修订附录.md:143-188` 与 `third_step_a/config/cases_v2.json:2-5` 中明确冻结。

## 7. 构造依赖与循环性判定

存在强构造闭环：三套完整目标算法已硬编码在 `third_step_a/src/protocol_executor.py:17-190`，决策只读取 retrieved record 的 `metadata.policy_id` 来选择算法，见同文件 `:193-222`；memory content、provenance 和 witness 并未被语义解释。三个 `Need=1` 又以 frozen fallback 没有相应 policy 且 fail closed 来定义，见 `third_step_a/config/cases_v2.json:68-70,108-110,148-150`。witness 只被加载、存档，不进入执行或 evaluator，见 `third_step_a/src/run_smoke_case.py:150-153,201,246-254`。

该循环性**不推翻最窄的 selector-channel/plumbing smoke**：它仍真实证明同检查点分支、删除、恢复、执行和 state evaluator 可以联通并复现。但它把 Full 成功/Evicted 失败在设计上近乎确定，因而只能限制为 constructed mechanism sanity check；它不能作为 external memory 自然必要性、语义价值、witness 预测有效性或外部有效性的证据。

## 必须修复后方可通过 3A

1. 使 negative probe 无副作用，或 probe 后清空 cache 并重新审计所有 surfaces；把最终 surface 状态及其 hash 落盘。
2. 泄漏检测加入 memory ID、完整内容、content hash、aliases、retrieval keys、policy ID、provenance 以及可解释的派生片段/sentinel，并对实际 prompt/code/retrieval/decision 与最终 store 同时检查。
3. 将修复后的 code、probe、config、prompt、witness、target/evaluator hashes 和实际环境检查冻结到新 execution record；使用新 run ID 从零重跑三案，不覆盖 `run_004`。
4. 对外结论固定为 constructed deterministic selector-channel mechanism smoke；若要主张 memory semantic utility 或 witness 有效性，必须另做非硬编码 selector、非 fail-closed 必然对照的实验。

AUDIT_REQUIRE_REPAIR_3A
