from __future__ import annotations

"""Structured PREEMPT-Mem agent worker.

This process never imports AppWorld and never evaluates model- or controller-
supplied Python.  Its complete external capability is the JSONL protocol on
stdin/stdout.  The controller is responsible for validating and executing
each requested public AppWorld API call.
"""

import json
import re
import sys
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any


PROTOCOL_VERSION = "preempt3a-isolated-tool-rpc-v1"
ALLOWED_INITIALIZE_KEYS = {
    "type",
    "protocol_version",
    "target_instruction",
    "retrieval_results",
}
FORBIDDEN_INPUT_KEY_FRAGMENTS = {
    "branch",
    "controller",
    "evaluation",
    "evaluator",
    "gold",
    "ground_truth",
    "manifest",
    "need_label",
    "project_root",
    "severity",
    "vault",
    "witness",
    "world",
}


class ProtocolError(RuntimeError):
    pass


def _emit(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()


def _read_message() -> dict[str, Any]:
    line = sys.stdin.readline()
    if not line:
        raise ProtocolError("controller closed the RPC stream")
    message = json.loads(line)
    if not isinstance(message, dict):
        raise ProtocolError("RPC message must be a JSON object")
    return message


def _validate_no_private_keys(value: Any, path: str = "request") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if any(fragment in normalized for fragment in FORBIDDEN_INPUT_KEY_FRAGMENTS):
                raise ProtocolError(f"private controller key rejected at {path}.{key}")
            _validate_no_private_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_private_keys(child, f"{path}[{index}]")


def _call(app: str, api: str, **arguments: Any) -> dict[str, Any]:
    response: dict[str, Any] = yield {
        "type": "tool_call",
        "app": app,
        "api": api,
        "arguments": arguments,
    }
    return response


def _items(response: Any, description: str) -> list[Any]:
    if not isinstance(response, list):
        raise ProtocolError(f"{description} must return a list")
    return response


def _mapping(response: Any, description: str) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ProtocolError(f"{description} must return an object")
    return response


def _access_token(response: Any, description: str) -> str:
    payload = _mapping(response, description)
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise ProtocolError(f"{description} did not return an access token")
    return token


def _current_datetime(response: Any) -> datetime:
    candidates: list[str] = []
    if isinstance(response, str):
        candidates.append(response)
    elif isinstance(response, dict):
        for key in ("date_and_time", "datetime", "current_datetime", "iso"):
            if isinstance(response.get(key), str):
                candidates.append(response[key])
        date = response.get("date")
        time = response.get("time")
        if isinstance(date, str):
            candidates.append(date + (f"T{time}" if isinstance(time, str) else ""))
        candidates.extend(value for value in response.values() if isinstance(value, str))
    for candidate in candidates:
        cleaned = candidate.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            pass
    if isinstance(response, dict):
        date = response.get("date")
        time = response.get("time")
        if isinstance(date, str) and isinstance(time, str):
            for format_string in ("%A, %B %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
                try:
                    return datetime.strptime(f"{date} {time}", format_string)
                except ValueError:
                    pass
    raise ProtocolError("phone.get_current_date_and_time returned no parseable ISO datetime")


def _parse_iso_datetime(value: Any, description: str) -> datetime:
    if not isinstance(value, str):
        raise ProtocolError(f"{description} is not a string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProtocolError(f"{description} is not ISO-8601") from error


def _pendulum_prefix(created_at: datetime, format_string: str) -> str:
    # Frozen cases use YYYY_MM_DD-.  The explicit mapping avoids importing the
    # AppWorld/Pendulum runtime into the agent process.
    translated = format_string
    for token, value in (
        ("YYYY", f"{created_at.year:04d}"),
        ("MM", f"{created_at.month:02d}"),
        ("DD", f"{created_at.day:02d}"),
    ):
        translated = translated.replace(token, value)
    return translated


def _profile_and_passwords() -> Generator[dict[str, Any], dict[str, Any], tuple[dict[str, Any], dict[str, str]]]:
    profile = _mapping((yield from _call("supervisor", "show_profile")), "supervisor profile")
    rows = _items(
        (yield from _call("supervisor", "show_account_passwords")),
        "supervisor account passwords",
    )
    passwords: dict[str, str] = {}
    for row in rows:
        row = _mapping(row, "account password row")
        account_name = row.get("account_name")
        password = row.get("password")
        if isinstance(account_name, str) and isinstance(password, str):
            passwords[account_name] = password
    return profile, passwords


def _workflow(instruction: str) -> Generator[dict[str, Any], dict[str, Any], dict[str, Any]]:
    match = re.search(r'to\s+"(~/[^"]+/)"\s+directory', instruction, flags=re.IGNORECASE)
    if not match:
        yield from _call("supervisor", "complete_task", status="fail")
        return {"status": "fail_closed", "reason": "workflow instruction did not match"}
    backup_directory = match.group(1)
    profile, passwords = yield from _profile_and_passwords()
    email = profile.get("email")
    if not isinstance(email, str):
        raise ProtocolError("supervisor profile has no email")
    note_token = _access_token(
        (yield from _call("simple_note", "login", username=email, password=passwords["simple_note"])),
        "simple_note.login",
    )
    file_token = _access_token(
        (yield from _call("file_system", "login", username=email, password=passwords["file_system"])),
        "file_system.login",
    )
    notes: list[dict[str, Any]] = []
    for page_index in range(10):
        page = _items(
            (yield from _call(
                "simple_note", "search_notes", page_index=page_index, access_token=note_token
            )),
            "simple_note.search_notes",
        )
        notes.extend(_mapping(item, "note search row") for item in page)
    for note in notes:
        note_id = note.get("note_id")
        title = note.get("title")
        if not isinstance(title, str):
            raise ProtocolError("note search row has no title")
        full_note = _mapping(
            (yield from _call("simple_note", "show_note", note_id=note_id, access_token=note_token)),
            "simple_note.show_note",
        )
        content = full_note.get("content")
        if not isinstance(content, str):
            raise ProtocolError("note has no content")
        yield from _call(
            "file_system",
            "create_file",
            file_path=backup_directory + title.replace(" ", "_") + ".md",
            content=content,
            access_token=file_token,
        )
    yield from _call("supervisor", "complete_task", status="success")
    return {"status": "success", "notes_exported": len(notes)}


def _gotcha(instruction: str) -> Generator[dict[str, Any], dict[str, Any], dict[str, Any]]:
    prefix_match = re.search(r'prefix\s+"([^"]+)"', instruction, flags=re.IGNORECASE)
    directories = re.findall(r'(~\/[A-Za-z0-9_.\/-]+\/)', instruction)
    if not prefix_match or len(directories) < 2:
        yield from _call("supervisor", "complete_task", status="fail")
        return {"status": "fail_closed", "reason": "gotcha instruction did not match"}
    prefix_format = prefix_match.group(1)
    source_directory, destination_directory = directories[:2]
    profile, passwords = yield from _profile_and_passwords()
    email = profile.get("email")
    if not isinstance(email, str):
        raise ProtocolError("supervisor profile has no email")
    file_token = _access_token(
        (yield from _call("file_system", "login", username=email, password=passwords["file_system"])),
        "file_system.login",
    )
    now = _current_datetime((yield from _call("phone", "get_current_date_and_time")))
    paths = list(
        _items(
            (yield from _call(
                "file_system", "show_directory", directory_path=source_directory, access_token=file_token
            )),
            "file_system.show_directory",
        )
    )
    moved = 0
    for original_path in paths:
        if not isinstance(original_path, str):
            raise ProtocolError("directory listing contains a non-string path")
        file_record = _mapping(
            (yield from _call(
                "file_system", "show_file", file_path=original_path, access_token=file_token
            )),
            "file_system.show_file",
        )
        created_at = _parse_iso_datetime(file_record.get("created_at"), "file created_at")
        prefix = _pendulum_prefix(created_at, prefix_format)
        destination = source_directory if created_at.year == now.year else destination_directory
        yield from _call(
            "file_system",
            "move_file",
            source_file_path=original_path,
            destination_file_path=destination + prefix + original_path.split("/")[-1],
            access_token=file_token,
        )
        moved += 1
    yield from _call("supervisor", "complete_task", status="success")
    return {"status": "success", "files_moved": moved}


def _constraint(instruction: str) -> Generator[dict[str, Any], dict[str, Any], dict[str, Any]]:
    friend_match = re.match(r"\s*([A-Za-z]+)\s+paid", instruction)
    quoted = re.findall(r'"([^"]*)"', instruction)
    if not friend_match or len(quoted) < 2:
        yield from _call("supervisor", "complete_task", status="fail")
        return {"status": "fail_closed", "reason": "constraint instruction did not match"}
    friend_first_name = friend_match.group(1)
    payment_note, message_text = quoted[-2:]
    profile, passwords = yield from _profile_and_passwords()
    phone_number = profile.get("phone_number")
    if not isinstance(phone_number, str):
        raise ProtocolError("supervisor profile has no phone number")
    phone_token = _access_token(
        (yield from _call("phone", "login", username=phone_number, password=passwords["phone"])),
        "phone.login",
    )
    now = _current_datetime((yield from _call("phone", "get_current_date_and_time")))
    matching_contacts: list[dict[str, Any]] = []
    for page_index in range(10):
        page = _items(
            (yield from _call(
                "phone",
                "search_contacts",
                page_index=page_index,
                access_token=phone_token,
                query=friend_first_name,
            )),
            "phone.search_contacts",
        )
        matching_contacts.extend(
            row
            for item in page
            for row in [_mapping(item, "contact row")]
            if row.get("first_name") == friend_first_name
        )
    if len(matching_contacts) != 1:
        yield from _call("supervisor", "complete_task", status="fail")
        return {"status": "fail_closed", "reason": "contact lookup was ambiguous"}
    friend = matching_contacts[0]
    friend_phone = friend.get("phone_number")
    friend_email = friend.get("email")
    if not isinstance(friend_phone, str) or not isinstance(friend_email, str):
        raise ProtocolError("contact has no phone number or email")
    yesterday = (now - timedelta(days=1)).date()
    messages: list[dict[str, Any]] = []
    for page_index in range(10):
        page = _items(
            (yield from _call(
                "phone",
                "search_text_messages",
                page_index=page_index,
                access_token=phone_token,
                phone_number=friend_phone,
            )),
            "phone.search_text_messages",
        )
        messages.extend(_mapping(item, "text message row") for item in page)
    amounts: list[int] = []
    for item in messages:
        sent_at = _parse_iso_datetime(item.get("sent_at"), "message sent_at")
        message = item.get("message")
        if sent_at.date() != yesterday or not isinstance(message, str):
            continue
        match = re.search(r"\$(\d+)", message)
        if match:
            amounts.append(int(match.group(1)))
    unique_amounts = sorted(set(amounts))
    if len(unique_amounts) != 1:
        yield from _call("supervisor", "complete_task", status="fail")
        return {"status": "fail_closed", "reason": "yesterday amount lookup was ambiguous"}
    email = profile.get("email")
    if not isinstance(email, str):
        raise ProtocolError("supervisor profile has no email")
    venmo_token = _access_token(
        (yield from _call("venmo", "login", username=email, password=passwords["venmo"])),
        "venmo.login",
    )
    yield from _call(
        "venmo",
        "create_transaction",
        access_token=venmo_token,
        receiver_email=friend_email,
        amount=unique_amounts[0],
        description=payment_note,
    )
    yield from _call(
        "phone",
        "send_text_message",
        access_token=phone_token,
        phone_number=friend_phone,
        message=message_text,
    )
    yield from _call("supervisor", "complete_task", status="success")
    return {"status": "success", "amount": unique_amounts[0]}


POLICIES = {
    "workflow_export_notes_v1": _workflow,
    "gotcha_prefix_before_move_v1": _gotcha,
    "constraint_exact_reimbursement_v1": _constraint,
}


def _fail_closed(reason: str) -> Generator[dict[str, Any], dict[str, Any], dict[str, Any]]:
    yield from _call("supervisor", "complete_task", status="fail")
    return {"status": "fail_closed", "reason": reason}


def _build_policy(
    target_instruction: str, retrieval_results: list[dict[str, Any]]
) -> Generator[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not retrieval_results:
        return _fail_closed("no external memory record retrieved")
    if len(retrieval_results) != 1:
        return _fail_closed("retrieval was ambiguous")
    record = retrieval_results[0]
    metadata = record.get("metadata", {})
    policy_id = metadata.get("policy_id") if isinstance(metadata, dict) else None
    policy = POLICIES.get(policy_id)
    if policy is None:
        return _fail_closed("retrieved memory has no supported policy selector")
    return policy(target_instruction)


def main() -> None:
    try:
        initialize = _read_message()
        if set(initialize) != ALLOWED_INITIALIZE_KEYS:
            extra = sorted(set(initialize) - ALLOWED_INITIALIZE_KEYS)
            missing = sorted(ALLOWED_INITIALIZE_KEYS - set(initialize))
            raise ProtocolError(f"invalid initialize schema; extra={extra}, missing={missing}")
        if initialize.get("type") != "initialize":
            raise ProtocolError("first RPC message must be initialize")
        if initialize.get("protocol_version") != PROTOCOL_VERSION:
            raise ProtocolError("unsupported protocol version")
        target_instruction = initialize.get("target_instruction")
        retrieval_results = initialize.get("retrieval_results")
        if not isinstance(target_instruction, str) or not isinstance(retrieval_results, list):
            raise ProtocolError("invalid initialize payload types")
        _validate_no_private_keys(retrieval_results, "retrieval_results")
        if not all(isinstance(item, dict) for item in retrieval_results):
            raise ProtocolError("retrieval_results must contain only objects")

        policy = _build_policy(target_instruction, retrieval_results)
        request_number = 0
        try:
            tool_call = next(policy)
            while True:
                request_number += 1
                request_id = f"call-{request_number:04d}"
                message = {**tool_call, "request_id": request_id, "protocol_version": PROTOCOL_VERSION}
                _emit(message)
                response = _read_message()
                expected_keys = {"type", "protocol_version", "request_id", "ok", "result"}
                if set(response) != expected_keys:
                    raise ProtocolError("invalid tool_result schema")
                if response.get("type") != "tool_result":
                    raise ProtocolError("expected tool_result")
                if response.get("protocol_version") != PROTOCOL_VERSION:
                    raise ProtocolError("tool_result protocol version mismatch")
                if response.get("request_id") != request_id:
                    raise ProtocolError("tool_result request_id mismatch")
                if response.get("ok") is not True:
                    raise ProtocolError("controller rejected a policy tool call")
                tool_call = policy.send(response.get("result"))
        except StopIteration as completed:
            _emit(
                {
                    "type": "final",
                    "protocol_version": PROTOCOL_VERSION,
                    "ok": True,
                    "result": completed.value,
                    "tool_call_count": request_number,
                }
            )
    except Exception as error:
        _emit(
            {
                "type": "final",
                "protocol_version": PROTOCOL_VERSION,
                "ok": False,
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
