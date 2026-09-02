from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import sys


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from isolated_rpc import (  # noqa: E402
    CAPABILITY_PROBES,
    WORKER_ENVIRONMENT_KEYS,
    CapabilityDeniedError,
    PublicAppWorldGateway,
    redact_rpc_evidence,
    run_capability_probes,
    run_structured_agent,
)
from isolated_agent_worker import _current_datetime  # noqa: E402


class _FakeWorld:
    def __init__(self) -> None:
        self.task = SimpleNamespace(ground_truth=None)
        self.completed: str | None = None
        self.created: list[dict[str, Any]] = []
        self.apis = {
            "supervisor": {
                "show_profile": lambda: {"email": "user@example.test", "phone_number": "555"},
                "show_account_passwords": lambda: [
                    {"account_name": "simple_note", "password": "note-secret"},
                    {"account_name": "file_system", "password": "file-secret"},
                ],
                "complete_task": self._complete_task,
                "unused_public_api": lambda: {"unexpected": True},
            },
            "simple_note": {
                "login": lambda **_: {"access_token": "note-token"},
                "search_notes": self._search_notes,
                "show_note": lambda **_: {"content": "body"},
            },
            "file_system": {
                "login": lambda **_: {"access_token": "file-token"},
                "create_file": self._create_file,
            },
        }

    def _complete_task(self, status: str) -> dict[str, str]:
        self.completed = status
        return {"status": status}

    @staticmethod
    def _search_notes(page_index: int, **_: Any) -> list[dict[str, Any]]:
        return [{"note_id": 1, "title": "A Note"}] if page_index == 0 else []

    def _create_file(self, **kwargs: Any) -> dict[str, str]:
        self.created.append(kwargs)
        return {"path": kwargs["file_path"]}


class IsolatedRpcTests(unittest.TestCase):
    WORKFLOW_ALLOWLIST = {
        "supervisor.show_profile",
        "supervisor.show_account_passwords",
        "supervisor.complete_task",
        "simple_note.login",
        "simple_note.search_notes",
        "simple_note.show_note",
        "file_system.login",
        "file_system.create_file",
    }

    def test_appworld_public_clock_shape_is_parseable(self) -> None:
        parsed = _current_datetime({"date": "Thursday, May 18, 2023", "time": "12:00 PM"})
        self.assertEqual(parsed.isoformat(), "2023-05-18T12:00:00")

    def test_config_matches_enforced_environment_and_probe_contract(self) -> None:
        config = json.loads(
            (SRC.parent / "config/cases_isolated_v1.json").read_text(encoding="utf-8")
        )
        isolation = config["isolation"]
        self.assertEqual(
            isolation["worker_environment_allowlist"], sorted(WORKER_ENVIRONMENT_KEYS)
        )
        self.assertEqual(
            isolation["required_denied_capability_probes"],
            [item[0] for item in CAPABILITY_PROBES],
        )
        self.assertFalse(isolation["windows_arbitrary_code_sandbox_claimed"])
        self.assertFalse(isolation["os_filesystem_sandbox_claimed"])

    def test_all_private_capability_probes_are_denied(self) -> None:
        gateway = PublicAppWorldGateway(
            _FakeWorld(), allowed_tools=self.WORKFLOW_ALLOWLIST
        )
        with tempfile.TemporaryDirectory() as temp:
            result = run_capability_probes(
                gateway,
                worker_path=SRC / "isolated_capability_probe_worker.py",
                sandbox_directory=Path(temp) / "probe",
            )
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["probe_count"], 10)
        self.assertTrue(all(item["denied"] for item in result["probes"]))
        self.assertTrue(
            all(item["protocol_error"] == "CAPABILITY_DENIED" for item in result["probes"])
        )
        process = result["process_attestation"]
        self.assertEqual(process["role"], "agent_capability_probe")
        self.assertEqual(process["exit_code"], 0)
        self.assertEqual(process["boundary"], "structured_json_tool_call_rpc")
        self.assertTrue(process["worker_copied_to_temporary_directory"])
        self.assertFalse(process["worker_command_contains_project_path"])
        self.assertFalse(process["project_root_path_disclosed"])
        self.assertTrue(process["interpreter_outside_project"])
        self.assertEqual(result["transcript_row_count"], 11)
        self.assertEqual(len(result["transcript"]), 11)
        self.assertEqual(set(result["transcript"][-1]), {"final"})
        transcript_bytes = "".join(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for row in result["transcript"]
        ).encode("utf-8")
        self.assertEqual(
            result["transcript_virtual_sha256"],
            hashlib.sha256(transcript_bytes).hexdigest(),
        )

    def test_non_allowlisted_public_api_is_denied(self) -> None:
        gateway = PublicAppWorldGateway(
            _FakeWorld(), allowed_tools=self.WORKFLOW_ALLOWLIST
        )
        with self.assertRaises(CapabilityDeniedError):
            gateway.dispatch(
                {
                    "type": "tool_call",
                    "protocol_version": "preempt3a-isolated-tool-rpc-v1",
                    "request_id": "negative-1",
                    "app": "supervisor",
                    "api": "unused_public_api",
                    "arguments": {},
                }
            )

    def test_structured_workflow_uses_only_gateway_calls(self) -> None:
        world = _FakeWorld()
        record = {
            "memory_id": "m1",
            "content": "export notes",
            "metadata": {"policy_id": "workflow_export_notes_v1"},
        }
        worker = SRC / "isolated_agent_worker.py"
        with tempfile.TemporaryDirectory() as temp:
            sandbox = Path(temp) / "agent"
            result = run_structured_agent(
                world=world,
                target_instruction='Back up all notes to "~/backup/" directory',
                retrieval_results=[record],
                allowed_tools=self.WORKFLOW_ALLOWLIST,
                redaction_nonce="ab" * 32,
                worker_path=worker,
                sandbox_directory=sandbox,
            )
        self.assertEqual(world.completed, "success")
        self.assertEqual(len(world.created), 1)
        self.assertEqual(result["tool_call_count"], 17)
        rendered = str(result["transcript_redacted"])
        self.assertNotIn("note-token", rendered)
        self.assertNotIn("user@example.test", rendered)
        self.assertNotIn("body", rendered)
        self.assertGreater(result["redaction_attestation"]["redaction_count"], 0)
        self.assertEqual(result["redaction_attestation"]["post_redaction_finding_count"], 0)
        process = result["process_attestation"]
        self.assertFalse(process["arbitrary_code_sandbox_claimed"])
        self.assertFalse(process["os_filesystem_sandbox_claimed"])
        self.assertTrue(process["source_copy_hash_equal"])
        self.assertTrue(process["interpreter_outside_project"])
        self.assertEqual(process["environment_key_names"], sorted(WORKER_ENVIRONMENT_KEYS))
        self.assertFalse(process["worker_command_contains_project_path"])

    def test_nonce_redaction_covers_required_sensitive_fragments(self) -> None:
        payload = {
            "tokens": "tok",
            "password": "pw",
            "secret": "s",
            "username": "user",
            "email": "u@example.test",
            "phone": "555",
            "message": "hello",
            "content": "private body",
            "amount": 42,
        }
        redacted_a, attestation_a = redact_rpc_evidence(payload, nonce="cd" * 32)
        redacted_b, attestation_b = redact_rpc_evidence(payload, nonce="cd" * 32)
        self.assertEqual(redacted_a, redacted_b)
        self.assertEqual(attestation_a, attestation_b)
        self.assertEqual(attestation_a["redaction_count"], len(payload))
        self.assertTrue(all(str(value).startswith("<REDACTED:") for value in redacted_a.values()))

    def test_redaction_never_rewrites_rpc_protocol_tool_names(self) -> None:
        payload = {
            "transcript": [
                {
                    "call": {
                        "type": "tool_call",
                        "protocol_version": "preempt3a-tool-rpc-v1",
                        "request_id": "call-0001",
                        "app": "simple_note",
                        "api": "login",
                        "arguments": {"username": "user@example.test", "password": "pw"},
                    },
                    "response": {
                        "type": "tool_result",
                        "protocol_version": "preempt3a-tool-rpc-v1",
                        "request_id": "call-0001",
                        "ok": True,
                        "result": {
                            "account_name": "file_system",
                            "access_token": "secret-token",
                        },
                    },
                },
                {
                    "call": {
                        "type": "tool_call",
                        "protocol_version": "preempt3a-tool-rpc-v1",
                        "request_id": "call-0002",
                        "app": "file_system",
                        "api": "login",
                        "arguments": {"password": "secret-token"},
                    },
                    "response": {
                        "type": "tool_result",
                        "protocol_version": "preempt3a-tool-rpc-v1",
                        "request_id": "call-0002",
                        "ok": True,
                        "result": {"message": "done"},
                    },
                },
            ],
            "agent_result": {"result": "file_system"},
        }
        redacted, attestation = redact_rpc_evidence(payload, nonce="ef" * 32)
        calls = [row["call"] for row in redacted["transcript"]]
        self.assertEqual(
            [(call["app"], call["api"]) for call in calls],
            [("simple_note", "login"), ("file_system", "login")],
        )
        rendered = json.dumps(redacted, ensure_ascii=False)
        self.assertNotIn("user@example.test", rendered)
        self.assertNotIn("secret-token", rendered)
        self.assertGreater(attestation["redaction_count"], 0)

    def test_agent_world_with_ground_truth_is_rejected(self) -> None:
        world = _FakeWorld()
        world.task.ground_truth = object()
        with self.assertRaises(RuntimeError):
            PublicAppWorldGateway(world, allowed_tools=self.WORKFLOW_ALLOWLIST)


if __name__ == "__main__":
    unittest.main()
