import json

from claude_code_transcripts import generate_html, parse_session_file


def test_native_codex_roundtrip_deduplicates_calls_and_preserves_failures(tmp_path):
    rows = [
        {"type": "session_meta", "payload": {"id": "native"}},
        {
            "type": "event_msg",
            "payload": {
                "type": "exec_command_begin",
                "call_id": "call",
                "command": ["false"],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "call_id": "call",
                "name": "exec_command",
                "arguments": '{"cmd":"false"}',
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call",
                "output": "failure evidence",
                "is_error": True,
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "exec_command_end", "call_id": "call", "exit_code": 1},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Readable result"}],
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "agent_message", "message": "Readable result"},
        },
    ]
    source = tmp_path / "rollout.jsonl"
    original = "\n".join(json.dumps(row) for row in rows)
    source.write_text(original)
    logs = parse_session_file(source)["loglines"]
    assert len(logs) == 3
    assert logs[0]["message"]["content"][0]["input"] == {"cmd": "false"}
    assert logs[1]["message"]["content"][0]["is_error"] is True
    generate_html(source, tmp_path / "html", single_page=True)
    html = (tmp_path / "html/index.html").read_text()
    assert "Readable result" in html
    assert "failure evidence" in html
    assert source.read_text() == original
