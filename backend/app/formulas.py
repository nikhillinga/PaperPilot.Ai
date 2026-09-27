"""
formulas.py — Formula and equation extraction for PaperPilot.

Identifies candidate pages with mathematical equations and formulas using
heuristic token detection, extracts contextual pages, and uses the LLM to
produce structured mathematical metadata without hallucinating equations.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

try:
    from app import llm_client, prompts
except ImportError:
    import llm_client, prompts

logger = logging.getLogger(__name__)

# Heuristic pattern to detect mathematical and formula tokens:
# 1. Math symbols: =, Σ, ∑, ∫, √, ≤, ≥, ±
# 2. Greek letters: α, β, γ, δ, θ, λ, μ, σ, etc.
# 3. Subscripts/indexed symbols: e.g. x_i, W_k, y(i)
FORMULA_TOKEN_RE = re.compile(
    r"[=Σ∑∫√≤≥±]"
    r"|[αβγδθλμσΔΩΠ]"
    r"|\b[a-zA-Z]_[a-zA-Z0-9]+"
    r"|\b[a-zA-Z]\([a-zA-Z0-9]+\)"
)


def _is_candidate_page(text: str) -> bool:
    """Check if a page contains at least one line with 2+ formula tokens."""
    for line in text.splitlines():
        # Match lines containing 2+ formula tokens
        tokens = FORMULA_TOKEN_RE.findall(line)
        if len(tokens) >= 2:
            return True
    return False


def extract_formulas(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Step 1 — candidate detection (no LLM call):
    For each page, check if its text contains at least one line matching
    formula-like patterns: lines containing 2+ of these characters/patterns:
    "=", "Σ", "∑", "∫", "√", "≤", "≥", "±", a Greek letter (α,β,γ,δ,θ,λ,μ,σ),
    or a pattern like a single letter followed by a subscript-looking suffix
    (e.g. "x_i", "y(i)"). Use a simple regex, don't overengineer this.

    Step 2:
    Collect only the candidate pages (plus, for context, the text of the
    page before each candidate page if it exists, since the sentence
    introducing an equation is often on the prior page).
    If zero candidate pages are found, return [] immediately (skip the LLM
    call entirely — no formulas to extract).

    Step 3:
    Call prompts.build_formula_prompt() with the candidate pages' text,
    call llm_client.call_llm(), return the parsed list.
    If the LLM call raises LLMOutputError, catch it and return [] with a
    printed warning rather than crashing the whole pipeline — formula
    extraction failing should not block the rest of the study kit.
    """
    if not pages:
        return []

    # Step 1: Detect candidate pages containing formulas
    candidate_indices: set[int] = set()
    for idx, page in enumerate(pages):
        page_text = page.get("text", "")
        if _is_candidate_page(page_text):
            candidate_indices.add(idx)

    # Step 2: Early return if no candidate pages found
    if not candidate_indices:
        return []

    # Collect candidate pages plus preceding context page if available
    included_indices: set[int] = set()
    for idx in candidate_indices:
        if idx > 0:
            included_indices.add(idx - 1)
        included_indices.add(idx)

    sorted_indices = sorted(included_indices)
    candidate_pages_text = "\n\n".join(
        pages[i].get("text", "") for i in sorted_indices
    )

    # Step 3: LLM prompt construction and execution
    system_prompt, user_prompt = prompts.build_formula_prompt(candidate_pages_text)

    try:
        raw_result = llm_client.call_llm(system_prompt, user_prompt, expect_json=True)
    except llm_client.LLMOutputError as exc:
        print(f"Warning: Formula extraction failed with LLMOutputError: {exc}")
        return []

    if isinstance(raw_result, list):
        return raw_result
    elif isinstance(raw_result, dict):
        if "formulas" in raw_result and isinstance(raw_result["formulas"], list):
            return raw_result["formulas"]
        return [raw_result]

    return []


if __name__ == "__main__":
    try:
        from app.parsing import extract_pages
    except ImportError:
        from parsing import extract_pages

    if len(sys.argv) < 2:
        print("Usage: python -m app.formulas <path/to/paper.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"Processing PDF: {pdf_path}")
    try:
        extracted_pages = extract_pages(pdf_path)
        print(f"Extracted {len(extracted_pages)} pages.")
        formulas_list = extract_formulas(extracted_pages)
        print(f"\nExtracted {len(formulas_list)} formulas:")
        print(json.dumps(formulas_list, indent=2))
    except Exception as err:
        print(f"Error during formula extraction: {err}")
        sys.exit(1)
