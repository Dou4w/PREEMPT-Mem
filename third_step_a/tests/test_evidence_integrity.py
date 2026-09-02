from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from aggregate_smoke import (  # noqa: E402
    REQUIRED_CAPABILITY_PROBES,
    expected_preaggregate_static_directories,
    expected_preaggregate_static_paths,
    expected_snapshot_artifact_paths,
    recompute_capability_probes,
    validate_exact_preaggregate_layout,
    validate_target_distractor_probe,
)
from target_distractor_probe import run_probe as run_target_distractor_probe  # noqa: E402
from evidence_integrity import (  # noqa: E402
    EvidenceError,
    assert_redacted_jsonl,
    build_manifest,
    canonical_json,
    logical_lf_sha256,
    redact_jsonl_file_new,
    sha256_bytes,
    verify_manifest,
)


@dataclass(frozen=True)
class ExampleRecord:
    name: str
    tags: set[str]


class EvidenceIntegrityTests(unittest.TestCase):
    def test_canonical_serializer_supports_dataclass_and_set(self) -> None:
        first = canonical_json(ExampleRecord("item", {"zeta", "alpha"}))
        second = canonical_json(ExampleRecord("item", {"alpha", "zeta"}))
        self.assertEqual(first, second)
        self.assertIn("alpha", first)
        self.assertNotEqual(canonical_json({"tags": {"alpha"}}), canonical_json({"tags": ["alpha"]}))
        self.assertNotEqual(
            canonical_json({"tags": {"alpha"}}),
            canonical_json({"tags": frozenset({"alpha"})}),
        )

    def test_logical_lf_and_file_hash_are_separate(self) -> None:
        text_lf = "one\ntwo\n"
        text_crlf = "one\r\ntwo\r\n"
        self.assertEqual(logical_lf_sha256(text_lf), logical_lf_sha256(text_crlf))
        self.assertNotEqual(
            sha256_bytes(text_lf.encode("utf-8")),
            sha256_bytes(text_crlf.encode("utf-8")),
        )

    def test_redaction_removes_jwt_and_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.jsonl"
            redacted = root / "api_calls.redacted.jsonl"
            raw.write_text(
                json.dumps(
                    {
                        "method": "POST",
                        "url": "/x",
                        "authorization": "Bearer abcdefghijklmnop",
                        "password": "low-entropy",
                        "amount": 98,
                        "content": "private note body",
                        "query": "private contact name",
                        "response": {"access_token": "eyJaaaaa.bbbbb.ccccc"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            attestation = redact_jsonl_file_new(
                raw,
                redacted,
                nonce="a" * 64,
                nonce_commitment_sha256="b" * 64,
            )
            self.assertGreaterEqual(attestation["redaction_count"], 3)
            self.assertEqual(assert_redacted_jsonl(redacted)["row_count"], 1)
            text = redacted.read_text(encoding="utf-8")
            self.assertNotIn("low-entropy", text)
            self.assertNotIn("eyJaaaaa", text)
            self.assertNotIn("private note body", text)
            self.assertNotIn("private contact name", text)
            self.assertNotIn('"amount":98', text)

    def test_manifest_detects_byte_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence.json").write_text("{}", encoding="utf-8")
            manifest = build_manifest(
                root,
                scope="unit-test",
                exclude_relative_paths=("manifest.json",),
            )
            verify_manifest(
                manifest,
                root,
                expected_scope="unit-test",
                expected_excluded_paths=("manifest.json",),
            )
            (root / "evidence.json").write_text('{"changed":true}', encoding="utf-8")
            with self.assertRaises(EvidenceError):
                verify_manifest(
                    manifest,
                    root,
                    expected_scope="unit-test",
                    expected_excluded_paths=("manifest.json",),
                )

    def test_capability_gate_ignores_claimed_summary(self) -> None:
        probes = {
            "all_denied": True,
            "probes": [
                {"probe": probe_id, "denied": True, "result": "PASS"}
                for probe_id in sorted(REQUIRED_CAPABILITY_PROBES)
            ],
        }
        # Claimed booleans alone are no longer evidence: the gate requires the
        # copied-worker process attestation and exact 10+final JSONL transcript.
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((EvidenceError, FileNotFoundError)):
                recompute_capability_probes(
                    probes, "test", branch_root=Path(directory)
                )

    def test_target_distractor_gate_recomputes_surface_hashes(self) -> None:
        document = run_target_distractor_probe()
        result = validate_target_distractor_probe(document)
        self.assertTrue(result["distractor_all_equal_recomputed"])

        tampered = copy.deepcopy(document)
        tampered["all_pass"] = False
        with self.assertRaises(EvidenceError):
            validate_target_distractor_probe(tampered)

        tampered = copy.deepcopy(document)
        tampered["effective_eviction_manifest"]["checks"] = []
        with self.assertRaises(EvidenceError):
            validate_target_distractor_probe(tampered)

        tampered = copy.deepcopy(document)
        first_surface = next(
            iter(tampered["distractor_equivalence_after_target_delete"]["surfaces"])
        )
        tampered["distractor_equivalence_after_target_delete"]["surfaces"][first_surface][
            "after_canonical_json"
        ] = '{"x":2}'
        with self.assertRaises(EvidenceError):
            validate_target_distractor_probe(tampered)

    def test_exact_layout_rejects_renamed_raw_dump(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory)
            for relative in expected_preaggregate_static_directories():
                (run_root / relative).mkdir(parents=True, exist_ok=True)
            for relative in expected_preaggregate_static_paths():
                path = run_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            for relative in expected_snapshot_artifact_paths():
                path = run_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            result = validate_exact_preaggregate_layout(run_root)
            self.assertTrue(result["all_static_paths_exact"])

            raw_dump = run_root / "cases/workflow/full/raw_tool_dump.json"
            raw_dump.write_text('{"secret":"unredacted"}', encoding="utf-8")
            with self.assertRaises(EvidenceError):
                validate_exact_preaggregate_layout(run_root)
            raw_dump.unlink()

            snapshot_dump = (
                run_root
                / "cases/workflow/full/db_snapshot_frozen/raw_tool_dump.json"
            )
            snapshot_dump.write_text('{"secret":"unredacted"}', encoding="utf-8")
            with self.assertRaises(EvidenceError):
                validate_exact_preaggregate_layout(run_root)


if __name__ == "__main__":
    unittest.main()
