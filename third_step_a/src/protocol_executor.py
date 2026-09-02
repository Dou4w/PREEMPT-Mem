from __future__ import annotations

import json
import re
from textwrap import dedent
from typing import Any


FAIL_CLOSED_CODE = dedent(
    """
    # Frozen fail-closed fallback: no state-changing task action.
    apis.supervisor.complete_task(status="fail")
    """
).strip()


def _workflow_code(instruction: str) -> str:
    match = re.search(r'to\s+"(~/[^\"]+/)"\s+directory', instruction, flags=re.IGNORECASE)
    if not match:
        return FAIL_CLOSED_CODE
    backup_directory = match.group(1)
    return dedent(
        f"""
        supervisor_profile = apis.supervisor.show_profile()
        supervisor_passwords = {{
            entry["account_name"]: entry["password"]
            for entry in apis.supervisor.show_account_passwords()
        }}
        note_token = apis.simple_note.login(
            username=supervisor_profile["email"],
            password=supervisor_passwords["simple_note"],
        )["access_token"]
        file_token = apis.file_system.login(
            username=supervisor_profile["email"],
            password=supervisor_passwords["file_system"],
        )["access_token"]
        notes = [
            item
            for page_index in range(0, 10)
            for item in apis.simple_note.search_notes(
                page_index=page_index, access_token=note_token
            )
        ]
        for note in notes:
            full_note = apis.simple_note.show_note(
                note_id=note["note_id"], access_token=note_token
            )
            file_name = note["title"].replace(" ", "_") + ".md"
            apis.file_system.create_file(
                file_path={backup_directory!r} + file_name,
                content=full_note["content"],
                access_token=file_token,
            )
        apis.supervisor.complete_task(status="success")
        """
    ).strip()


def _gotcha_code(instruction: str) -> str:
    prefix_match = re.search(r'prefix\s+"([^"]+)"', instruction, flags=re.IGNORECASE)
    directory_matches = re.findall(r'(~\/[A-Za-z0-9_.\/-]+\/)', instruction)
    if not prefix_match or len(directory_matches) < 2:
        return FAIL_CLOSED_CODE
    prefix_format = prefix_match.group(1)
    source_directory, destination_directory = directory_matches[:2]
    return dedent(
        f"""
        from appworld.common.datetime import VanillaDateTime as DateTime
        from appworld.common.datetime import pendulum

        supervisor_profile = apis.supervisor.show_profile()
        supervisor_passwords = {{
            entry["account_name"]: entry["password"]
            for entry in apis.supervisor.show_account_passwords()
        }}
        file_token = apis.file_system.login(
            username=supervisor_profile["email"],
            password=supervisor_passwords["file_system"],
        )["access_token"]
        original_paths = list(
            apis.file_system.show_directory(
                directory_path={source_directory!r}, access_token=file_token
            )
        )
        for original_path in original_paths:
            file_record = apis.file_system.show_file(
                file_path=original_path, access_token=file_token
            )
            created_at = pendulum.parse(file_record["created_at"])
            prefix = created_at.format({prefix_format!r})
            new_name = prefix + file_record["path"].split("/")[-1]
            destination = (
                {source_directory!r}
                if created_at.year == DateTime.now().year
                else {destination_directory!r}
            )
            apis.file_system.move_file(
                source_file_path=original_path,
                destination_file_path=destination + new_name,
                access_token=file_token,
            )
        apis.supervisor.complete_task(status="success")
        """
    ).strip()


def _constraint_code(instruction: str) -> str:
    friend_match = re.match(r"\s*([A-Za-z]+)\s+paid", instruction)
    quoted = re.findall(r'"([^"]*)"', instruction)
    if not friend_match or len(quoted) < 2:
        return FAIL_CLOSED_CODE
    friend_first_name = friend_match.group(1)
    payment_note, message_text = quoted[-2:]
    return dedent(
        f"""
        import re
        from appworld.common.datetime import VanillaDateTime as DateTime
        from appworld.common.datetime import pendulum

        supervisor_profile = apis.supervisor.show_profile()
        supervisor_passwords = {{
            entry["account_name"]: entry["password"]
            for entry in apis.supervisor.show_account_passwords()
        }}
        phone_token = apis.phone.login(
            username=supervisor_profile["phone_number"],
            password=supervisor_passwords["phone"],
        )["access_token"]
        matching_contacts = [
            item
            for page_index in range(0, 10)
            for item in apis.phone.search_contacts(
                page_index=page_index,
                access_token=phone_token,
                query={friend_first_name!r},
            )
            if item["first_name"] == {friend_first_name!r}
        ]
        if len(matching_contacts) != 1:
            apis.supervisor.complete_task(status="fail")
        else:
            friend = matching_contacts[0]
            yesterday_messages = [
                item
                for page_index in range(0, 10)
                for item in apis.phone.search_text_messages(
                    page_index=page_index,
                    access_token=phone_token,
                    phone_number=friend["phone_number"],
                )
                if pendulum.parse(item["sent_at"])
                > DateTime.now().subtract(days=1).start_of("day")
                and pendulum.parse(item["sent_at"])
                < DateTime.now().subtract(days=1).end_of("day")
            ]
            amounts = [
                int(match.group(1))
                for item in yesterday_messages
                for match in [re.search(r"\\$(\\d+)", item["message"])]
                if match
            ]
            unique_amounts = sorted(set(amounts))
            if len(unique_amounts) != 1:
                apis.supervisor.complete_task(status="fail")
            else:
                venmo_token = apis.venmo.login(
                    username=supervisor_profile["email"],
                    password=supervisor_passwords["venmo"],
                )["access_token"]
                apis.venmo.create_transaction(
                    access_token=venmo_token,
                    receiver_email=friend["email"],
                    amount=unique_amounts[0],
                    description={payment_note!r},
                )
                apis.phone.send_text_message(
                    access_token=phone_token,
                    phone_number=friend["phone_number"],
                    message={message_text!r},
                )
                apis.supervisor.complete_task(status="success")
        """
    ).strip()


POLICY_COMPILERS = {
    "workflow_export_notes_v1": _workflow_code,
    "gotcha_prefix_before_move_v1": _gotcha_code,
    "constraint_exact_reimbursement_v1": _constraint_code,
}


def compile_agent_code(
    target_instruction: str, retrieved_records: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    if not retrieved_records:
        return FAIL_CLOSED_CODE, {
            "decision": "fail_closed",
            "reason": "no external memory record retrieved",
            "policy_id": None,
        }
    if len(retrieved_records) != 1:
        return FAIL_CLOSED_CODE, {
            "decision": "fail_closed",
            "reason": "retrieval was ambiguous",
            "policy_id": None,
        }
    record = retrieved_records[0]
    policy_id = record.get("metadata", {}).get("policy_id")
    compiler = POLICY_COMPILERS.get(policy_id)
    if compiler is None:
        return FAIL_CLOSED_CODE, {
            "decision": "fail_closed",
            "reason": "retrieved memory has no supported policy selector",
            "policy_id": policy_id,
        }
    code = compiler(target_instruction)
    return code, {
        "decision": "execute_retrieved_policy" if code != FAIL_CLOSED_CODE else "fail_closed",
        "reason": "one supported external policy record retrieved",
        "policy_id": policy_id,
    }


def compose_prompt(
    template: str,
    target_instruction: str,
    retrieval_query: str,
    retrieved_records: list[dict[str, Any]],
) -> str:
    return template.format(
        target_instruction=target_instruction,
        retrieval_query=retrieval_query,
        retrieved_memory_or_empty=json.dumps(
            retrieved_records, ensure_ascii=False, sort_keys=True, indent=2
        ),
    )
