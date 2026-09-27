"""
sections.py — Section detection for parsed PDF papers in PaperPilot.

Identifies major academic sections (e.g. Introduction, Methodology, Results)
from the extracted pages and segments the document text into a dictionary of
sections, preserving [PAGE n] citation markers.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from typing import Any

try:
    from app.config import KNOWN_SECTION_HEADERS
except ImportError:
    from config import KNOWN_SECTION_HEADERS


def _normalize_line(line: str) -> str:
    """Normalize a candidate header line by stripping whitespace, lowercasing,
    and removing trailing colons as well as leading/trailing section numbering
    (e.g., '3.', '3.1', 'Section 4:', 'IV.').
    """
    norm = line.strip().lower().rstrip(":").strip()
    pattern = (
        r"^(?:section\s+(?:\d+|[ivxlcdm]+)|(?:\d+(?:\.\d+)*|[ivxlcdm]+[\.\)]))\s*[:\.\-]?\s*"
    )
    cleaned = re.sub(pattern, "", norm).strip()
    cleaned = re.sub(r"\s*[:\.\-]?\s*(?:\d+(?:\.\d+)*\.?)\s*$", "", cleaned).strip().rstrip(":").rstrip(".")
    return cleaned


def _match_header_candidate(line: str) -> str | None:
    """Check if a line qualifies as a section header candidate.

    Criteria:
    - Under 6 words.
    - Does not end with a comma (simple heuristic to avoid mid-sentence lines).
    - Normalized form fuzzy-matches one of KNOWN_SECTION_HEADERS:
      1. Exact match (or plural) against a known header.
      2. Known header as title prefix (e.g., '5. Results and Discussion',
         'Limitations & Future Work').

    Returns:
        The matched known header string (lowercase), or None if no match.
    """
    words = line.strip().split()
    if not (1 <= len(words) < 6):
        return None

    # Keep mid-sentence heuristic simple: line must not end in a comma
    if line.strip().endswith(","):
        return None

    cleaned = _normalize_line(line)

    # 1. Exact match check against known headers (or plural form)
    for header in KNOWN_SECTION_HEADERS:
        if cleaned == header or cleaned == header + "s":
            return header

    # 2. Compound header match: e.g., 'Results and Discussion', 'Methodology & Evaluation'
    for header in sorted(KNOWN_SECTION_HEADERS, key=len, reverse=True):
        if re.match(r"^" + re.escape(header) + r"s?\s+(?:and|&|\/)\b", cleaned):
            return header

    return None


def detect_sections(pages: list[dict[str, Any]]) -> dict[str, str]:
    """
    Returns {"Introduction": "...", "Methodology": "...", ...}
    Each value is the concatenated text (including [PAGE n] markers)
    between that header and the next detected header.
    """
    if not pages:
        return {"Full Text": ""}

    # 1. Concatenate all pages' text into one string, preserving [PAGE n] markers
    full_text = "\n".join(p.get("text", "") for p in pages)
    lines = full_text.splitlines()

    # 2. Identify candidate header lines and their positions
    detected_headers: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        matched = _match_header_candidate(line)
        if matched:
            detected_headers.append((idx, matched))

    # 3. If no headers detected, fall back to "Full Text"
    if not detected_headers:
        return {"Full Text": full_text}

    # 4. Slice text between successive headers
    sections: dict[str, str] = {}
    header_counts: Counter[str] = Counter()

    for i, (line_idx, matched_header) in enumerate(detected_headers):
        # Title-case matched header for output dict key
        title_key = matched_header.title()

        # Handle duplicate header names with " (2)", " (3)", etc. suffix
        header_counts[title_key] += 1
        count = header_counts[title_key]
        dict_key = title_key if count == 1 else f"{title_key} ({count})"

        start_line = line_idx + 1
        end_line = (
            detected_headers[i + 1][0]
            if i + 1 < len(detected_headers)
            else len(lines)
        )

        section_body = "\n".join(lines[start_line:end_line]).strip()
        sections[dict_key] = section_body

    return sections


if __name__ == "__main__":
    try:
        from app.parsing import extract_pages
    except ImportError:
        from parsing import extract_pages

    if len(sys.argv) < 2:
        print("Usage: python -m app.sections <path/to/paper.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    try:
        pages = extract_pages(pdf_path)
    except Exception as exc:
        print(f"Error extracting pages: {exc}")
        sys.exit(1)

    sections = detect_sections(pages)
    print("=" * 60)
    print("DETECTED SECTIONS")
    print("=" * 60)
    for name, text in sections.items():
        print(f"  {name}: {len(text)} characters")
