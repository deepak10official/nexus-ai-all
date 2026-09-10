"""Load prompt text and persona definitions from Markdown files on disk.

All prompt wording lives in ``.md`` files so it can be edited without touching
Python:

- ``templates/*.md`` : the shared persona + reviser prompt templates.
- ``personas/*.md``  : one file per persona, with YAML frontmatter (structured
  metadata for the UI) followed by the persona's profile text (used in the
  prompt).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import yaml

_PROMPTS_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _PROMPTS_DIR / "templates"
_PERSONAS_DIR = _PROMPTS_DIR / "personas"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_template(filename: str) -> str:
    """Return the raw text of a template markdown file (placeholders intact)."""

    return _read(_TEMPLATES_DIR / filename).strip()


def _split_frontmatter(text: str) -> Tuple[Dict, str]:
    """Split a ``--- yaml --- body`` markdown string into (metadata, body)."""

    stripped = text.lstrip()
    if stripped.startswith("---"):
        # ['', frontmatter, body] — maxsplit=2 keeps any '---' inside the body.
        parts = stripped.split("---", 2)
        if len(parts) == 3:
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2].strip()
    return {}, text.strip()


def _find_persona_file(persona_id: str) -> Path:
    """Locate ``<persona_id>.md`` anywhere under the personas directory.

    Supports both the flat layout (``personas/arjun.md``) and the categorised
    layout (``personas/students_early_career/arjun.md``).
    """

    # Fast path — direct file at the top level.
    direct = _PERSONAS_DIR / f"{persona_id}.md"
    if direct.exists():
        return direct

    # Search one level of subdirectories (category folders).
    for child in _PERSONAS_DIR.iterdir():
        if child.is_dir():
            candidate = child / f"{persona_id}.md"
            if candidate.exists():
                return candidate

    raise FileNotFoundError(
        f"No persona markdown for '{persona_id}' under {_PERSONAS_DIR}"
    )


def load_persona_markdown(persona_id: str) -> Tuple[Dict, str]:
    """Return ``(metadata, profile_body)`` for a persona markdown file."""

    return _split_frontmatter(_read(_find_persona_file(persona_id)))


def available_persona_ids() -> list[str]:
    """List persona ids that have a markdown file (sorted).

    Finds ``.md`` files at the top level *and* inside category subdirectories.
    """

    ids: set[str] = set()
    # Top-level .md files.
    for p in _PERSONAS_DIR.glob("*.md"):
        ids.add(p.stem)
    # Categorised .md files (one level deep).
    for p in _PERSONAS_DIR.glob("*/*.md"):
        ids.add(p.stem)
    return sorted(ids)
