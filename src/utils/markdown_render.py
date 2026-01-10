"""Markdown to HTML rendering utilities."""

from __future__ import annotations

import html
import re
from typing import List

try:
    import markdown as _markdown
except Exception:  # pragma: no cover - optional dependency
    _markdown = None

_ORDERED_LIST_RE = re.compile(r"^\d+[.)]\s+")


def _simple_markdown_to_html(text: str) -> str:
    lines = text.splitlines()
    output: List[str] = []
    in_ul = False
    in_ol = False
    in_paragraph = False
    in_code = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            output.append("</ul>")
            in_ul = False
        if in_ol:
            output.append("</ol>")
            in_ol = False

    def close_paragraph() -> None:
        nonlocal in_paragraph
        if in_paragraph:
            output.append("</p>")
            in_paragraph = False

    for line in lines:
        stripped = line.rstrip("\n")
        trimmed = stripped.strip()

        if trimmed.startswith("```"):
            close_lists()
            close_paragraph()
            if in_code:
                output.append("</code></pre>")
            else:
                output.append("<pre><code>")
            in_code = not in_code
            continue

        if in_code:
            output.append(html.escape(stripped))
            continue

        if not trimmed:
            close_lists()
            close_paragraph()
            continue

        if trimmed.startswith("<") and trimmed.endswith(">"):
            close_lists()
            close_paragraph()
            output.append(trimmed)
            continue

        if trimmed.startswith("# "):
            close_lists()
            close_paragraph()
            output.append(f"<h1>{html.escape(trimmed[2:].strip())}</h1>")
            continue
        if trimmed.startswith("## "):
            close_lists()
            close_paragraph()
            output.append(f"<h2>{html.escape(trimmed[3:].strip())}</h2>")
            continue
        if trimmed.startswith("### "):
            close_lists()
            close_paragraph()
            output.append(f"<h3>{html.escape(trimmed[4:].strip())}</h3>")
            continue

        if trimmed.startswith(("- ", "* ")):
            close_paragraph()
            if not in_ul:
                close_lists()
                output.append("<ul>")
                in_ul = True
            output.append(f"<li>{html.escape(trimmed[2:].strip())}</li>")
            continue

        if _ORDERED_LIST_RE.match(trimmed):
            close_paragraph()
            if not in_ol:
                close_lists()
                output.append("<ol>")
                in_ol = True
            item = _ORDERED_LIST_RE.sub("", trimmed).strip()
            output.append(f"<li>{html.escape(item)}</li>")
            continue

        close_lists()
        if not in_paragraph:
            output.append("<p>")
            in_paragraph = True
        output.append(html.escape(trimmed))

    if in_code:
        output.append("</code></pre>")
    close_lists()
    close_paragraph()
    return "\n".join(output)


def render_markdown_to_html(text: str) -> str:
    """Render Markdown to HTML with an optional dependency."""
    if _markdown is None:
        return _simple_markdown_to_html(text)
    return _markdown.markdown(
        text,
        extensions=["extra"],
        output_format="html5",
    )
