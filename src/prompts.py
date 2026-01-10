"""Prompt loading utilities with variant support."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

PROMPTS_ROOT = Path(
    os.getenv("PROMPTS_DIR", Path(__file__).resolve().parent.parent / "prompts")
)
logger = logging.getLogger(__name__)


def _resolve_variant(explicit_variant: Optional[str]) -> str:
    variant = explicit_variant or os.getenv("PROMPT_VARIANT", "default")
    variant = variant.strip().lower()
    return variant or "default"


@lru_cache(maxsize=32)
def load_prompt(prompt_name: str, variant: Optional[str] = None) -> str:
    """Load prompt text for the given logical name and variant.

    Args:
        prompt_name: Hierarchical prompt identifier (e.g. "summarize/system").
        variant: Optional override for PROMPT_VARIANT.

    Returns:
        Prompt text as a string.
    """
    variant_key = _resolve_variant(variant)
    relative_path = Path(prompt_name)
    prompt_key = "_".join(relative_path.parts)
    candidate = PROMPTS_ROOT / variant_key / f"{variant_key}_{prompt_key}.txt"
    fallback = PROMPTS_ROOT / "default" / f"default_{prompt_key}.txt"

    path = candidate if candidate.exists() else fallback
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found for {prompt_name} (variant={variant_key})"
        )

    if path != candidate:
        logger.info(
            "Prompt variant '%s' missing for %s. Falling back to default.",
            variant_key,
            prompt_name,
        )

    return path.read_text(encoding="utf-8")


def render_prompt(template: str, **values: str) -> str:
    """Render a prompt template with safe defaults for missing data."""
    safe_values = {
        key: "" if value is None else str(value)
        for key, value in values.items()
    }
    return template.format(**safe_values)
