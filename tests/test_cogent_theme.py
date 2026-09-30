import base64
import re
from pathlib import Path

from claude_code_transcripts import generate_html


def test_cogent_theme_is_self_contained_and_preserves_transcript_controls(tmp_path):
    generate_html(Path(__file__).parent / "sample_session.json", tmp_path)
    for page in tmp_path.glob("*.html"):
        html = page.read_text()
        assert 'class="cogent-masthead"' in html
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
