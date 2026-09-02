# PREEMPT-Mem 第三步 A-R 实验完整性独立复核

**日期**：2026-09-01  
**审稿人**：GPT-5.6-Sol ultra（fresh same-family agent，只读）  
**独立性**：`same-family`  
**接受状态**：`provisional`  
**审计对象**：`third_step_a/artifacts/smoke/run_isolated_001`  
**总体判定**：`WARN`

## 结论

在严格限定为“冻结 trusted worker 下的 constructed deterministic `policy_id` selector-channel mechanism smoke”时，没有发现残余 BLOCK 级因果错误。三案 Full/Evicted/Restore 结果、同 snapshot、Restore 同一记录、DB/evaluator 对称性、90 项 capability denial、target+distractor 失效、hash/manifest/attestation 与新旧 run 独立性均可从封存证据重算。

该结论不构成任意/model-generated Python Agent 的 OS/文件系统沙箱证明，不支持 semantic memory、learned retrieval、自然生命周期、通用 Agent-memory 收益、3B 或 Pilot。由于审稿人与执行者同属 OpenAI/GPT 家族，任何正面结论均只作 provisional。

## A–F 检查

| 检查 | 状态 | 结论 |
|---|---|---|
| A. Ground-truth provenance | WARN | Agent-time GT 缺失与 evaluator-only official call path 成立；本地源码/GT 哈希一致；受保护数据缺少独立签名的上游 bundle 锚点。 |
| B. Metric integrity | WARN | official pass 语义、双重复、raw/semantic vectors 与 aggregate 重算成立；A-R 将所有 evaluator failure 固定映射为 severity=3，score 1/2/4 不可达。 |
| C. Result integrity | WARN | 留存的 outcome、snapshot、DB diff、vector、probe、restore、manifest、attestation 与 fresh-run 证据一致；raw pre-redaction/controller-memory 输入被删除，无法从 seal 独立重放。 |
| D. Code-path integrity | WARN | 冻结 worker 只有结构化 public tool path，无已发现私有能力路径；探针只证明 RPC-method denial，不证明 OS/Python sandbox；prompt 行为上是 dead input，`policy_id` 选择硬编码 executor。 |
| E. Scope/claim integrity | PASS | 修复报告严格限定 constructed deterministic selector-channel smoke，并明确排除语义、自然生命周期、泛化、3B 与 Pilot 主张。 |
| F. Evaluation type | PASS | inference-time mechanistic intervention；adapted + constructed/semi-synthetic mechanism smoke，不是训练时或观察性证据。 |

## 独立重算要点

- 三案结果：workflow 8/8→2/8→8/8；gotcha 5/5→2/5→5/5；constraint/permission 10/10→2/10→10/10。
- 9/9 evaluator semantic repeats 相等；7/9 raw vectors 相等，另两对只差 `failures[*].trace` 的 set-repr 顺序。
- Full=1、Evicted=0、Restore=1 条 retrieval；Restore memory ID/SHA 与 Full 相同。
- 每案三分支 checkpoint 相同；Full/Restore request、plan、RPC、DB tree 与 evaluator vectors 对称。
- 90/90 forbidden RPC probes 返回 exact `CAPABILITY_DENIED`；445 行 Agent API 调用均属于 per-case allowlist。
- target+distractor：target-only deletion、非空 distractor 不变、共享 ANN/query/cache collision、mixed nested dependency invalidation 与 exact Restore 均成立。
- final manifest：467 entries、2,439,465 bytes、root `d607e9f83938e0505d6d86269aa2aeb8b3d22fa840c650eefcf71d4ced819d75`；manifest SHA `4988163e6774d1794e8cb4e1cbfecb0053879987ddb7fec97ff9598002f5deb7`。
- 物理 run：468 files、2,529,502 bytes；216 JSON 与 243 JSONL 全部可解析。
- 与 `run_reproduction_001` 比较：无 hardlink/file identity、无交叉 run ID、时间与 manifest 分离；静态证据强支持 fresh execution，但不能密码学排除“复制后重新序列化”。

## Required fixes / claim guards

1. 任意或 model-generated code Agent 仍须使用真正 OS sandbox/container；在此之前不得扩大 capability-isolation 主张。
2. 在后续实验前修复 severity rubric，使 0–4，尤其 score-4 collateral 条件可真实计算；当前 smoke outcome 不受影响。
3. 若要把 raw-firewall/redaction 结论提升为完全可重放证据，需引入不向 Agent 暴露、但可由独立审计者验证的安全封存或流式独立 verifier。
4. 有可用官方签名/checksum 时补充 AppWorld protected-data bundle 的上游锚点。
5. 持续把 `policy_id` hard-coded executor 与 dead prompt 明示为 selector-channel instrumentation；不得将其写成 semantic memory 或 prompt-following 证据。

## BLOCK-level statement

**对 exact frozen trusted-worker / constructed deterministic selector-channel mechanism smoke，没有残余 BLOCK 级因果错误。**

对 arbitrary/free-code Agent、OS/filesystem isolation、semantic record-content utility、learned retrieval、natural lifecycle、general Agent-memory benefit、3B 或 Pilot readiness，仍然不能放行。

## Trace

完整 reviewer prompt、逐字响应与元数据：

`.aris/traces/experiment-audit/2026-09-01_run02/`

