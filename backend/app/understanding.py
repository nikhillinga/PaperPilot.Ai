"""
understanding.py — Paper understanding extraction for PaperPilot.

Extracts core conceptual and technical understanding (problem, motivation,
solution, dataset, methodology, metrics, key_results, limitations) from
the most relevant sections of a parsed paper using the configured LLM.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

try:
    from app import config, llm_client, prompts
except ImportError:
    import config, llm_client, prompts

logger = logging.getLogger(__name__)

# Expected 8 core keys from the LLM prompt
EXPECTED_KEYS = [
    "problem",
    "motivation",
    "solution",
    "dataset",
    "methodology",
    "metrics",
    "key_results",
    "limitations",
]

FALLBACK_VALUE = {
    "text": "Not specified in the provided text",
    "page": None,
}

# Target section identifiers to prioritize
TARGET_SECTION_ROOTS = {
    "introduction",
    "methodology",
    "method",
    "approach",
    "results",
    "evaluation",
    "discussion",
    "conclusion",
    "limitations",
}


def _is_relevant_section(header: str) -> bool:
    """Check if a section header matches any of the target relevant sections."""
    # Normalize header: strip numbering like " (2)", lowercase, strip punctuation
    clean = re.sub(r"\s*\(\d+\)$", "", header).strip().lower()
    clean = re.sub(r"^[0-9\.\s]+", "", clean).strip()
    return clean in TARGET_SECTION_ROOTS


def _truncate_sections_text(
    selected_sections: list[tuple[str, str]],
    max_chars: int,
) -> str:
    """Combine sections into one string, budgeting characters across sections
    so the start of each section is preserved rather than dropping entire
    sections.
    """
    if not selected_sections:
        return ""

    # Measure header formatting overhead: "=== SECTION: <name> ===\n\n"
    overhead = sum(len(f"=== {k} ===\n\n") for k, _ in selected_sections)
    available_chars = max(0, max_chars - overhead)

    current_lens = {k: len(v) for k, v in selected_sections}
    total_text_len = sum(current_lens.values())

    if total_text_len + overhead > max_chars:
        logger.warning(
            "Combined sections text length (%d chars) exceeds MAX_CHARS_PER_LLM_CALL (%d chars). "
            "Truncating sections to preserve start of each section.",
            total_text_len + overhead,
            max_chars,
        )

        # Iteratively distribute available characters so shorter sections keep
        # their full text while longer sections are trimmed equally from the end.
        active_keys = [k for k, _ in selected_sections]
        remaining_budget = available_chars
        allocated: dict[str, int] = {}

        while active_keys:
            per_section_budget = remaining_budget // len(active_keys)
            under_budget = [k for k in active_keys if current_lens[k] <= per_section_budget]

            if under_budget:
                for k in under_budget:
                    allocated[k] = current_lens[k]
                    remaining_budget -= current_lens[k]
                    active_keys.remove(k)
            else:
                for k in active_keys:
                    allocated[k] = per_section_budget
                break

        parts: list[str] = []
        for k, content in selected_sections:
            keep_len = allocated.get(k, per_section_budget)
            truncated_body = content[:keep_len].strip()
            parts.append(f"=== {k} ===\n{truncated_body}")
        combined = "\n\n".join(parts)
    else:
        parts = [f"=== {k} ===\n{v}" for k, v in selected_sections]
        combined = "\n\n".join(parts)

    return combined[:max_chars]


def generate_understanding(sections: dict[str, str]) -> dict[str, Any]:
    """
    Takes the output of sections.detect_sections().
    Builds a combined text string from the most relevant sections
    (Introduction, Methodology/Method/Approach, Results/Evaluation,
    Discussion/Conclusion, Limitations — include whichever of these keys
    are actually present in `sections`, skip missing ones, don't error).
    If total combined text exceeds config.MAX_CHARS_PER_LLM_CALL, truncate
    it to that length (keep the start of each section rather than cutting
    mid-section where possible) and log a warning.
    Calls prompts.build_understanding_prompt() with the combined text.
    Calls llm_client.call_llm() and returns the parsed dict.
    Validates the returned dict has all 8 expected top-level keys (problem,
    motivation, solution, dataset, methodology, metrics, key_results,
    limitations); if any are missing, fill them with
    {"text": "Not specified in the provided text", "page": None}
    rather than raising.
    """
    if not sections:
        logger.warning("Empty sections dictionary provided to generate_understanding.")
        return {key: dict(FALLBACK_VALUE) for key in EXPECTED_KEYS}

    # 1. Select relevant sections present in input
    selected: list[tuple[str, str]] = [
        (k, v) for k, v in sections.items() if _is_relevant_section(k) and v.strip()
    ]

    # If no recognized relevant sections were found, fall back to all available non-empty sections
    if not selected:
        selected = [(k, v) for k, v in sections.items() if v.strip()]

    # 2. Combine and truncate text within limit
    max_chars = getattr(config, "MAX_CHARS_PER_LLM_CALL", 60000)
    combined_text = _truncate_sections_text(selected, max_chars)

    # 3. Build prompts and call LLM
    system_prompt, user_prompt = prompts.build_understanding_prompt(combined_text)
    raw_result = llm_client.call_llm(system_prompt, user_prompt, expect_json=True)

    result_dict: dict[str, Any] = raw_result if isinstance(raw_result, dict) else {}

    # 4. Validate and backfill all 8 expected keys
    validated_output: dict[str, Any] = {}
    for key in EXPECTED_KEYS:
        val = result_dict.get(key)
        if isinstance(val, dict):
            text_val = val.get("text", FALLBACK_VALUE["text"])
            page_val = val.get("page", FALLBACK_VALUE["page"])
            validated_output[key] = {
                "text": str(text_val) if text_val is not None else FALLBACK_VALUE["text"],
                "page": page_val if (isinstance(page_val, int) or page_val is None) else None,
            }
        else:
            validated_output[key] = dict(FALLBACK_VALUE)

    return validated_output


if __name__ == "__main__":
    try:
        from app.parsing import extract_pages
        from app.sections import detect_sections
    except ImportError:
        from parsing import extract_pages
        from sections import detect_sections

    if len(sys.argv) < 2:
        print("Usage: python -m app.understanding <path/to/paper.pdf>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    print(f"Processing PDF: {pdf_file} ...")
    try:
        pages = extract_pages(pdf_file)
        print(f"Extracted {len(pages)} pages.")
        detected = detect_sections(pages)
        print(f"Detected sections: {list(detected.keys())}")
        understanding_data = generate_understanding(detected)
        print("\nGenerated Understanding:")
        print(json.dumps(understanding_data, indent=2))
    except Exception as exc:
        print(f"Error during understanding generation: {exc}")
        sys.exit(1)
