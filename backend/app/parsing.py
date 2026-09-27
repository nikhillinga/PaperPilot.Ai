"""
parsing.py — PDF text extraction and metadata helpers for PaperPilot.

Uses PyMuPDF (fitz) to pull page text from uploaded research papers, with
heuristics for stripping running headers/footers and truncating at the
References / Bibliography section so downstream LLM calls only receive the
substantive body of the paper.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from typing import Any

import fitz  # PyMuPDF

try:
    from app.config import MAX_PAGES
except ImportError:
    from config import MAX_PAGES

# ── Constants ──────────────────────────────────────────────────────────
_MIN_TOTAL_CHARS = 200
_HEADER_FOOTER_THRESHOLD = 3          # line must repeat on ≥ N pages
_REF_HEADING_RE = re.compile(
    r"^\s*(?:(?:\d+|[ivxlcdm]+)\.?\s*)?(references|bibliography)\s*:?\s*$",
    re.IGNORECASE,
)


# ── Helpers ────────────────────────────────────────────────────────────

def _normalize(line: str) -> str:
    """Strip and lowercase a line for comparison purposes."""
    return line.strip().lower()


def _detect_repeated_lines(
    raw_pages: list[str],
) -> set[str]:
    """Return the set of *normalized* lines that appear as the first or last
    line on >= ``_HEADER_FOOTER_THRESHOLD`` distinct pages, which strongly
    suggests they are running headers or footers.
    """
    first_lines: Counter[str] = Counter()
    last_lines: Counter[str] = Counter()

    for text in raw_pages:
        lines = text.splitlines()
        if not lines:
            continue
        first = _normalize(lines[0])
        last = _normalize(lines[-1])
        if first:
            first_lines[first] += 1
        if last:
            last_lines[last] += 1

    repeated: set[str] = set()
    for line, count in first_lines.items():
        if count >= _HEADER_FOOTER_THRESHOLD:
            repeated.add(line)
    for line, count in last_lines.items():
        if count >= _HEADER_FOOTER_THRESHOLD:
            repeated.add(line)
    return repeated


def _strip_headers_footers(text: str, repeated: set[str]) -> str:
    """Remove leading/trailing lines from *text* that match any entry in
    *repeated* (compared after normalization).
    """
    if not repeated:
        return text

    lines = text.splitlines()

    # Strip from the top
    while lines and _normalize(lines[0]) in repeated:
        lines.pop(0)

    # Strip from the bottom
    while lines and _normalize(lines[-1]) in repeated:
        lines.pop()

    return "\n".join(lines)


def _find_references_start(text: str) -> int | None:
    """Return the line index where a standalone References/
    Bibliography heading starts, or None if not found. Scans the
    WHOLE page, not just the top N lines.
    """
    for idx, line in enumerate(text.splitlines()):
        if _REF_HEADING_RE.match(line):
            return idx
    return None


# ── Public API ─────────────────────────────────────────────────────────

def extract_pages(pdf_path: str) -> list[dict[str, Any]]:
    """Extract readable text from a PDF, page-by-page.

    Returns a list of dicts::

        [
            {"page_number": 1, "text": "[PAGE 1]\\nFirst page body …"},
            {"page_number": 2, "text": "[PAGE 2]\\nSecond page body …"},
            …
        ]

    Heuristics applied:
    * Text extracted with sort=True to preserve column reading order.
    * Running headers/footers (lines repeated on ≥ 3 pages) are stripped.
    * Extraction stops at the References/Bibliography section, keeping any
      pre-references content if it starts mid-page.
    * Each page's text is prefixed with a ``[PAGE n]`` marker for later
      LLM citation.

    Raises:
        ValueError: If the PDF cannot be opened, has zero pages, or yields
            fewer than 200 total characters (likely a scanned/image PDF).
    """
    # ── Open the document ──────────────────────────────────────────────
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise ValueError("SCANNED_OR_UNREADABLE_PDF") from exc

    if doc.page_count == 0:
        doc.close()
        raise ValueError(
            "PDF has zero pages — nothing to extract."
        )

    # ── Raw extraction (up to MAX_PAGES) ───────────────────────────────
    page_limit = min(doc.page_count, MAX_PAGES)
    raw_texts: list[str] = []
    for idx in range(page_limit):
        page = doc[idx]
        raw_texts.append(page.get_text("text", sort=True))

    doc.close()

    # ── Check minimum content ──────────────────────────────────────────
    total_chars = sum(len(t) for t in raw_texts)
    if total_chars < _MIN_TOTAL_CHARS:
        raise ValueError("SCANNED_OR_UNREADABLE_PDF")

    # ── Detect and strip running headers/footers ───────────────────────
    repeated = _detect_repeated_lines(raw_texts)
    cleaned_texts = [_strip_headers_footers(t, repeated) for t in raw_texts]

    # ── Truncate at References / Bibliography ──────────────────────────
    truncated: list[dict[str, Any]] = []
    for idx, text in enumerate(cleaned_texts):
        page_number = idx + 1  # 1-indexed
        ref_start_line = _find_references_start(text)

        if ref_start_line is not None:
            # References starts on this page. Keep any substantive text before it.
            lines_before = text.splitlines()[:ref_start_line]
            content_before = "\n".join(lines_before).strip()
            if content_before:
                prefixed = f"[PAGE {page_number}]\n{content_before}"
                truncated.append({"page_number": page_number, "text": prefixed})
            # Stop extraction — do not include references text or subsequent pages
            break

        prefixed = f"[PAGE {page_number}]\n{text}"
        truncated.append({"page_number": page_number, "text": prefixed})

    # Edge case: if every page was references (unlikely but defensive)
    if not truncated:
        raise ValueError(
            "No substantive content found — the entire PDF appears to be "
            "a reference list."
        )

    return truncated


def extract_metadata(pdf_path: str) -> dict[str, str]:
    """Return best-effort ``{"title": …, "authors": …}`` from the PDF.

    Strategy:
    1. Try the document-level metadata fields (``doc.metadata``).
    2. Check if title is suspect (empty, filename-like, shorter than 15 chars,
       or ending in trailing punctuation suggesting a fragment). If suspect,
       fall back to the largest-font-size text span on page 1.
    3. Check if authors is suspect (empty, or a single lowercase word without spaces).
       If suspect, return ``"Unknown"``.

    This function never raises — it always returns *something*.
    """
    title = ""
    authors = ""

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return {"title": "", "authors": "Unknown"}

    if doc.page_count == 0:
        doc.close()
        return {"title": "", "authors": "Unknown"}

    # ── Try embedded metadata ──────────────────────────────────────────
    meta = doc.metadata or {}
    title = (meta.get("title") or "").strip()
    authors = (meta.get("author") or "").strip()

    # ── Title sanity check ─────────────────────────────────────────────
    def _is_suspect_title(t: str) -> bool:
        t_clean = t.strip()
        if len(t_clean) < 15:
            return True
        t_lower = t_clean.lower()
        if re.search(r"\.\w{2,4}$", t_lower):
            return True
        # Ending in trailing punctuation suggesting a cut-off fragment
        if t_clean.endswith((":", "-", "–", "—", ";", ",")):
            return True
        return False

    if not title or _is_suspect_title(title):
        # Fallback: find the largest text span on page 1
        title = _title_from_largest_span(doc[0])

    doc.close()

    # ── Author sanity check ────────────────────────────────────────────
    # A single lowercase word with no spaces is suspect (e.g. "cairo", tool artifact)
    if not authors or (" " not in authors and authors.islower()):
        authors = "Unknown"

    return {"title": title, "authors": authors}


def _title_from_largest_span(page: fitz.Page) -> str:
    """Heuristic: collect contiguous top-of-page text spans within tolerance of
    the maximum font size found on the first page to reconstruct multi-line titles.
    """
    try:
        blocks = page.get_text("dict").get("blocks", [])
    except Exception:
        return ""

    candidates = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_y = line.get("bbox", [0, 0, 0, 0])[1]
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    span_bbox = span.get("bbox") or [0, 0, 0, 0]
                    candidates.append({
                        "y": line_y,
                        "x": span_bbox[0],
                        "size": span.get("size", 0),
                        "text": text,
                    })

    if not candidates:
        return ""

    max_size = max(c["size"] for c in candidates)
    tolerance = 0.5
    max_gap = max(max_size * 1.8, 20.0)

    # Sort by vertical position (top to bottom), then horizontal position (left to right)
    candidates.sort(key=lambda c: (c["y"], c["x"]))

    title_parts: list[str] = []
    started = False
    last_y: float | None = None

    for c in candidates:
        is_title_size = c["size"] >= max_size - tolerance
        if is_title_size:
            # If we've started, ensure vertical gap isn't a new paragraph/section
            if started and last_y is not None and (c["y"] - last_y) > max_gap:
                break
            title_parts.append(c["text"])
            started = True
            last_y = c["y"]
        elif started:
            # We've started collecting the title and hit a smaller-font line below it
            if last_y is not None and c["y"] > last_y:
                break

    return " ".join(title_parts).strip()


# ── CLI entry-point ────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.parsing <path/to/paper.pdf>")
        sys.exit(1)

    pdf = sys.argv[1]

    print("=" * 60)
    print("METADATA")
    print("=" * 60)
    meta = extract_metadata(pdf)
    print(f"  Title:   {meta['title']}")
    print(f"  Authors: {meta['authors']}")

    print()
    print("=" * 60)
    print("PAGES")
    print("=" * 60)
    try:
        pages = extract_pages(pdf)
        for p in pages:
            preview = p["text"][:200]
            if len(p["text"]) > 200:
                preview += " …"
            print(f"\n--- Page {p['page_number']} ---")
            print(preview)
        print(f"\nTotal pages extracted: {len(pages)}")
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
