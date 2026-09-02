from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_memory_store import AuditMemoryStore, MemoryRecord


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[2]
    output_path = (project_root / args.output).resolve()

    record = MemoryRecord(
        memory_id="pm3a-interface-probe-v1",
        memory_type="episodic_semantic",
        content="Probe memory: export notes through the file-system API.",
        provenance={
            "source_episode": "structural-probe-only",
            "source_type": "constructed/semi-synthetic",
            "created_by": "preempt-3a-controller",
        },
        aliases=("interface-probe",),
        retrieval_keys=("export", "notes", "file system"),
        metadata={
            "summary": "interface-only probe",
            "graph_edges": [],
            "policy_id": "probe_policy_v1",
            "leakage_sentinel": "PM3A-SENTINEL::interface-probe::fixed",
        },
    )
    store = AuditMemoryStore()
    put_result = store.put(record)
    interface_before = store.interface_manifest(record.memory_id, "export notes to file system")
    delete_result = store.delete(record.memory_id)
    eviction = store.effective_eviction_manifest(record)
    cache_after_negative_probe = dict(store.retrieval_cache)
    store.agent_view().retrieve("current unrelated future task", limit=1)
    eviction_after_agent_negative_retrieval = store.effective_eviction_manifest(record)
    cache_after_agent_negative_retrieval = dict(store.retrieval_cache)
    restore_result = store.restore(record.memory_id)
    interface_after = store.interface_manifest(record.memory_id, "export notes to file system")
    result = {
        "probe_version": "preempt-3a-memory-store-probe-v1",
        "put": put_result,
        "interface_before_delete": interface_before,
        "delete": delete_result,
        "effective_eviction": eviction,
        "cache_after_negative_probe": cache_after_negative_probe,
        "effective_eviction_after_agent_negative_retrieval": eviction_after_agent_negative_retrieval,
        "cache_after_agent_negative_retrieval": cache_after_agent_negative_retrieval,
        "restore": restore_result,
        "interface_after_restore": interface_after,
        "same_record_after_restore": (
            put_result["record_sha256"] == restore_result["record_sha256"]
        ),
    }
    result["all_required_checks_pass"] = bool(
        all(interface_before.values())
        and eviction["all_pass"]
        and not cache_after_negative_probe
        and eviction_after_agent_negative_retrieval["all_pass"]
        and cache_after_agent_negative_retrieval == {"current unrelated future task": []}
        and all(interface_after.values())
        and result["same_record_after_restore"]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_required_checks_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
