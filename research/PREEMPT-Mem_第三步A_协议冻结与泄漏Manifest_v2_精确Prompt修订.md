# PREEMPT-Mem 第三步 A 协议 v2：精确 Prompt 修订

> 状态：**FROZEN BEFORE PRIMARY RUN_004**  
> 继承：`PREEMPT-Mem_第三步A_协议冻结与泄漏Manifest.md` 的全部 target、source、candidate ID/provenance、Need、gold evaluator、severity、witness firewall、seed、model、decoder、tool budget、checkpoint 与 eviction 定义。  
> 唯一修订：将 retrieval output 从 prompt 正文移至独立 external-memory tool channel。

## 修订原因

v1 在三分支使用同一 prompt template，但将 treatment-specific retrieval result 序列化进 `prompt.txt`。这可视为 memory treatment context，但用户要求“所有分支 prompt 相同”的最严格解释是 prompt bytes 完全一致。v2 因而作更严格实现：

- Full、Evicted、Restore 的 `prompt.txt` 必须 byte-identical；
- retrieval query 仍相同；
- retrieval result 只保存在独立的 `retrieval_results.json` tool-channel log；
- deterministic executor 只通过该 tool result 获得 `policy_id`；
- Evicted 无 result 时 fail closed；
- Full/Restore 的 tool result 必须同 record hash；
- 此修订不改变 target、Need、evaluator、severity、witness 或任何预算。

## 新冻结文件

- `third_step_a/config/cases_v2.json`：仅更新 protocol ID 与 agent prompt path；
- `third_step_a/prompts/agent_prompt_v2.txt`：删除 memory-result placeholder；
- 其他实现沿用修复后版本，并在 `execution_freeze_run_004_sha256.json` 中逐项固定 hash。

`run_001`、`run_002`、`run_003` 全部保留为开发轨迹；最终 gate 只使用 freeze 后、从零执行的 `run_004`。
