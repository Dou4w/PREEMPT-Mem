from __future__ import annotations

"""Agent-role negative capability probe worker for the isolated JSONL boundary.

The controller copies this stdlib-only source to a fresh temporary directory and
launches it with ``python -I``. Each forbidden request must receive the typed
``CAPABILITY_DENIED`` result. This tests the structured tool interface; it does
not claim to be an arbitrary-code operating-system sandbox.
"""

import json
import sys
from typing import Any


PROTOCOL_VERSION = "preempt3a-isolated-tool-rpc-v1"
PROBES: tuple[tuple[str, str, str, dict[str, Any]], ...] = (
    ("caller_secret", "controller", "read_caller_secret", {}),
    ("inspect_stack", "runtime", "inspect_stack", {}),
    ("branch", "controller", "get_branch", {}),
    ("project_file", "host_files", "read_project_file", {"path": "sentinel"}),
    ("world_object", "controller", "get_world", {}),
    ("memory_store", "controller", "get_store", {}),
    ("controller_vault", "controller", "get_vault", {}),
    ("ground_truth", "ground_truth", "load", {}),
    ("evaluation_code", "evaluation", "read_code", {}),
    ("controller_directory", "host_files", "list_controller_directory", {}),
)


def _emit(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()


def _read() -> dict[str, Any]:
    line = sys.stdin.readline()
    if not line:
        raise RuntimeError("controller closed the capability-probe stream")
    value = json.loads(line)
    if not isinstance(value, dict):
        raise RuntimeError("capability-probe response is not an object")
    return value


def main() -> None:
    names: list[str] = []
    try:
        for index, (name, app, api, arguments) in enumerate(PROBES, start=1):
            request_id = f"probe-{index:04d}-{name}"
            _emit(
                {
                    "type": "tool_call",
                    "protocol_version": PROTOCOL_VERSION,
                    "request_id": request_id,
                    "app": app,
                    "api": api,
                    "arguments": arguments,
                }
            )
            response = _read()
            expected_keys = {"type", "protocol_version", "request_id", "ok", "result"}
            if set(response) != expected_keys:
                raise RuntimeError(f"probe {name} response schema is not exact")
            if response.get("type") != "tool_result":
                raise RuntimeError(f"probe {name} did not receive tool_result")
            if response.get("protocol_version") != PROTOCOL_VERSION:
                raise RuntimeError(f"probe {name} protocol version mismatch")
            if response.get("request_id") != request_id:
                raise RuntimeError(f"probe {name} request id mismatch")
            if response.get("ok") is not False:
                raise RuntimeError(f"forbidden probe {name} unexpectedly succeeded")
            result = response.get("result")
            if not isinstance(result, dict) or result.get("error_code") != "CAPABILITY_DENIED":
                raise RuntimeError(f"probe {name} did not receive CAPABILITY_DENIED")
            names.append(name)
        _emit(
            {
                "type": "final",
                "protocol_version": PROTOCOL_VERSION,
                "ok": True,
                "result": {
                    "all_denied": True,
                    "probe_count": len(names),
                    "probe_names": names,
                },
            }
        )
    except Exception as error:
        _emit(
            {
                "type": "final",
                "protocol_version": PROTOCOL_VERSION,
                "ok": False,
                "result": {
                    "all_denied": False,
                    "probe_count": len(names),
                    "probe_names": names,
                    "error_type": type(error).__name__,
                },
            }
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
