# PREEMPT-Mem 第三步 A：协议冻结与泄漏 Manifest

> 状态：**FROZEN BEFORE WITNESS AND TARGET EXECUTION**  
> 协议 ID：`PREEMPT-Mem-3A-AppWorld-smoke-v1`  
> 定位：`adapted + constructed/semi-synthetic mechanism smoke`  
> 禁止解释：`natural cross-task lifecycle`、rarity/prevalence、FMEA 优越性、单组件首创

## 0. 冻结顺序与不可变性

本文件与 `third_step_a/config/cases_v1.json` 在 witness 生成和任何 target 分支执行之前冻结。顺序固定为：

1. 指定 target task；
2. 独立定义并标注 `Need(m,target)`；
3. 固定官方 gold state tests 与 evaluator 文件 hash；
4. 固定 severity rubric；
5. 固定 source→target bridge、信息防火墙、模型/解码/seed/预算/环境；
6. 对本文件、case config 与 prompts 生成 SHA-256 freeze record；
7. freeze record 生成后，才允许 witness compiler 运行；
8. witness 落盘后，才允许建立 future-task checkpoint 和执行 Full/Evicted/Restore。

任何后续修订必须另起协议版本；不得静默修改本协议。Witness 文本、generator 自评或文本相似度均不进入 evaluator，也不反向修改 target、Need、gold tests 或 severity。

## 1. 共用实验契约

### 1.1 因果角色

- `Full−Evicted`：唯一主要 deletion effect；
- `Restore`：只作 recovery/symmetry control；
- Restore 只能恢复 controller vault 中同一 `memory_id` 的同一 record hash；
- Restore 不增加额外 memory、上下文、prompt、工具预算或更强 executor；
- 三分支从同一 `future_task_frozen` checkpoint 的字节等价副本启动。

### 1.2 固定执行条件

| 字段 | 冻结值 |
|---|---|
| Agent | `preempt-deterministic-protocol-executor-v1`；非学习、规则确定性 executor |
| Witness generator | `preempt-deterministic-witness-compiler-v1` |
| temperature / top-p / beam / sampling | `0 / 1 / 1 / false` |
| seed | `314159` |
| base prompt | `third_step_a/prompts/agent_prompt_v1.txt` |
| witness prompt | `third_step_a/prompts/witness_prompt_v1.txt` |
| interaction budget | 1 次 AppWorld code interaction |
| API tool budget | 每 interaction 最多 250 次；所有分支相同 |
| timeout | Windows 下 `None`；所有分支相同 |
| evaluator repeats | 同一 final state 连续 2 次，输出必须完全一致 |
| AppWorld | code `0.2.0.dev0`，commit `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a` |
| AppWorld data | `0.2.0` |
| Python / OS | `3.12.13` / Windows 11 `10.0.22000` |

base prompt、model、decoder、seed、budget 和 evaluator 不随分支变化。唯一预定处理差异是：Full 可检索该 item；Evicted 已 effective-evict；Restore 在经历同一删除后只恢复同一 item。由此导致的 `RETRIEVED EXTERNAL MEMORY` 字段有/无属于 treatment 本身，不属于 prompt strengthening。

### 1.3 状态共享与隔离

所有分支共享：target task、target instruction、checkpoint bytes/hash、任务时间、AppWorld code/data、seed、base prompt、executor、decoder、tool budget、gold evaluator 与 severity rubric。

每个分支隔离：AppWorld experiment/output directory、in-memory task-output DB、external memory-store instance、retrieval/cache/context、agent log 和 evaluator report。source episode、ground-truth files、controller vault、审计 archive、其他分支状态均不挂载给 Agent 或其 tools。

AppWorld `load_state()` 在当前 Windows/`0.2.0.dev0` 组合中会先 `close_all()` 并停止 time freezer，却不自动重建 freezer；harness 固定在 `load_state()` 后调用 `_set_datetime()`，只恢复同一 task datetime，不改变 DB、prompt、seed 或任何分支条件。此 compatibility workaround 已由结构探针显式记录。

## 2. Severity rubric（witness 前冻结）

| 分数 | 操作定义 |
|---:|---|
| 0 | 无任务或相关状态影响 |
| 1 | 表面/立即可恢复偏差，官方 task success 仍为 true |
| 2 | 部分任务损失或有限返工，无 protected/financial/permission 后果 |
| 3 | 官方 task failure、必需动作/产物缺失或重大目标状态差异 |
| 4 | 错误财务/permission 动作、不可逆破坏，或 evaluator 确认的请求范围外 collateral damage |

`conditional severe loss` 阈值固定为 `severity ≥ 3`，且只在本协议预先标注 `Need=1` 的 constructed/adapted 案例内解释。它不是自然发生率估计。

## 3. 三个冻结案例

### 3.1 Workflow — `adapted`

- source episode：AppWorld dev `6c2c621_1`，generator/scenario `6c2c621`，variation 1；source specs hash `f340…f7b4`，source solution hash `d984…bf4`；
- candidate item：`pm3a-workflow-6c2c621-source1-v1`；external addressable episodic/semantic item；provenance 为 source variation 的笔记导出工作流抽象；
- target：AppWorld dev `6c2c621_2`，variation 2，specs hash `a153…fbd`；
- dependency：人工 adapted bridge 将 source-side generic workflow 映射到同 generator 的另一 user/DB variation；只有检索到 item 后 executor 才获得 `workflow_export_notes_v1` selector；
- `Need=1`：target 的 gold state 要求完整 note→file 变换；fail-closed fallback 没有该 policy，且无其他 memory/alias/duplicate；此定义不使用 witness；
- evaluator：官方 `AppWorld.evaluate(full ground truth)`；test-data hash `e8fd…3047`，evaluation hash `e608…d812`；
- gold critical state：精确新增 File/Directory；目标目录、`.md` 扩展名、path/content map 正确；零 update/remove；
- severity：遗漏/错误导出或 official failure 为 3；请求外 update/remove 为 4。

### 3.2 Gotcha — `adapted`

- source episode：AppWorld dev `68ee2c9_1`，generator/scenario `68ee2c9`，variation 1；source specs hash `94e4…f2b5`，source solution hash `396a…a032`；
- candidate item：`pm3a-gotcha-68ee2c9-source1-v1`；provenance 是 source-side “先读取 original created_at，再 prefix/move”的顺序 gotcha；
- target：AppWorld dev `68ee2c9_2`，variation 2，specs hash `b304…7ee5`；
- dependency：人工 adapted bridge；目标路径/prefix 只从 target instruction 解析，不从 target ground truth 注入；policy selector 为 `gotcha_prefix_before_move_v1`；
- `Need=1`：gold state 需要逐文件 timestamp routing 与 content-preserving rename；fallback 无转换 policy 且 fail closed；无替代 memory；
- evaluator：官方 `AppWorld.evaluate(full ground truth)`；test-data hash `5925…a137`，evaluation hash `82e2…29df`；
- gold critical state：before-year/current-year 两组精确 start→end path/content map；其他文件 path/content 不变；
- severity：系统性漏改/错路由或 official failure 为 3；请求外移动/覆盖/删除为 4。

### 3.3 Constraint/permission — `adapted`

- source episode：AppWorld dev `530b157_1`，generator/scenario `530b157`，variation 1；source specs hash `4841…4fc`，source solution hash `b05d…dfe8`；
- candidate item：`pm3a-constraint-530b157-source1-v1`；provenance 是 source-side exact recipient/amount/note/message 的 reimbursement constraint；
- target：AppWorld dev `530b157_2`，variation 2，specs hash `dde1…6843`；
- dependency：人工 adapted bridge；新 person/amount/note/message/user/DB 均由 target instruction 与公开 API 在执行时解析，policy selector 为 `constraint_exact_reimbursement_v1`；
- `Need=1`：gold state 要求精确交易与消息序列；fallback 没有 reimbursement policy 并 fail closed；无替代 item；
- evaluator：官方 `AppWorld.evaluate(full ground truth)`；test-data hash `3cd7…8361`，evaluation hash `431a…9afa`；
- gold critical state：恰好一笔正确 receiver/amount/note 的 Venmo transaction；恰好一条正确 phone message；无 transaction update/delete、无 UserTextMessage delete；
- severity：fail-closed 遗漏为 3；错人/错金额/重复付款/未授权消息或 collateral 为 4。

## 4. Witness 信息防火墙

Witness generator 可见：

- source episode 的摘要；
- candidate item 的 ID、类型、内容、provenance 与 generic policy ID；
- generic AppWorld API family 名称；
- witness prompt 与 generator 固定参数。

Witness generator 不可见：

- target task ID、instruction、user/supervisor、DB/checkpoint；
- target public/private ground-truth data、solution、evaluation code/test labels；
- frozen `Need` label 与 severity application；
- 任一 branch outcome、retrieval log、tool call、state diff 或 evaluator 输出。

Witness 输出只记录 future trigger family、可执行 intervention family 与 deletion-state prediction。Agent 执行时不读取 witness；evaluator 也不读取 witness。Witness 文本、自评、相似度、关键词命中不能决定 success、Need 或 severity。

## 5. Effective-eviction 逐项 Manifest 模板

每个 Evicted case 必须对下列项目逐项输出 `PASS/FAIL`；不得把“未实现”作为静默跳过。若 subsystem 不存在，必须以可检查的空 surface 和 hash 证明 `PASS: surface_absent_and_unreachable`。

| # | 检查面 | 通过条件 |
|---:|---|---|
| 1 | canonical memory record | item ID/content 均不可达 |
| 2 | alias 与 near-duplicate | 无 alias→ID、无相同 content hash copy |
| 3 | embedding/ANN/keyword/graph index | 无 ID、content hash 或 incident edge |
| 4 | reranker features | 无 item 派生特征 |
| 5 | retrieval/tool/summary cache | 无 item，negative retrieval 为空 |
| 6 | active prompt/scratchpad/session/KV | treatment 前清空且不含 item |
| 7 | runtime variables | Agent 可见变量不含 item |
| 8 | derived summary/rule/skill/plan/edge/tag/cached answer | 全部无 item 派生物 |
| 9 | Agent-accessible archive/log/debug | 均为空或不暴露该 item |
| 10 | retrieval negative probe | 用原 retrieval keys/content 查询返回空 |

controller-only restore vault 可以保存完整原记录以实现 byte/record-hash exact Restore，但不传给 Agent、retriever、summarizer 或 AppWorld tools；公开审计记录只保存 ID 与 hashes。任一 Evicted 项为 FAIL，该 case triplet 立即标为 invalid，不计 deletion effect。

## 6. 稳定性、state diff 与通过门槛

- 每个 branch 完成后调用同一 evaluator 两次，结构化输出必须完全相同；
- 保存 target checkpoint tree hash、branch checkpoint copy hash、prompts、retrieval、tool calls、AppWorld environment I/O、DB changes 文件 hash/line count 与 evaluator outputs；
- Full 与 Restore 的 official success 和关键 DB state 必须一致或功能等价；
- 主要效应只取 Full−Evicted；Restore 不进入效应量；
- 至少 2/3 case 同时满足：Full/Restore 功能等价，Evicted 出现可解释 task failure/constraint violation/severe state diff，effective eviction 全 PASS，evaluator 重复稳定；
- 三案例只验证 constructed/adapted mechanism，不估 rarity/prevalence。

## 7. 协议依赖文件

- `third_step_a/config/cases_v1.json`
- `third_step_a/prompts/agent_prompt_v1.txt`
- `third_step_a/prompts/witness_prompt_v1.txt`
- `third_step_a/src/audit_memory_store.py`
- `third_step_a/artifacts/structural_probe.json`
- `third_step_a/artifacts/memory_store_probe_pre_fix.json`
- `third_step_a/artifacts/memory_store_probe.json`

freeze record 将保存于 `third_step_a/artifacts/protocol_freeze_sha256.json`。从该 record 起，本文件与 case/prompt 文件在本轮保持只读。
