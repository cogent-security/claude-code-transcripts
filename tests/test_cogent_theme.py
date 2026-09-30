import base64
import re
from pathlib import Path

from claude_code_transcripts import generate_html, generate_html_from_session_data, cli
from click.testing import CliRunner


def test_cogent_theme_is_self_contained_and_preserves_transcript_controls(tmp_path):
    generate_html(Path(__file__).parent / "sample_session.json", tmp_path)
    for page in tmp_path.glob("*.html"):
        html = page.read_text()
        assert 'class="cogent-masthead"' in html
        assert 'aria-label="Cogent"' in html
        assert 'viewBox="0 0 1699 375"' in html
        assert "Cogent" in html
        assert "Geist Mono" in html
        assert "--cogent-accent: #d8813e" in html
        fonts = re.findall(r"data:font/woff2;base64,([A-Za-z0-9+/=]+)", html)
        assert len(fonts) == 2
        assert all(base64.b64decode(font).startswith(b"wOF2") for font in fonts)
        assert "fonts.googleapis.com" not in html
        assert "fonts.gstatic.com" not in html
        assert 'id="local-message-controls"' in html
        assert "document.createElement('details')" in html
        assert "document.createElement('summary')" in html
        assert "expand-btn" in html
        assert 'href="index.html"' in html or 'href="page-001.html"' in html


def test_single_page_contains_entire_session(tmp_path):
    result = CliRunner().invoke(
        cli,
        [
            "json",
            str(Path(__file__).parent / "sample_session.json"),
            "-o",
            str(tmp_path),
            "--single-page",
        ],
    )
    assert result.exit_code == 0, result.output
    assert [p.name for p in tmp_path.glob("*.html")] == ["index.html"]
    html = (tmp_path / "index.html").read_text()
    assert "Create a simple Python function" in html
    assert "Add a multiply function too" in html
    assert 'href="page-001.html' not in html
    assert 'class="pagination"' not in html
    assert "Show full message" in html
    assert "max-height: 24rem" in html
    assert 'class="conversation-heading"' in html
    assert 'class="conversation-log"' in html


def test_single_page_handles_empty_session(tmp_path):
    generate_html_from_session_data({"loglines": []}, tmp_path, single_page=True)
    assert "No messages in this session" in (tmp_path / "index.html").read_text()
