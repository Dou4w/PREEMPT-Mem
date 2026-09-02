from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass, replace
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from audit_memory_store import AuditMemoryStore, MemoryRecord, canonical_json  # noqa: E402
from target_distractor_probe import _make_records, run_probe  # noqa: E402


@dataclass(frozen=True)
class NestedFixture:
    name: str
    coordinates: tuple[int, ...]
    labels: frozenset[str]


class CanonicalSerializerTests(unittest.TestCase):
    def test_dataclass_tuple_set_and_non_empty_memory_record_are_stable(self) -> None:
        record = MemoryRecord(
            memory_id="serializer-record",
            memory_type="test",
            content="non-empty record",
            provenance={"source": "unit-test"},
            aliases=("serializer-alias",),
            retrieval_keys=("serializer key",),
            metadata={"labels": {"zeta", "alpha"}},
        )
        first = canonical_json(
            {
                "record": record,
                "fixture": NestedFixture(
                    name="nested", coordinates=(3, 1, 2), labels=frozenset({"b", "a"})
                ),
            }
        )
        second = canonical_json(
            {
                "fixture": NestedFixture(
                    name="nested", coordinates=(3, 1, 2), labels=frozenset({"a", "b"})
                ),
                "record": record,
            }
        )
        self.assertEqual(first, second)
        decoded = json.loads(first)
        self.assertEqual(decoded["record"]["memory_id"], "serializer-record")
        self.assertEqual(
            decoded["record"]["metadata"]["labels"],
            {"__canonical_type__": "set", "items": ["alpha", "zeta"]},
        )
        self.assertEqual(decoded["fixture"]["coordinates"], [3, 1, 2])

    def test_reserved_canonical_type_tag_cannot_spoof_a_set(self) -> None:
        with self.assertRaisesRegex(ValueError, "reserved"):
            canonical_json(
                {"__canonical_type__": "set", "items": ["spoofed", "payload"]}
            )
        with self.assertRaisesRegex(ValueError, "reserved"):
            canonical_json(
                {"nested": {"__canonical_type__": "frozenset", "items": []}}
            )


class TargetScopedInvalidationTests(unittest.TestCase):
    def test_target_delete_preserves_distractor_on_every_surface(self) -> None:
        result = run_probe()
        self.assertTrue(result["serializer_checks"]["all_pass"])
        self.assertTrue(result["positive_surface_coverage"]["all_surfaces_nonempty"])
        self.assertTrue(result["positive_component_coverage"]["all_components_nonempty"])
        self.assertTrue(result["target_unreachable"]["all_pass"])
        self.assertTrue(
            result["target_component_absence_after_delete"][
                "all_components_absent"
            ]
        )
        self.assertTrue(
            result["distractor_equivalence_after_target_delete"][
                "all_surfaces_equal"
            ]
        )
        for evidence in result["distractor_equivalence_after_target_delete"][
            "surfaces"
        ].values():
            self.assertTrue(evidence["equal"])
            self.assertEqual(evidence["before_sha256"], evidence["after_sha256"])
        self.assertTrue(result["restore_identity"]["all_pass"])
        self.assertTrue(result["all_pass"])

    def test_shared_keyword_cache_and_ann_collision_keep_distractor(self) -> None:
        result = run_probe()["shared_keyword_cache_and_ann_collision"]
        self.assertTrue(result["checks"]["all_pass"])
        self.assertEqual(
            result["before_delete"]["ann_members"],
            ["pm3ar-distractor-v1", "pm3ar-target-v1"],
        )
        self.assertEqual(
            result["after_delete"]["ann_members"], ["pm3ar-distractor-v1"]
        )
        self.assertEqual(
            result["after_delete"]["shared_cache_ids"],
            ["pm3ar-distractor-v1"],
        )
        self.assertEqual(
            sorted(result["before_delete"]["target_derived_mixed_cache_ids"]),
            ["pm3ar-distractor-v1", "pm3ar-target-v1"],
        )
        self.assertFalse(
            result["after_delete"]["target_derived_mixed_cache_present"]
        )

    def test_unique_unscoped_summary_is_removed_and_distractor_is_equivalent(self) -> None:
        result = run_probe()
        summary = result["unscoped_summary_fallback"]
        self.assertTrue(summary["checks"]["all_pass"])
        self.assertTrue(summary["before_delete"]["target_present"])
        self.assertFalse(summary["after_delete"]["target_present"])
        self.assertTrue(summary["after_delete"]["distractor_present"])
        self.assertTrue(
            result["distractor_equivalence_after_target_delete"][
                "all_surfaces_equal"
            ]
        )

    def test_shared_unscoped_summary_is_preserved_as_distractor_owned(self) -> None:
        target, distractor = _make_records()
        shared_summary = "legitimate shared summary fallback"
        target = replace(
            target, metadata={**target.metadata, "summary": shared_summary}
        )
        distractor = replace(
            distractor, metadata={**distractor.metadata, "summary": shared_summary}
        )
        store = AuditMemoryStore()
        store.put(target)
        store.put(distractor)
        store.tool_cache["legacy-shared-summary"] = shared_summary

        store.delete(target.memory_id)

        self.assertEqual(store.tool_cache["legacy-shared-summary"], shared_summary)
        manifest = store.effective_eviction_manifest(target)
        self.assertTrue(manifest["all_pass"])
        self.assertIn(
            "metadata_summary",
            {item["kind"] for item in manifest["shared_needle_manifest"]},
        )

    def test_recursive_metadata_provenance_and_graph_scalars_are_pruned(self) -> None:
        target, distractor = _make_records()
        target = replace(
            target,
            metadata={
                **target.metadata,
                "nested": {"secret": "target-only nested metadata scalar"},
            },
        )
        distractor = replace(
            distractor,
            metadata={
                **distractor.metadata,
                "nested": {"secret": "distractor nested metadata scalar"},
            },
        )
        store = AuditMemoryStore()
        store.put(target)
        store.put(distractor)
        store.tool_cache.update(
            {
                "neutral-a": target.metadata["graph_edges"][0],
                "neutral-b": target.metadata["nested"]["secret"],
                "neutral-c": target.provenance["source_episode"],
                "neutral-d": distractor.metadata["graph_edges"][0],
                "neutral-e": distractor.metadata["nested"]["secret"],
                "neutral-f": distractor.provenance["source_episode"],
            }
        )

        store.delete(target.memory_id)

        self.assertNotIn("neutral-a", store.tool_cache)
        self.assertNotIn("neutral-b", store.tool_cache)
        self.assertNotIn("neutral-c", store.tool_cache)
        self.assertEqual(
            store.tool_cache["neutral-d"], distractor.metadata["graph_edges"][0]
        )
        self.assertEqual(
            store.tool_cache["neutral-e"], distractor.metadata["nested"]["secret"]
        )
        self.assertEqual(
            store.tool_cache["neutral-f"], distractor.provenance["source_episode"]
        )
        manifest = store.effective_eviction_manifest(target)
        self.assertTrue(manifest["all_pass"])
        enforced_kinds = {
            item["kind"] for item in manifest["forbidden_needle_manifest"]
        }
        shared_kinds = {item["kind"] for item in manifest["shared_needle_manifest"]}
        self.assertIn("graph_edge", enforced_kinds)
        self.assertIn("metadata_scalar::nested.secret", enforced_kinds)
        self.assertIn("provenance_scalar::source_episode", enforced_kinds)
        self.assertIn("provenance_scalar::source_type", shared_kinds)
        self.assertIn("provenance_scalar::created_by", shared_kinds)

    def test_explicit_distractor_provenance_overrides_shared_text(self) -> None:
        target, distractor = _make_records()
        store = AuditMemoryStore()
        store.put(target)
        store.put(distractor)
        store.tool_cache["distractor-owned"] = store.scoped_value(
            target.content, distractor.memory_id
        )
        store.tool_cache["target-owned"] = store.scoped_value(
            "paraphrase without a target literal", target.memory_id
        )

        store.delete(target.memory_id)

        self.assertIn("distractor-owned", store.tool_cache)
        self.assertNotIn("target-owned", store.tool_cache)
        self.assertEqual(
            store.tool_cache["distractor-owned"].depends_on_memory_ids,
            (distractor.memory_id,),
        )
        self.assertTrue(store.effective_eviction_manifest(target)["all_pass"])

    def test_nested_target_scope_cannot_hide_under_distractor_mapping(self) -> None:
        target, distractor = _make_records()
        store = AuditMemoryStore()
        store.put(target)
        store.put(distractor)
        store.tool_cache["mixed-owner"] = {
            "memory_id": distractor.memory_id,
            "shared_payload": target.content,
            "nested": {
                "memory_id": target.memory_id,
                "secret": target.aliases[0],
            },
        }

        store.delete(target.memory_id)

        mixed = store.tool_cache["mixed-owner"]
        self.assertEqual(mixed["memory_id"], distractor.memory_id)
        self.assertEqual(mixed["shared_payload"], target.content)
        self.assertNotIn("nested", mixed)
        self.assertTrue(store.effective_eviction_manifest(target)["all_pass"])

    def test_effective_eviction_detects_target_unique_unscoped_residue(self) -> None:
        target, distractor = _make_records()
        store = AuditMemoryStore()
        store.put(target)
        store.put(distractor)
        store.delete(target.memory_id)
        # Simulate a post-delete buggy subsystem reintroducing a unique target
        # scalar: the manifest must independently catch it.
        store.tool_cache["legacy-residue"] = target.aliases[0]
        manifest = store.effective_eviction_manifest(target)

        self.assertFalse(manifest["all_pass"])
        failing = {
            check["surface"]
            for check in manifest["checks"]
            if check["result"] == "FAIL"
        }
        self.assertIn("retrieval_tool_summary_caches", failing)
        self.assertIn("component::tool_cache", failing)
        enforced_kinds = {
            item["kind"] for item in manifest["forbidden_needle_manifest"]
        }
        shared_kinds = {item["kind"] for item in manifest["shared_needle_manifest"]}
        self.assertIn("alias", enforced_kinds)
        self.assertIn("exact_content", shared_kinds)
        self.assertIn("content_sha256", shared_kinds)


if __name__ == "__main__":
    unittest.main()
