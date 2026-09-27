"""
notes.py — Markdown revision notes renderer for PaperPilot.

Pure template renderer: takes already-extracted understanding, formulas,
and findings data and formats them into a structured Markdown study sheet.
Makes no LLM calls.
"""

from __future__ import annotations


def _page_suffix(page: int | None) -> str:
    """Return '  (p.N)' when page is a valid int, or '' if None/falsy."""
    if isinstance(page, int):
        return f"  (p.{page})"
    return ""


def _field(understanding: dict, key: str) -> tuple[str, int | None]:
    """Safely extract (text, page) from an understanding field dict."""
    field = understanding.get(key) or {}
    text = field.get("text") or "Not specified in the provided text"
    page = field.get("page")
    return text, page


def generate_notes(
    title: str,
    understanding: dict,
    formulas: list[dict],
    findings: list[dict],
) -> str:
    """
    Returns a single Markdown string in this exact structure:

    # Quick Revision Notes — {title}

    ## Problem
    {understanding['problem']['text']}  (p.{understanding['problem']['page']})

    ## Motivation
    {understanding['motivation']['text']}  (p.{understanding['motivation']['page']})

    ## Method
    {understanding['solution']['text']}  (p.{understanding['solution']['page']})

    ## Dataset
    {understanding['dataset']['text']}  (p.{understanding['dataset']['page']})

    ## Methodology
    {understanding['methodology']['text']}  (p.{understanding['methodology']['page']})

    ## Key Formulas
    - **{formula['name']}**: {formula['meaning']}  (p.{formula['page']})
    [one bullet per item in formulas, skip if equation_raw is null and
    just note the name + "(formula not machine-readable, see paper)"]

    ## Key Findings
    - {finding['finding']}  (p.{finding['page']})
    [one bullet per item in findings]

    ## Metrics
    {understanding['metrics']['text']}  (p.{understanding['metrics']['page']})

    ## Key Results
    {understanding['key_results']['text']}  (p.{understanding['key_results']['page']})

    ## Limitations
    {understanding['limitations']['text']}  (p.{understanding['limitations']['page']})

    If any understanding field's page value is None, omit the "(p.N)"
    suffix for that line rather than printing "(p.None)".
    """
    lines: list[str] = []

    # ── Title ─────────────────────────────────────────────────────────
    lines.append(f"# Quick Revision Notes — {title}")
    lines.append("")

    # ── Problem ───────────────────────────────────────────────────────
    prob_text, prob_page = _field(understanding, "problem")
    lines.append("## Problem")
    lines.append(f"{prob_text}{_page_suffix(prob_page)}")
    lines.append("")

    # ── Motivation ────────────────────────────────────────────────────
    mot_text, mot_page = _field(understanding, "motivation")
    lines.append("## Motivation")
    lines.append(f"{mot_text}{_page_suffix(mot_page)}")
    lines.append("")

    # ── Method ────────────────────────────────────────────────────────
    sol_text, sol_page = _field(understanding, "solution")
    lines.append("## Method")
    lines.append(f"{sol_text}{_page_suffix(sol_page)}")
    lines.append("")

    # ── Dataset ───────────────────────────────────────────────────────
    dat_text, dat_page = _field(understanding, "dataset")
    lines.append("## Dataset")
    lines.append(f"{dat_text}{_page_suffix(dat_page)}")
    lines.append("")

    # ── Methodology ───────────────────────────────────────────────────
    meth_text, meth_page = _field(understanding, "methodology")
    lines.append("## Methodology")
    lines.append(f"{meth_text}{_page_suffix(meth_page)}")
    lines.append("")

    # ── Key Formulas ──────────────────────────────────────────────────
    lines.append("## Key Formulas")
    if formulas:
        for formula in formulas:
            name = formula.get("name", "Unnamed Formula")
            meaning = formula.get("meaning", "")
            equation_raw = formula.get("equation_raw")
            page = formula.get("page")

            if equation_raw is None:
                # Formula detected but not machine-readable
                bullet = f"- **{name}**: (formula not machine-readable, see paper)"
            else:
                bullet = f"- **{name}**: {meaning}"

            bullet += _page_suffix(page)
            lines.append(bullet)
    else:
        lines.append("_No formulas detected._")
    lines.append("")

    # ── Key Findings ──────────────────────────────────────────────────
    lines.append("## Key Findings")
    if findings:
        for finding in findings:
            finding_text = finding.get("finding", "")
            page = finding.get("page")
            lines.append(f"- {finding_text}{_page_suffix(page)}")
    else:
        lines.append("_No findings detected._")
    lines.append("")

    # ── Metrics ───────────────────────────────────────────────────────
    met_text, met_page = _field(understanding, "metrics")
    lines.append("## Metrics")
    lines.append(f"{met_text}{_page_suffix(met_page)}")
    lines.append("")

    # ── Key Results ───────────────────────────────────────────────────
    res_text, res_page = _field(understanding, "key_results")
    lines.append("## Key Results")
    lines.append(f"{res_text}{_page_suffix(res_page)}")
    lines.append("")

    # ── Limitations ───────────────────────────────────────────────────
    lim_text, lim_page = _field(understanding, "limitations")
    lines.append("## Limitations")
    lines.append(f"{lim_text}{_page_suffix(lim_page)}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    sample_understanding = {
        "problem": {"text": "Sequence-to-sequence models struggle with long-range dependencies.", "page": 1},
        "motivation": {"text": "Recurrent models are slow to train due to sequential computation.", "page": 2},
        "solution": {"text": "The Transformer architecture uses multi-head self-attention exclusively.", "page": 3},
        "dataset": {"text": "WMT 2014 English-German and English-French translation benchmarks.", "page": 5},
        "methodology": {"text": "Stacked encoder-decoder with 6 layers, 8 attention heads, d_model=512.", "page": 4},
        "metrics": {"text": "BLEU score on WMT translation tasks.", "page": 6},
        "key_results": {"text": "Achieves 28.4 BLEU on EN-DE, outperforming prior best by 2+ points.", "page": 7},
        "limitations": {"text": None},  # page None — suffix must be omitted
    }

    sample_formulas = [
        {
            "name": "Scaled Dot-Product Attention",
            "equation_raw": "softmax(QK^T / sqrt(d_k)) V",
            "meaning": "Computes weighted sum of values using query-key similarity scaled by dimension.",
            "variables": [
                {"symbol": "Q", "meaning": "Query matrix"},
                {"symbol": "K", "meaning": "Key matrix"},
                {"symbol": "d_k", "meaning": "Key dimension"},
            ],
            "page": 3,
        },
        {
            "name": "Positional Encoding",
            "equation_raw": None,  # not machine-readable
            "meaning": "Formula detected on this page but could not be extracted as text.",
            "variables": [],
            "page": 4,
        },
    ]

    sample_findings = [
        {"finding": "Achieves 28.4 BLEU on EN-DE, exceeding prior SOTA by 2 BLEU points.", "page": 7},
        {"finding": "Training takes 3.5 days on 8 P100 GPUs, 4x faster than prior best.", "page": 7},
        {"finding": "Self-attention is O(1) sequential operations vs O(n) for RNNs.", "page": 5},
    ]

    notes_md = generate_notes(
        title="Attention Is All You Need",
        understanding=sample_understanding,
        formulas=sample_formulas,
        findings=sample_findings,
    )
    print(notes_md)
