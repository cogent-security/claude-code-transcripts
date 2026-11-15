import json


def normalize_codex_rows(rows):
    """Adapt native Codex messages and event-only tools without duplicate calls."""
    native = [row["payload"] for row in rows if row.get("type") == "response_item"]
    calls = {
        item.get("call_id")
        for item in native
        if item.get("type") in {"function_call", "custom_tool_call"}
    }
    results = {
        item.get("call_id")
        for item in native
        if item.get("type") in {"function_call_output", "custom_tool_call_output"}
    }
    texts = {
        block.get("text")
        for item in native
        if item.get("type") == "message"
        for block in item.get("content", [])
    }
    output = []

    def emit(row, role, block):
        output.append(
            {
                "type": role,
                "timestamp": row.get("timestamp", ""),
                "message": {"role": role, "content": [block]},
            }
        )

    def tool(row, identifier, name, arguments):
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                pass
        if not isinstance(arguments, dict):
            arguments = {"input": arguments}
        emit(
            row,
            "assistant",
            {"type": "tool_use", "id": identifier, "name": name, "input": arguments},
        )

    def result(row, identifier, content, error=False):
        emit(
            row,
            "user",
            {
                "type": "tool_result",
                "tool_use_id": identifier,
                "content": content,
                "is_error": error,
            },
        )

    for row in rows:
        item = row.get("payload", {})
        kind, identifier = item.get("type"), item.get("call_id")
        if row.get("type") == "response_item":
            if kind == "message" and item.get("role") in {"user", "assistant"}:
                for block in item.get("content", []):
                    if block.get("type") in {"input_text", "output_text", "text"}:
                        emit(row, item["role"], {"type": "text", "text": block["text"]})
                    else:
                        emit(
                            row,
                            item["role"],
                            {
                                "type": "text",
                                "text": json.dumps(block, ensure_ascii=False),
                            },
                        )
            elif kind in {"function_call", "custom_tool_call"}:
                tool(
                    row,
                    identifier,
                    item["name"],
                    item.get("arguments", item.get("input", {})),
                )
            elif kind in {"function_call_output", "custom_tool_call_output"}:
                content = item.get("output", "")
                error = item.get("is_error", False) or (
                    isinstance(content, dict) and content.get("isError", False)
                )
                result(row, identifier, content, error)
            elif kind == "reasoning":
                for summary in (
                    item.get("summary", [])
                    if isinstance(item.get("summary"), list)
                    else []
                ):
                    if summary.get("text"):
                        emit(
                            row,
                            "assistant",
                            {"type": "thinking", "thinking": summary["text"]},
                        )
            elif kind != "message":
                emit(
                    row,
                    "assistant",
                    {
                        "type": "text",
                        "text": f"Codex {kind}:\n{json.dumps(item, ensure_ascii=False)}",
                    },
                )
        elif row.get("type") == "event_msg":
            # The native response items are authoritative when both streams record a call.
            if kind == "mcp_tool_call_begin" and identifier not in calls:
                invocation = item["invocation"]
                tool(
                    row,
                    identifier,
                    f"mcp__{invocation['server']}__{invocation['tool']}",
                    invocation.get("arguments", {}),
                )
            elif kind == "mcp_tool_call_end" and identifier not in results:
                value = item.get("result", {})
                result(
                    row,
                    identifier,
                    value.get("Err", value.get("Ok", value)),
                    "Err" in value or bool(value.get("Ok", {}).get("isError")),
                )
            elif kind == "exec_command_begin" and identifier not in calls:
                tool(
                    row,
                    identifier,
                    "exec_command",
                    {"command": item.get("command"), "cwd": item.get("cwd")},
                )
            elif kind == "exec_command_end" and identifier not in results:
                result(
                    row,
                    identifier,
                    item.get("aggregated_output", item.get("output", "")),
                    item.get("exit_code", 0) != 0,
                )
            elif (
                kind in {"user_message", "agent_message"}
                and item.get("message") not in texts
            ):
                emit(
                    row,
                    "user" if kind == "user_message" else "assistant",
                    {"type": "text", "text": item["message"]},
                )
            elif kind in {"error", "turn_aborted"}:
                emit(
                    row,
                    "assistant",
                    {
                        "type": "text",
                        "text": f"Codex {kind}:\n{json.dumps(item, ensure_ascii=False)}",
                    },
                )
    if not output:
        raise ValueError("Codex rollout contains no supported transcript messages")
    return output
