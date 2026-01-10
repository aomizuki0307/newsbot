"""Markdown text formatting helpers."""

from __future__ import annotations

import re
from typing import Iterable, List


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?])")
_LIST_PREFIX_RE = re.compile(r"^(?:[-*+]\s+|\d+\.|\d+\))")


def _split_sentences(text: str) -> List[str]:
    parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]
    return parts


def _is_special_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return True
    if stripped.startswith(">"):
        return True
    if stripped.startswith("|"):
        return True
    if stripped.startswith("```"):
        return True
    if stripped.startswith("!["):
        return True
    if stripped.startswith("<"):
        return True
    if stripped.startswith("f:id:"):
        return True
    if _LIST_PREFIX_RE.match(stripped):
        return True
    return False


def format_markdown_paragraphs(text: str, sentences_per_paragraph: int = 2) -> str:
    """Insert blank lines to create short Markdown paragraphs.

    Keeps headings, lists, blockquotes, tables, HTML, and fenced code blocks intact.
    """
    if sentences_per_paragraph <= 0:
        return text

    lines = text.splitlines()
    output: List[str] = []
    buffer: List[str] = []
    in_code_block = False

    def flush_buffer() -> None:
        if not buffer:
            return
        paragraph = " ".join(part.strip() for part in buffer if part.strip()).strip()
        buffer.clear()
        if not paragraph:
            return
        sentences = _split_sentences(paragraph)
        if not sentences:
            output.append(paragraph)
            return
        for index in range(0, len(sentences), sentences_per_paragraph):
            chunk = "".join(sentences[index:index + sentences_per_paragraph]).strip()
            if chunk:
                output.append(chunk)
            if index + sentences_per_paragraph < len(sentences):
                output.append("")

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_buffer()
            output.append(line)
            in_code_block = not in_code_block
            continue

        if in_code_block:
            output.append(line)
            continue

        if not stripped:
            flush_buffer()
            output.append("")
            continue

        if _is_special_line(line):
            flush_buffer()
            output.append(line)
            continue

        buffer.append(line)

    flush_buffer()
    return "\n".join(output)
