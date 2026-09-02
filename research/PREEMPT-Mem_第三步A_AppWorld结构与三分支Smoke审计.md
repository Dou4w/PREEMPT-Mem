# PREEMPT-Mem 第三步 A：AppWorld 结构与三分支 Smoke 审计

> 日期：2026-08-27  
> 最终主运行：third_step_a/artifacts/smoke/run_005  
> 定位：adapted + constructed/semi-synthetic mechanism smoke  
> 唯一允许表述：constructed deterministic selector-channel mechanism smoke

## 1. 结论

本轮严格完成“前置修订 → AppWorld 真实实现检查 → 协议冻结 → 三分支 Smoke → gate”，未进入完整 Pilot，未估计 rarity/prevalence，未比较 FMEA，未训练模型，也未修改三份原始审查报告。

run_005 的冻结结果：

- 3/3：Full 成功、Evicted 失败、Restore 成功；
- 3/3：Full 与 Restore 的 evaluator、generated code、memory record 和最终 DB tree hash 完全相同；
- 3/3：Evicted 为 fail-closed omission，severity=3；
- 3/3：最终 effective-eviction manifest 15/15 PASS；
- 9/9：evaluator 连续两次输出一致；
- 9/9：branch checkpoint 与同案例 base checkpoint byte-equivalent；
- 3/3：同案例三分支 exact prompt hash 相同；
- 377/377 run artifacts 重算 size/SHA-256 匹配。

这只证明窄范围的 constructed selector-channel plumbing：外部 selector record 的存在、删除和同记录恢复能在固定 AppWorld 状态机中产生可复现方向性结果。Executor 依据 metadata.policy_id 选择硬编码算法，不语义解释 memory content；因此不支持 semantic memory utility、自然 memory 必要性或 witness 有效性。

## 2. 前置修订与原报告保护

research/PREEMPT-Mem_第二步结论修订附录.md 在 Smoke 前创建，SHA-256 为 95629d35e050f20bd8cda63a51a6edfff5daf3ac741d889b4d7f6f88a16cd091，已落实：

1. 七项强近邻矩阵；
2. What Eviction Destroys = U / unverified lead；
3. 八要素完整组合是唯一安全 novelty；
4. external addressable episodic/semantic memory 是对象；
5. FMEA 仅为可选 schema，不使用 RPN；
6. 后续 Pilot 加 generic risk triage，不主张单组件首创；
7. AppWorld 仅作 adapted + constructed/semi-synthetic smoke；
8. 三案例和未来平衡 40 条均不得估计 prevalence。

三份原始报告当前 hash 与执行前基线一致：

| 文件 | SHA-256 |
|---|---|
| research/PREEMPT-Mem_第二步_数据源码与现象验证审计.md | cdeef88ef0282128b063200340f74f5f712237f73a5f5af1d3f1f60956ad4003 |
| review/PREEMPT-Mem_已完成内容独立复核报告.md | 0e48bd034e363784a0f7af7a15f5d9ca8721fddb3f7fc35f945edbf69acff5ed |
| research/PREEMPT-Mem_第二步交叉复核与第三步A准入意见.md | ffaba6f88d1eb26f7382930a8eea80b1d60646dc4e12d4917d7e4af60161c3f1 |

## 3. AppWorld 真实实现

实际源码位于 third_step_a/vendor/appworld_source，commit a072b7a86e7c1d5b1d7175659d750ebb9b79f10a；package 0.2.0.dev0，data 0.2.0，Python 3.12.13，Windows-11-10.0.22000-SP0。官方 protected bundles 已通过正式接口解包；结论来自源码和 third_step_a/artifacts/structural_probe.json 的真实执行，不是论文推断。

确认事项：

- Task.id 是 grounded task；generator_id 是 scenario/programmatic family；后缀为 variation；
- specs.json 提供 instruction、supervisor/user、datetime、db_version；
- 每个 task 从 data/tasks/<task_id>/dbs 加载 task-specific DB；
- 同 generator 的不同 variation 可有不同 user、instruction 和 DB；
- 新 AppWorld 会关闭旧 world，从当前 task DB 重建 output DB；跨 task 不自然共享 live DB；
- save_state(state_id) 保存 app JSONL 和 model hashes；load_state(state_id) 从 checkpoint 重建；
- 探针完成卡片数 5 → 0 → load(initial)=5 → load(mutated)=0；
- state evaluator 可重复调用；official solution 成功；额外删除 Amazon payment cards 后 collateral invariant 稳定失败。

Windows 下 load_state() 会经 close_all() 停止 time freezer 而不重建。Runner 在 load_state() 后调用 _set_datetime()，只恢复原 task 时间；此 workaround 已记录，不改变 DB、prompt、seed、memory 或 treatment。

AppWorld 不提供跨 task external memory。Source→target dependency 必须由本轮外部 adapted/constructed bridge 建立。

## 4. 外部 memory store、失败与修复

AuditMemoryStore 提供 stable ID、provenance、canonical/alias/index/cache surfaces、retrieve、delete、controller-only exact restore 和 ID/hash audit record。Agent 只持有 AgentMemoryView.retrieve()。

保留的失败证据：

1. memory_store_probe_pre_fix.json：Restore 后旧 negative cache 未失效；
2. memory_store_probe_pre_negative_probe_fix.json：第一版修复仍让 effective-eviction negative probe 写回 item-derived query，且 delete 保留空结果 query；
3. review/PREEMPT-Mem_第三步A_独立实验审计.md：据此对 run_004 给出 AUDIT_REQUIRE_REPAIR_3A。

最终修复：

- put/restore 清空 retrieval cache；
- delete 完全失效 retrieval/tool/summary caches；
- negative probe 固定 cache_result=false；
- probe 前后全部 store surfaces 的 canonical hash 必须相同；
- Agent 对真实 target query 检索后，再次做最终 surface scan；
- Restore 必须恢复同一 ID 和完全相同 record hash。

最终 memory_store_probe.json 证明：probe 无副作用，删除后 cache 为空，Agent 负检索后再审计仍通过，Restore 后相同 query 返回同一 ID。

## 5. 协议、Witness 与 execution freeze

协议链：

- v1：research/PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest.md，冻结 target、Need、gold evaluator、severity、bridge、witness 边界和分支合同；
- v2：把 treatment-specific retrieval result 从 prompt 移到独立 memory-tool channel，保证 exact prompt 相同；
- v3：research/PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest_v3_审计修订.md，前瞻性修复 leakage、freeze enforcement 和 severity，并收窄 selector-channel 主张。

v3 未改变 target、Need label、candidate item content/ID/provenance、gold tests、severity rubric、witness、seed、decoder、prompt、budget 或 AppWorld 版本。

Witness generator 只看 source summary、candidate/provenance 和 generic API family；看不到 target、target DB、gold evaluator、Need/severity 或 outcome。Agent、Need、severity、evaluator 均不读取 witness。

execution_freeze_run_005_sha256.json 在 run_005 目录产生前创建，hash 为：

15d9caaf5c3c0e91424c114da3939fb9010c4910b8bd0d142d7fdd379310a4c0

它冻结 21 个协议/config/prompt/witness/probe/code 文件和实际环境。Runner 将 execution freeze 设为必填，并在 target checkpoint 前验证 run ID/path、所有文件 hash、Python/OS/AppWorld commit/code/data、source specs/solution、target specs/test_data/evaluation。九个分支全部验证通过。Aggregator 读取原始 branch_result 复算 gate，拒绝 summary/raw 不一致和覆盖已有 aggregate。

## 6. 冻结案例与因果合同

| Case | 标签 | Source → target | Memory ID |
|---|---|---|---|
| workflow | adapted | dev 6c2c621_1 → 6c2c621_2 | pm3a-workflow-6c2c621-source1-v1 |
| gotcha | adapted | dev 68ee2c9_1 → 68ee2c9_2 | pm3a-gotcha-68ee2c9-source1-v1 |
| constraint/permission | adapted | dev 530b157_1 → 530b157_2 | pm3a-constraint-530b157-source1-v1 |

三对为同一 official generator 的不同 variations，但 user/DB 不同。AppWorld 不共享 episode；retrieved metadata.policy_id 人工选择冻结 executor。Need=1 是“无 selector 的冻结 fallback 会 fail closed”的构造机制条件，不是自然 prevalence。

每案从同一 future-task checkpoint 执行 Full、Evicted、Restore。Full−Evicted 是唯一 primary effect；Restore 仅是 recovery/symmetry control，且只恢复同一 record。三分支固定 seed 314159、deterministic executor、temperature 0、top_p 1、beam 1、sampling=false、1 interaction、250 API-call 上限、exact prompt、环境与 evaluator。

## 7. run_005 结果

| Case | Checkpoint 前 12 | Prompt 前 12 | Full | Evicted | Restore | Calls F/E/R | Full=Restore DB | Severity | Eviction |
|---|---|---|---|---|---|---:|---|---:|---|
| workflow | 04be6a922e4c | 309164004993 | 8/8 | 2/8 | 8/8 | 67/1/67 | 是 | 3 | 15/15 |
| gotcha | 4e8ecf535fd8 | 2355d2ed5e84 | 5/5 | 2/5 | 5/5 | 125/1/125 | 是 | 3 | 15/15 |
| constraint/permission | b287fd56077d | d89e1915e65b | 10/10 | 2/10 | 10/10 | 27/1/27 | 是 | 3 | 15/15 |

Exact hashes：

| Case | Candidate record | Full/Restore final DB | Evicted final DB |
|---|---|---|---|
| workflow | 22ada72a1203d85da27e20fa2e6ef2a16ec22f807675872da5cae26be9875dd0 | f108a182afe06cecffd69729cbc5c63935c5b6886a371e3c7fa004fa94737804 | a0c618c8e1d82f616a317743b76a7f1af0c9936f84344734367e712ff2c5e2c8 |
| gotcha | 265c5a51eddfd3abc4dcc03c0f421e383829d1139993853e17350a4aced8fa7e | d09499dbbf844c0d3010475a8e034d1773ea56d1a00f5a3d13919a0dbb5749e1 | e8601b6d4779bcdbb7b5ad3398900b35027cffc6312755d8e41ad067a8f6bc33 |
| constraint/permission | 5cfa4e1af49779cbea63be8ec7af65c5c0f09a363840d5b96bf971ababc48fc6 | df00314c335bc910c3f45949064cc5c836e05b37602f965fd1e968d68c80e7c6 | 622aeef84ec021264d00a40598297b1884edd18c076f822e82ebb22b92ad2ee2 |

Evicted 三案只调用 supervisor fail-closed completion，没有目标写入或 Venmo/phone 敏感写操作。可执行 rubric 判为 official failure/required action omission without collateral，因此 severity=3。

## 8. Effective eviction

每个 Evicted 最终 manifest 在真实 target retrieval 后检查 15 项：negative-probe side effect、negative retrieval、九类 store surfaces、actual prompt、generated code、retrieval result、decision payload。

禁止针包括 memory ID、完整 content、content hash、record hash、aliases、retrieval keys、policy ID、canonical provenance、8-token content fragments 和唯一 leakage sentinel。三案均：

- 15/15 PASS；
- forbidden matches=0；
- negative probe 前后 surface hash 相同；
- retrieval_results.json 为空；
- decision 为 fail_closed、policy_id=null。

Controller restore vault 与只含 ID/hash 的 audit record 被隔离，Agent/retriever/executor/tool 不可访问。Restore 未增加 prompt/context；其 record、code、evaluator 和最终 DB 与 Full 完全相同。

## 9. 状态差异、日志与完整性

每案 database_state_diff.json 保存 checkpoint→Full/Evicted/Restore、Full→Evicted、Full→Restore 五组逐文件差异。JSONL 包含完整 added/removed counts 和 records。三案 Full→Restore 全文件 byte-equivalent，Full→Evicted 均有可解释差异。

每案还保存 source episode、memory provenance、target relationship、witness、checkpoint/freeze manifests、prompts、retrieval、code、decision、API calls、environment I/O、DB snapshots、evaluator report/双次结构化输出、severity reason、pre-agent/final eviction manifests、环境/依赖版本和 case summary。

入口：

- config：third_step_a/config/cases_v3.json；
- freeze：third_step_a/artifacts/execution_freeze_run_005_sha256.json；
- code：third_step_a/src；
- raw evidence：third_step_a/artifacts/smoke/run_005；
- aggregate：third_step_a/artifacts/smoke/run_005/aggregate_gate.json；
- manifest：third_step_a/artifacts/smoke/run_005/artifact_manifest.json。

完整性重算：377/377 artifacts 匹配，21/21 freeze files 匹配，三份原始报告匹配基线。aggregate deterministic verdict 为 PASS_3A_READY_FOR_INDEPENDENT_AUDIT。

## 10. Gate 与边界

| Gate | 结果 |
|---|---|
| 至少 2/3 Full/Restore 成功且状态一致 | PASS：3/3 exact DB equal |
| Evicted 相对 Full 可解释失败/严重差异 | PASS：3/3 severity 3 |
| effective eviction 无泄漏 | PASS：3/3，各 15/15 |
| evaluator 稳定 | PASS：9/9 双跑一致 |
| checkpoint/environment | PASS：9/9 hash equal，freeze 强制通过 |
| exact prompt | PASS：3/3 案例内相同 |
| Restore 只恢复同一 item | PASS：record/code/evaluator/DB 相同 |
| claim firewall | PASS：仅 selector-channel mechanism smoke |

允许结论仅限上述三个 constructed selector-channel 案例的 item deletion/restore plumbing。禁止 natural lifecycle、semantic utility、witness validity、rarity/prevalence、FMEA 优越性、完整 PREEMPT 优越性、单组件首创及跨 Agent/LLM/task-family 外推。

run_001–run_003 是开发轨迹；run_004 因独立审计发现 leak checker 假阳性而作废其 leak-free gate。run_005 是修复、重新冻结后用新 ID 从零执行的唯一最终证据，未覆盖历史运行。

## 11. Fresh 独立实验审计

按 experiment-audit 流程，fresh zero-context GPT-5.6-Sol reviewer 对 run_005 做了 same-family provisional 只读复核，报告保存于 review/PREEMPT-Mem_第三步A_run005独立实验审计.md，最终建议为 AUDIT_PASS_3A_READY。

Reviewer 独立重算 21/21 freeze files、377/377 run artifacts、三个案例九个原始分支、数据库差异、泄漏 manifests、Restore 对称性与隔离进程 evaluator；未发现需要重跑或阻断本轮窄 gate 的完整性缺陷。其记录的非阻断限制是：severity 1/2 尚无实现路径，当前只验证本轮观测的 0/3 和风险路径 4；跨 Python 进程的失败 trace 中 set 元素顺序可能变化，但判定、通过数、failure label 与 requirement 稳定。这些限制不得在后续被表述为完整 0–4 校准或跨进程 trace byte-identical。

该复核与本报告的 PASS 均为项目内 same-family assurance，不替代用户要求的后续外部/独立复核。

## 12. 最终判决

PASS_3A_READY_FOR_INDEPENDENT_AUDIT
