"""INV-1 (__init__.py, cogent.css): tables scroll without crushed headers.
INV-2 (__init__.py, tool_activity.html): group only uninterrupted tool activity,
preserving all records, links, errors and visible narrative boundaries.
INV-3 (__init__.py, cogent.css): reasoning has one unambiguous label.
INV-4 (message_controls.html): permalinks reveal collapsed ancestor groups.
"""

import json

from claude_code_transcripts import (
    generate_single_page,
    make_msg_id,
    render_markdown_text,
    render_message,
)


def entry(index, role, *blocks):
    return {
        "type": role,
        "timestamp": f"2026-09-30T10:00:{index:02d}Z",
        "message": {"content": list(blocks)},
    }


def tool(index, name="Bash"):
    return entry(
        index,
        "assistant",
        {
            "type": "tool_use",
            "id": f"tool-{index}",
            "name": name,
            "input": {"command": "echo example"},
        },
    )


def text(index, role="assistant"):
    return entry(index, role, {"type": "text", "text": f"Visible narrative {index}"})


def test_wide_table_has_keyboard_accessible_scroller(tmp_path):
    markup = render_markdown_text(
        "| Rule | Customer rationale | Updated |\n|---|---|---|\n| example_rule | Example rationale | 2026-09-30 |"
    )
    assert (
        '<div class="table-scroll" role="region" aria-label="Scrollable table" tabindex="0">'
        in markup
    )
    assert "<th>Customer rationale</th>" in markup
    assert "example_rule" in markup
    assert markup.endswith("</table></div>")
    generate_single_page([], tmp_path)
    page = (tmp_path / "index.html").read_text()
    assert ".table-scroll { overflow-x: auto;" in page
    assert "white-space: nowrap; overflow-wrap: normal;" in page


def test_raw_table_attributes_do_not_leave_unbalanced_wrappers():
    markup = render_markdown_text(
        '<table class="custom"><tr><td>Example</td></tr></table>'
    )
    assert markup.count("<div") == markup.count("</div>")


def test_activity_groups_keep_boundaries_errors_and_every_record(tmp_path):
    records = [
        text(0, "user"),
        entry(
            1, "assistant", {"type": "thinking", "thinking": "Consider the evidence."}
        ),
        tool(2),
        entry(
            3,
            "user",
            {
                "type": "tool_result",
                "tool_use_id": "tool-2",
                "content": "Example failure",
                "is_error": True,
            },
        ),
        tool(4, "Read"),
        text(5),
        tool(6),
        text(7, "user"),
        tool(8),
    ]
    generate_single_page(records, tmp_path)
    page = (tmp_path / "index.html").read_text()
    assert page.count('<details class="tool-activity">') == 3
    group = page.split('<details class="tool-activity">')[1].split("</details>")[0]
    assert "2 tool calls" in group
    assert "Bash, Read" in group
    assert "1 error" in group
    assert "Consider the evidence." in group
    assert "Example failure" in group
    assert "Visible narrative" not in group
    for record in records:
        assert page.count(f'id="{make_msg_id(record["timestamp"])}"') == 1
    assert "<span>9</span>" in page
    assert page.index("Visible narrative 5") < page.index(
        'id="msg-2026-09-30T10-00-06Z"'
    )


def test_mixed_text_and_tool_message_is_never_hidden_in_group(tmp_path):
    mixed = entry(
        2,
        "assistant",
        {"type": "text", "text": "Keep this explanation visible"},
        tool(2)["message"]["content"][0],
    )
    generate_single_page([tool(1), mixed, tool(3)], tmp_path)
    page = (tmp_path / "index.html").read_text()
    assert page.count('<details class="tool-activity">') == 2
    first_end = page.index("</details>", page.index('<details class="tool-activity">'))
    assert first_end < page.index("Keep this explanation visible")


def test_reasoning_only_and_orphan_result_do_not_invent_tool_calls(tmp_path):
    reasoning = entry(
        1, "assistant", {"type": "thinking", "thinking": "A short thought."}
    )
    result = entry(2, "user", {"type": "tool_result", "content": "An unmatched result"})
    generate_single_page([reasoning, result], tmp_path)
    page = (tmp_path / "index.html").read_text()
    assert '<details class="tool-activity">' not in page
    rendered = render_message(
        "assistant", json.dumps(reasoning["message"]), reasoning["timestamp"]
    )
    assert 'class="message assistant reasoning"' in rendered
    assert '<span class="role-label">Reasoning</span>' in rendered
    assert ".reasoning .thinking-label { display: none; }" in page
    assert "An unmatched result" in page


def test_message_permalink_opens_all_details_ancestors(tmp_path):
    generate_single_page([tool(1)], tmp_path)
    page = (tmp_path / "index.html").read_text()
    assert "ancestor = ancestor.parentElement" in page
    assert "ancestor.matches('details')" in page
    assert "ancestor.open = true" in page
    assert "label.dataset.sequence = String(index + 1)" in page
    assert "content: attr(data-sequence)" in page
