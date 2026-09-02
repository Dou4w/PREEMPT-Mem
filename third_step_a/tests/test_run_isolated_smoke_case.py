from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "third_step_a/src"
sys.path.insert(0, str(SRC))

from evidence_integrity import sensitive_findings  # noqa: E402
from aggregate_smoke import (  # noqa: E402
    _forbidden_agent_key_findings as gate_forbidden_key_findings,
    _private_needle_partition as gate_private_needle_partition,
    evaluator_semantic_vector as gate_evaluator_semantic_vector,
    make_expected_record,
    record_artifact_mapping,
)
from run_isolated_smoke_case import (  # noqa: E402
    BRANCHES,
    RunnerEvidenceError,
    _redact_controller_transcript,
    _forbidden_agent_key_findings as runner_forbidden_key_findings,
    _write_redacted_tool_evidence,
    build_agent_request,
    build_firewall_leakage_manifest,
    build_raw_controller_firewall_scan,
    compose_treatment_blind_prompt,
    evaluator_semantic_vector,
    load_isolated_config,
    public_retrieval_projection,
    recompute_database_diff,
)


class IsolatedRunnerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_isolated_config(
            PROJECT_ROOT,
            PROJECT_ROOT / "third_step_a/config/cases_isolated_v1.json",
        )

    def test_evaluator_semantic_stability_excludes_only_failure_trace(self) -> None:
        first = {
            "difficulty": 2,
            "success": False,
            "num_tests": 2,
            "passes": [{"label": "ok", "requirement": "assert ok"}],
            "failures": [
                {
                    "label": "bad",
                    "requirement": "assert values match",
                    "trace": "AssertionError: {'a', 'b'}",
                }
            ],
        }
        second = json.loads(json.dumps(first))
        second["failures"][0]["trace"] = "AssertionError: {'b', 'a'}"
        self.assertEqual(
            evaluator_semantic_vector(first), evaluator_semantic_vector(second)
        )
        self.assertEqual(
            evaluator_semantic_vector(first),
            gate_evaluator_semantic_vector(first, "first"),
        )
        second["failures"][0]["requirement"] = "assert something else"
        self.assertNotEqual(
            evaluator_semantic_vector(first), evaluator_semantic_vector(second)
        )

    def test_record_artifact_mapping_is_json_native(self) -> None:
        case = json.loads(
            (PROJECT_ROOT / "third_step_a/config/cases_v3.json").read_text(
                encoding="utf-8"
            )
        )["cases"][0]
        mapping = record_artifact_mapping(make_expected_record(case))
        self.assertIsInstance(mapping["aliases"], list)
        self.assertIsInstance(mapping["retrieval_keys"], list)
        self.assertEqual(mapping, json.loads(json.dumps(mapping)))

    def test_public_contact_relationship_key_is_path_scoped(self) -> None:
        public_result = {
            "agent_rpc_transcript": [
                {
                    "response": {
                        "result": {
                            "contacts": [{"relationships": ["friend"]}]
                        }
                    }
                }
            ]
        }
        self.assertEqual(
            runner_forbidden_key_findings(public_result, path="$raw"), []
        )
        self.assertEqual(gate_forbidden_key_findings(public_result, path="$raw"), [])
        private_result = {"agent_final_result": {"relationship": 1}}
        self.assertEqual(
            len(runner_forbidden_key_findings(private_result, path="$raw")), 1
        )
        self.assertEqual(
            len(gate_forbidden_key_findings(private_result, path="$raw")), 1
        )
        spoofed_path_key = {
            "agent_final_result": {
                "spoof.agent_rpc_transcript[0].response.result": {
                    "relationships": 1
                }
            }
        }
        self.assertEqual(
            len(runner_forbidden_key_findings(spoofed_path_key, path="$raw")), 1
        )
        self.assertEqual(
            len(gate_forbidden_key_findings(spoofed_path_key, path="$raw")), 1
        )
        persisted_public_result = public_result["agent_rpc_transcript"]
        self.assertEqual(
            runner_forbidden_key_findings(
                persisted_public_result, path="$agent_rpc_transcript.jsonl"
            ),
            [],
        )
        self.assertEqual(
            gate_forbidden_key_findings(
                persisted_public_result, path="$agent_rpc_transcript.jsonl"
            ),
            [],
        )

    def test_agent_request_contains_exact_case_tool_allowlist_and_no_branch(self) -> None:
        template = (
            PROJECT_ROOT / self.config["global"]["prompt_path"]
        ).read_text(encoding="utf-8")
        for case in self.config["cases"]:
            case_id = case["case_id"]
            instruction = json.loads(
                (
                    PROJECT_ROOT
                    / "third_step_a/appworld_root/data/tasks"
                    / case["target_task"]["task_id"]
                    / "specs.json"
                ).read_text(encoding="utf-8")
            )["instruction"]
            prompt = compose_treatment_blind_prompt(template, instruction)
            allowed = sorted(
                self.config["isolation"]["allowed_tools_by_case"][case_id]
            )
            request = build_agent_request(
                target_instruction=instruction,
                prompt=prompt,
                retrieval_results=[],
                allowed_tools=allowed,
                nonce_commitment_sha256="0" * 64,
            )
            self.assertEqual(request["allowed_tools"], allowed)
            self.assertNotIn("allowed_apps", request)
            serialized = json.dumps(request, ensure_ascii=False).casefold()
            for forbidden_key in (
                '"branch"',
                '"need_label"',
                '"severity"',
                '"witness"',
                '"ground_truth"',
                '"gold_state_evaluator"',
            ):
                self.assertNotIn(forbidden_key, serialized)

    def test_aggregate_firewall_partition_and_recursive_key_gate(self) -> None:
        full_only = "FULL_ONLY_PUBLIC_MEMORY_VALUE_20260901"
        private_sources = {"relationship": {"need_definition": full_only}}
        full_needles, full_exclusions = gate_private_needle_partition(
            public={"target_instruction": "normal instruction", "retrieval": [full_only]},
            private_sources=private_sources,
        )
        evicted_needles, evicted_exclusions = gate_private_needle_partition(
            public={"target_instruction": "normal instruction", "retrieval": []},
            private_sources=private_sources,
        )
        self.assertEqual(full_needles, [])
        self.assertEqual(len(full_exclusions), 1)
        self.assertEqual(len(evicted_needles), 1)
        self.assertEqual(evicted_exclusions, [])
        for key, value in (("Need", 1), ("severity", 3), ("ground_truth", False)):
            with self.subTest(key=key):
                findings = gate_forbidden_key_findings(
                    {"safe": [{key: value}]}, path="$surface"
                )
                self.assertEqual(len(findings), 1)

    def test_evidence_redaction_is_independent_and_stricter_than_rpc_shape(self) -> None:
        raw = [
            {
                "call": {
                    "app": "file_system",
                    "api": "create_file",
                    "arguments": {
                        "file_path": "~/private/example.md",
                        "content": "private contents",
                        "access_token": "secret-token",
                    },
                },
                "response": {"ok": True},
            }
        ]
        rpc_shape = [
            {
                "call": {
                    "app": "file_system",
                    "api": "create_file",
                    "arguments": {
                        "file_path": "~/private/example.md",
                        "content": "<REDACTED:CONTENT:0123456789abcdef>",
                        "access_token": "<REDACTED:ACCESS_TOKEN:0123456789abcdef>",
                    },
                },
                "response": {"ok": True},
            }
        ]
        redacted, count, raw_sha256 = _redact_controller_transcript(
            raw_rows=raw,
            rpc_redacted_rows=rpc_shape,
            nonce="1" * 64,
        )
        self.assertGreaterEqual(count, 1)
        self.assertEqual(len(raw_sha256), 64)
        self.assertEqual(sensitive_findings(redacted), [])
        self.assertNotIn("~/private/example.md", json.dumps(redacted))

        with tempfile.TemporaryDirectory() as temporary:
            attestation = _write_redacted_tool_evidence(
                branch_root=Path(temporary),
                redacted_rows=redacted,
                raw_virtual_sha256=raw_sha256,
                rpc_redaction_count=2,
                evidence_additional_redaction_count=count,
                nonce_commitment_sha256="2" * 64,
            )
        self.assertEqual(attestation["rpc_redaction_count"], 2)
        self.assertEqual(attestation["evidence_additional_redaction_count"], count)
        self.assertEqual(attestation["total_redaction_count"], 2 + count)

    def test_raw_controller_firewall_scan_is_hash_only_and_detects_leakage(self) -> None:
        instruction = "Back up all notes into the normal public destination."
        public_record = {
            "memory_id": "memory-public-001",
            "memory_type": "external",
            "content": "Use the public backup procedure.",
            "aliases": [],
            "retrieval_keys": ["backup notes"],
            "metadata": {"policy_id": "policy-public-001"},
        }
        target_relationship = {
            "target": {"task_id": "task-public-001"},
            "need_definition": "PRIVATE_NEED_DEFINITION_20260901",
            "need_label": "PRIVATE_NEED_LABEL_20260901",
            "severity_application": "PRIVATE_SEVERITY_20260901",
            "gold_state_evaluator": "PRIVATE_GOLD_VECTOR_20260901",
        }
        witness = {"evidence": "PRIVATE_WITNESS_STRING_20260901"}
        canaries = {
            branch: {
                "caller_secret": "CALLER_SECRET_SHARED_20260901",
                "branch_canary": f"BRANCH_CANARY_{branch.upper()}_20260901",
            }
            for branch in BRANCHES
        }

        def contexts(
            *, leak: bool, forbidden_key: str | None = None
        ) -> dict[str, dict[str, object]]:
            return {
                branch: {
                    "initialize_wire": {
                        "type": "initialize",
                        "protocol_version": "v1",
                        "target_instruction": instruction,
                        "retrieval_results": (
                            [public_record] if branch in {"Full", "Restore"} else []
                        ),
                    },
                    "raw_transcript_controller_only": [
                        {
                            "call": {"app": "supervisor", "api": "complete_task"},
                            "response": {
                                "status": (
                                    "PRIVATE_WITNESS_STRING_20260901"
                                    if leak and branch == "Full"
                                    else "success"
                                )
                            },
                        }
                    ],
                    "raw_agent_result_controller_only": (
                        {"status": "success", forbidden_key: 1}
                        if forbidden_key is not None and branch == "Full"
                        else {"status": "success"}
                    ),
                    "raw_transcript_virtual_sha256": "a" * 64,
                }
                for branch in BRANCHES
            }

        result = build_raw_controller_firewall_scan(
            target_instruction=instruction,
            public_retrieval_records_by_branch={
                "Full": [public_record],
                "Evicted": [],
                "Restore": [public_record],
            },
            target_relationship=target_relationship,
            witness=witness,
            branch_canaries=canaries,
            branch_contexts=contexts(leak=False),
        )
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["total_private_exact_match_count"], 0)
        rendered = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("PRIVATE_WITNESS_STRING_20260901", rendered)
        self.assertNotIn("CALLER_SECRET_SHARED_20260901", rendered)
        with self.assertRaises(RunnerEvidenceError):
            build_raw_controller_firewall_scan(
                target_instruction=instruction,
                public_retrieval_records_by_branch={
                    "Full": [public_record],
                    "Evicted": [],
                    "Restore": [public_record],
                },
                target_relationship=target_relationship,
                witness=witness,
                branch_canaries=canaries,
                branch_contexts=contexts(leak=True),
            )
        for forbidden_key in (
            "Need",
            "severity",
            "target_relationship",
            "gold_state",
            "evaluator",
            "evaluation_code",
            "witness",
            "controller",
            "vault",
            "ground_truth",
            "world",
            "project_file",
            "manifest",
            "caller_secret",
            "inspect_stack",
            "store",
        ):
            with self.subTest(forbidden_key=forbidden_key), self.assertRaises(
                RunnerEvidenceError
            ):
                build_raw_controller_firewall_scan(
                    target_instruction=instruction,
                    public_retrieval_records_by_branch={
                        "Full": [public_record],
                        "Evicted": [],
                        "Restore": [public_record],
                    },
                    target_relationship=target_relationship,
                    witness=witness,
                    branch_canaries=canaries,
                    branch_contexts=contexts(
                        leak=False, forbidden_key=forbidden_key
                    ),
                )

    def test_evicted_does_not_inherit_full_public_value_exclusion(self) -> None:
        instruction = "Perform the same public target task in every branch."
        full_memory_value = "FULL_ONLY_PUBLIC_MEMORY_VALUE_20260901"
        public_record = {
            "memory_id": "memory-public-001",
            "memory_type": "external",
            "content": full_memory_value,
            "aliases": [],
            "retrieval_keys": ["public retrieval key"],
            "metadata": {"policy_id": "policy-public-001"},
        }
        relationship = {
            "need_definition": full_memory_value,
            "gold_state_evaluator": "PRIVATE_GOLD_VECTOR_20260901",
        }
        canaries = {
            branch: {
                "caller_secret": "CALLER_SECRET_SHARED_20260901",
                "branch_canary": f"BRANCH_CANARY_{branch.upper()}_20260901",
            }
            for branch in BRANCHES
        }
        contexts = {
            branch: {
                "initialize_wire": {
                    "type": "initialize",
                    "protocol_version": "v1",
                    "target_instruction": instruction,
                    "retrieval_results": (
                        [public_record] if branch in {"Full", "Restore"} else []
                    ),
                },
                "raw_transcript_controller_only": [
                    {
                        "call": {"app": "supervisor", "api": "complete_task"},
                        "response": {
                            "status": (
                                full_memory_value if branch == "Evicted" else "success"
                            )
                        },
                    }
                ],
                "raw_agent_result_controller_only": {"status": "success"},
                "raw_transcript_virtual_sha256": "a" * 64,
            }
            for branch in BRANCHES
        }
        with self.assertRaises(RunnerEvidenceError):
            build_raw_controller_firewall_scan(
                target_instruction=instruction,
                public_retrieval_records_by_branch={
                    "Full": [public_record],
                    "Evicted": [],
                    "Restore": [public_record],
                },
                target_relationship=relationship,
                witness={},
                branch_canaries=canaries,
                branch_contexts=contexts,
            )

    def test_persisted_firewall_rejects_recursive_private_keys_and_branch_leak(self) -> None:
        instruction = "Perform the same public target task in every branch."
        full_memory_value = "FULL_ONLY_PUBLIC_MEMORY_VALUE_20260901"
        record = {
            "memory_id": "memory-public-001",
            "memory_type": "external",
            "content": full_memory_value,
            "aliases": [],
            "retrieval_keys": ["public retrieval key"],
            "metadata": {"policy_id": "policy-public-001"},
        }
        public_by_branch = {
            "Full": [record],
            "Evicted": [],
            "Restore": [record],
        }
        relationship = {
            "need_definition": full_memory_value,
            "gold_state_evaluator": "PRIVATE_GOLD_VECTOR_20260901",
        }
        canaries = {
            branch: {
                "caller_secret": "CALLER_SECRET_SHARED_20260901",
                "branch_canary": f"BRANCH_CANARY_{branch.upper()}_20260901",
            }
            for branch in BRANCHES
        }
        branch_results = {
            branch: {"severity": 0, "severity_reason": "ordinary safe outcome"}
            for branch in BRANCHES
        }

        def write_surfaces(root: Path) -> None:
            for branch in BRANCHES:
                branch_root = root / branch.lower()
                branch_root.mkdir(parents=True)
                retrieval = public_by_branch[branch]
                (branch_root / "agent_initialize.json").write_text(
                    json.dumps(
                        {
                            "type": "initialize",
                            "protocol_version": "v1",
                            "target_instruction": instruction,
                            "retrieval_results": retrieval,
                        }
                    ),
                    encoding="utf-8",
                )
                (branch_root / "agent_request.json").write_text(
                    json.dumps(
                        {
                            "target_instruction": instruction,
                            "retrieval_results": retrieval,
                        }
                    ),
                    encoding="utf-8",
                )
                (branch_root / "agent_final.redacted.json").write_text(
                    json.dumps(
                        {
                            "type": "final",
                            "protocol_version": "v1",
                            "ok": True,
                            "result": {"status": "success"},
                            "tool_call_count": 1,
                        }
                    ),
                    encoding="utf-8",
                )
                (branch_root / "retrieval_results.json").write_text(
                    json.dumps(retrieval), encoding="utf-8"
                )
                (branch_root / "prompt.txt").write_text(instruction, encoding="utf-8")
                (branch_root / "agent_rpc_transcript.jsonl").write_text(
                    json.dumps({"call": {"app": "supervisor", "api": "complete_task"}})
                    + "\n",
                    encoding="utf-8",
                )
                (branch_root / "structured_agent_plan.json").write_text(
                    json.dumps({"agent_result": {"status": "success"}}),
                    encoding="utf-8",
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_surfaces(root)
            safe = build_firewall_leakage_manifest(
                case_root=root,
                target_instruction=instruction,
                public_retrieval_records_by_branch=public_by_branch,
                target_relationship=relationship,
                witness={},
                branch_results=branch_results,
                branch_canaries=canaries,
            )
            self.assertTrue(safe["all_pass"])
            self.assertEqual(safe["total_forbidden_private_key_count"], 0)
            (root / "full/structured_agent_plan.json").write_text(
                json.dumps({"agent_result": {"Need": 1}}), encoding="utf-8"
            )
            with self.assertRaises(RunnerEvidenceError):
                build_firewall_leakage_manifest(
                    case_root=root,
                    target_instruction=instruction,
                    public_retrieval_records_by_branch=public_by_branch,
                    target_relationship=relationship,
                    witness={},
                    branch_results=branch_results,
                    branch_canaries=canaries,
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_surfaces(root)
            (root / "evicted/prompt.txt").write_text(
                instruction + "\n" + full_memory_value, encoding="utf-8"
            )
            with self.assertRaises(RunnerEvidenceError):
                build_firewall_leakage_manifest(
                    case_root=root,
                    target_instruction=instruction,
                    public_retrieval_records_by_branch=public_by_branch,
                    target_relationship=relationship,
                    witness={},
                    branch_results=branch_results,
                    branch_canaries=canaries,
                )

    def test_public_retrieval_projection_drops_controller_private_fields(self) -> None:
        projected = public_retrieval_projection(
            [
                {
                    "memory_id": "memory-1",
                    "memory_type": "external",
                    "content": "policy body",
                    "aliases": ["alias"],
                    "retrieval_keys": ["query"],
                    "provenance": {"private": "source"},
                    "metadata": {
                        "policy_id": "policy-1",
                        "summary": "private summary",
                        "leakage_sentinel": "private sentinel",
                    },
                }
            ]
        )
        self.assertEqual(
            set(projected[0]),
            {
                "memory_id",
                "memory_type",
                "content",
                "aliases",
                "retrieval_keys",
                "metadata",
            },
        )
        self.assertEqual(projected[0]["metadata"], {"policy_id": "policy-1"})
        self.assertNotIn("provenance", projected[0])

    def test_database_diff_recomputes_jsonl_multiset_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left, right = root / "left", root / "right"
            left.mkdir()
            right.mkdir()
            (left / "app.jsonl").write_text('{"id":1}\n', encoding="utf-8")
            (right / "app.jsonl").write_text(
                '{"id":1}\n{"id":2}\n', encoding="utf-8"
            )
            result = recompute_database_diff(left, right)
            self.assertFalse(result["all_files_byte_equal"])
            self.assertEqual(result["files"][0]["removed_count"], 0)
            self.assertEqual(result["files"][0]["added_count"], 1)


if __name__ == "__main__":
    unittest.main()
