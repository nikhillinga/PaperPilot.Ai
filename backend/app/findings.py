"""
findings.py — Key empirical findings extraction for PaperPilot.

Extracts specific, quantitative, and comparative empirical takeaways
from the Results, Evaluation, Discussion, and Conclusion sections of a paper.
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

# Target section roots relevant to findings
FINDINGS_SECTION_ROOTS = {
    "results",
    "evaluation",
    "discussion",
    "conclusion",
}


def _is_findings_section(header: str) -> bool:
    """Check if a section header matches any of the target findings sections."""
    clean = re.sub(r"\s*\(\d+\)$", "", header).strip().lower()
    clean = re.sub(r"^[0-9\.\s]+", "", clean).strip()
    return clean in FINDINGS_SECTION_ROOTS


def extract_findings(sections: dict[str, str]) -> list[dict[str, Any]]:
    """
    Build combined text from whichever of these keys are present in
    `sections`: Results, Evaluation, Discussion, Conclusion (skip missing
    ones, don't error if none are present — fall back to "Full Text" key
    if that's all that was detected).
    Call prompts.build_findings_prompt(), call llm_client.call_llm(),
    return the parsed list.
    If the LLM call raises LLMOutputError, catch it and return []
    with a printed warning rather than crashing the pipeline.
    """
    if not sections:
        return []

    # 1. Collect candidate sections in order
    selected: list[tuple[str, str]] = [
        (k, v) for k, v in sections.items() if _is_findings_section(k) and v.strip()
    ]

    # Fallback to "Full Text" or all available sections if no target section was detected
    if not selected:
        if "Full Text" in sections and sections["Full Text"].strip():
            selected = [("Full Text", sections["Full Text"])]
        else:
            selected = [(k, v) for k, v in sections.items() if v.strip()]

    if not selected:
        return []

    parts = [f"=== {k} ===\n{v.strip()}" for k, v in selected]
    combined_text = "\n\n".join(parts)

    # Respect character budget limit
    max_chars = getattr(config, "MAX_CHARS_PER_LLM_CALL", 60000)
    if len(combined_text) > max_chars:
        logger.warning(
            "Combined findings text length (%d chars) exceeds MAX_CHARS_PER_LLM_CALL (%d chars); truncating.",
            len(combined_text),
            max_chars,
        )
        combined_text = combined_text[:max_chars]

    # 2. Build prompt and invoke LLM
    system_prompt, user_prompt = prompts.build_findings_prompt(combined_text)

    try:
        raw_result = llm_client.call_llm(system_prompt, user_prompt, expect_json=True)
    except llm_client.LLMOutputError as exc:
        print(f"Warning: Findings extraction failed with LLMOutputError: {exc}")
        return []

    # 3. Format result as a list of dicts
    if isinstance(raw_result, list):
        return raw_result
    elif isinstance(raw_result, dict):
        if "findings" in raw_result and isinstance(raw_result["findings"], list):
            return raw_result["findings"]
        return [raw_result]

    return []


if __name__ == "__main__":
    try:
        from app.parsing import extract_pages
        from app.sections import detect_sections
    except ImportError:
        from parsing import extract_pages
        from sections import detect_sections

    if len(sys.argv) < 2:
        print("Usage: python -m app.findings <path/to/paper.pdf>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    print(f"Processing PDF: {pdf_file}")
    try:
        pages = extract_pages(pdf_file)
        print(f"Extracted {len(pages)} pages.")
        detected = detect_sections(pages)
        print(f"Detected sections: {list(detected.keys())}")
        findings_data = extract_findings(detected)
        print(f"\nExtracted {len(findings_data)} findings:")
        print(json.dumps(findings_data, indent=2))
    except Exception as err:
        print(f"Error during findings extraction: {err}")
        sys.exit(1)
