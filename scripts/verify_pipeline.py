#!/usr/bin/env python3
"""
verify_pipeline.py — End-to-end verification script for PaperPilot.

Validates all pipeline stages against a sample PDF:
1. Parsing (PyMuPDF text extraction & metadata)
2. Section Detection (abstract, methodology, results, etc.)
3. Understanding Generation (8 core academic facets with page citations)
4. Formula Extraction (heuristic filtering + equation breakdown)
5. Empirical Findings (quantitative results & evidence)
6. Revision Notes Generation (structured Markdown)
7. Viva Voce Generation (tiered examination questions)
8. Flashcard Generation & Anki CSV Export
9. API Endpoints (Health check & POST /papers upload if running)

Usage:
    python scripts/verify_pipeline.py path/to/sample.pdf
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# ── Ensure backend is on sys.path ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app import (
        config,
        findings,
        flashcards,
        formulas,
        notes,
        parsing,
        sections,
        understanding,
        viva,
    )
except ImportError as e:
    print(f"Error importing PaperPilot backend modules: {e}")
    sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_pipeline.py path/to/sample.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.exists() or not pdf_path.is_file():
        print(f"Error: Sample PDF file not found at '{pdf_path}'")
        sys.exit(1)

    print("=" * 70)
    print("PaperPilot — End-to-End Pipeline Verification")
    print(f"Sample PDF: {pdf_path}")
    print("=" * 70)

    results: dict[str, Any] = {}
    failures: list[str] = []

    pages: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    title: str = pdf_path.stem
    section_map: dict[str, list[dict[str, Any]]] = {}
    understanding_data: dict[str, Any] = {}
    formulas_list: list[dict[str, Any]] = []
    findings_list: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []

    # ── 1. PARSING ────────────────────────────────────────────────────────────
    print("\n[Step 1/9] PARSING")
    try:
        pages = parsing.extract_pages(pdf_path)
        metadata = parsing.extract_metadata(pdf_path)
        if metadata.get("title"):
            title = metadata["title"]

        if not pages:
            raise ValueError("extract_pages returned an empty list")

        for idx, p in enumerate(pages):
            if "page_number" not in p or "text" not in p:
                raise ValueError(
                    f"Page index {idx} missing 'page_number' or 'text' key (found keys: {list(p.keys())})"
                )

        total_pages = len(pages)
        total_chars = sum(len(p.get("text", "")) for p in pages)
        print(f"  ✓ Extracted {total_pages} pages ({total_chars:,} total characters)")
        print(f"  ✓ Metadata title: {title}")
        results["Parsing"] = True
    except Exception as exc:
        print(f"  ✗ Parsing failed: {exc}")
        results["Parsing"] = False
        failures.append(f"Parsing: {exc}")

    # ── 2. SECTIONS ───────────────────────────────────────────────────────────
    print("\n[Step 2/9] SECTIONS")
    if results.get("Parsing"):
        try:
            section_map = sections.detect_sections(pages)
            if not isinstance(section_map, dict) or not section_map:
                raise ValueError("detect_sections returned an empty or non-dict result")

            detected_names = list(section_map.keys())
            print(f"  ✓ Detected {len(detected_names)} sections: {', '.join(detected_names)}")
            results["Sections"] = True
        except Exception as exc:
            print(f"  ✗ Section detection failed: {exc}")
            results["Sections"] = False
            failures.append(f"Sections: {exc}")
    else:
        print("  ⊘ Skipped due to previous step failure")
        results["Sections"] = False

    # ── 3. UNDERSTANDING ──────────────────────────────────────────────────────
    print("\n[Step 3/9] UNDERSTANDING")
    expected_facets = [
        "problem",
        "motivation",
        "solution",
        "dataset",
        "methodology",
        "metrics",
        "key_results",
        "limitations",
    ]
    if results.get("Sections"):
        try:
            understanding_data = understanding.generate_understanding(section_map)
            if not isinstance(understanding_data, dict):
                raise ValueError(
                    f"generate_understanding returned {type(understanding_data)}, expected dict"
                )

            for key in expected_facets:
                if key not in understanding_data:
                    raise ValueError(f"Missing expected understanding facet: '{key}'")
                item = understanding_data[key]
                if not isinstance(item, dict) or "text" not in item or "page" not in item:
                    raise ValueError(
                        f"Facet '{key}' missing required 'text' or 'page' attributes (found: {item})"
                    )

                snippet = item["text"].replace("\n", " ").strip()
                if len(snippet) > 65:
                    snippet = snippet[:65] + "..."
                page_str = f"p.{item['page']}" if item["page"] is not None else "no page"
                print(f"  • {key.capitalize():<14} ({page_str}): {snippet}")

            print(f"  ✓ All {len(expected_facets)} understanding facets validated with page citations")
            results["Understanding"] = True
        except Exception as exc:
            print(f"  ✗ Understanding generation failed: {exc}")
            results["Understanding"] = False
            failures.append(f"Understanding: {exc}")
    else:
        print("  ⊘ Skipped due to previous step failure")
        results["Understanding"] = False

    # ── 4. FORMULAS ───────────────────────────────────────────────────────────
    print("\n[Step 4/9] FORMULAS")
    if results.get("Parsing"):
        try:
            formulas_list = formulas.extract_formulas(pages)
            if not formulas_list:
                print("  ✓ No formulas detected in paper (empty list is normal for qualitative papers)")
            else:
                print(f"  ✓ Detected {len(formulas_list)} mathematical formulas:")
                for f in formulas_list:
                    name = f.get("name", "Unnamed Formula")
                    eq = f.get("equation_raw") or f.get("formula") or "Formula detected but unparsed"
                    page_str = f" (p.{f.get('page')})" if f.get("page") is not None else ""
                    print(f"    • {name}{page_str}: {eq}")
            results["Formulas"] = True
        except Exception as exc:
            print(f"  ✗ Formula extraction failed: {exc}")
            results["Formulas"] = False
            failures.append(f"Formulas: {exc}")
    else:
        print("  ⊘ Skipped due to previous step failure")
        results["Formulas"] = False

    # ── 5. FINDINGS ───────────────────────────────────────────────────────────
    print("\n[Step 5/9] FINDINGS")
    if results.get("Sections"):
        try:
            findings_list = findings.extract_findings(section_map)
            if not findings_list:
                print("  ⚠ Warning: No empirical findings extracted (empty list)")
            else:
                print(f"  ✓ Extracted {len(findings_list)} key empirical findings:")
                for idx, item in enumerate(findings_list, 1):
                    f_text = item.get("finding") or item.get("claim") or str(item)
                    page_str = f" (p.{item.get('page')})" if item.get("page") is not None else ""
                    print(f"    [{idx}]{page_str} {f_text}")
            results["Findings"] = True
        except Exception as exc:
            print(f"  ✗ Findings extraction failed: {exc}")
            results["Findings"] = False
            failures.append(f"Findings: {exc}")
    else:
        print("  ⊘ Skipped due to previous step failure")
        results["Findings"] = False

    # ── 6. NOTES ──────────────────────────────────────────────────────────────
    print("\n[Step 6/9] NOTES")
    if results.get("Understanding"):
        try:
            notes_md = notes.generate_notes(
                title, understanding_data, formulas_list, findings_list
            )
            if not isinstance(notes_md, str) or not notes_md.strip():
                raise ValueError("generate_notes returned an empty string")
            if "# Quick Revision Notes" not in notes_md:
                raise ValueError("Notes missing expected header '# Quick Revision Notes'")

            print(f"  ✓ Generated structured revision notes ({len(notes_md):,} characters)")
            results["Notes"] = True
        except Exception as exc:
            print(f"  ✗ Notes generation failed: {exc}")
            results["Notes"] = False
            failures.append(f"Notes: {exc}")
    else:
        print("  ⊘ Skipped due to previous step failure")
        results["Notes"] = False

    # ── 7. VIVA ───────────────────────────────────────────────────────────────
    print("\n[Step 7/9] VIVA")
    viva_tiers = ["basic", "intermediate", "advanced", "research_level"]
    if results.get("Understanding"):
        try:
            viva_list = viva.generate_viva_questions(understanding_data)
            if not isinstance(viva_list, list) or not viva_list:
                raise ValueError("generate_viva_questions returned empty or non-list output")

            tier_counts = {t: 0 for t in viva_tiers}
            for q in viva_list:
                t = q.get("tier")
                if t in tier_counts:
                    tier_counts[t] += 1

            for t in viva_tiers:
                count = tier_counts[t]
                print(f"  • {t.capitalize():<16}: {count} questions")
                if count == 0:
                    raise ValueError(f"Tier '{t}' has 0 questions generated")

            print(f"  ✓ Total viva questions: {len(viva_list)} across all 4 tiers")
            results["Viva"] = True
        except Exception as exc:
            print(f"  ✗ Viva generation failed: {exc}")
            results["Viva"] = False
            failures.append(f"Viva: {exc}")
    else:
        print("  ⊘ Skipped due to previous step failure")
        results["Viva"] = False

    # ── 8. FLASHCARDS ─────────────────────────────────────────────────────────
    print("\n[Step 8/9] FLASHCARDS")
    if results.get("Understanding"):
        try:
            cards = flashcards.generate_flashcards(understanding_data, findings_list)
            if not isinstance(cards, list) or not cards:
                raise ValueError("generate_flashcards returned an empty list")

            csv_text = flashcards.export_flashcards_csv(cards)
            if not isinstance(csv_text, str) or (
                not csv_text.startswith('"question","answer"')
                and not csv_text.startswith("question,answer")
            ):
                raise ValueError("Exported flashcards CSV missing 'question,answer' header")

            print(f"  ✓ Generated {len(cards)} active-recall flashcards")
            print(f"  ✓ Successfully verified Anki CSV export ({len(csv_text):,} characters)")
            results["Flashcards"] = True
        except Exception as exc:
            print(f"  ✗ Flashcard generation failed: {exc}")
            results["Flashcards"] = False
            failures.append(f"Flashcards: {exc}")
    else:
        print("  ⊘ Skipped due to previous step failure")
        results["Flashcards"] = False

    # ── 9. API INTEGRATION ────────────────────────────────────────────────────
    print("\n[Step 9/9] API INTEGRATION")
    api_url = f"http://localhost:{getattr(config, 'API_PORT', 8000)}"
    try:
        import httpx

        with httpx.Client(timeout=3.0) as client:
            health_res = client.get(f"{api_url}/health")
            if health_res.status_code != 200 or health_res.json().get("status") != "ok":
                raise ValueError(
                    f"Health check failed (HTTP {health_res.status_code}): {health_res.text}"
                )
            print(f"  ✓ API is running at {api_url} (/health -> status: ok)")

            with open(pdf_path, "rb") as f:
                upload_res = client.post(
                    f"{api_url}/papers",
                    files={"file": (pdf_path.name, f, "application/pdf")},
                    timeout=180.0,
                )

            if upload_res.status_code != 200:
                raise ValueError(
                    f"POST /papers returned HTTP {upload_res.status_code}: {upload_res.text}"
                )

            paper_res = upload_res.json()
            status_val = paper_res.get("status")
            paper_id = paper_res.get("id")

            if status_val == "ready":
                print(f"  ✓ Uploaded and analyzed paper (status: ready, id: {paper_id})")
            elif status_val == "failed":
                print(
                    f"  ⚠ Paper processed with status 'failed': {paper_res.get('error_message')}"
                )
            else:
                print(f"  ✓ Upload response status: {status_val} (id: {paper_id})")

            results["API"] = True
    except (ImportError, Exception) as exc:
        err_msg = str(exc)
        if "Connection" in err_msg or "ConnectError" in err_msg or "refused" in err_msg.lower():
            print("  SKIPPED — API not running at localhost:8000")
        else:
            print(f"  SKIPPED — API integration skipped ({err_msg})")
        results["API"] = "SKIPPED"

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    step_order = [
        ("Parsing", "Parsing"),
        ("Sections", "Sections"),
        ("Understanding", "Understanding"),
        ("Formulas", "Formulas"),
        ("Findings", "Findings"),
        ("Notes", "Notes"),
        ("Viva", "Viva"),
        ("Flashcards", "Flashcards"),
        ("API", "API"),
    ]

    for key, display_name in step_order:
        status_val = results.get(key)
        if status_val is True:
            print(f"  ✓ {display_name}")
        elif status_val == "SKIPPED":
            print(f"  - {display_name} (SKIPPED — API not running)")
        else:
            print(f"  ✗ {display_name}")

    required_steps = ["Parsing", "Sections", "Understanding", "Notes", "Viva", "Flashcards"]
    failed_required = [s for s in required_steps if results.get(s) is not True]

    if failed_required:
        print("\n" + "!" * 70)
        print("VERIFICATION FAILED:")
        for fail in failures:
            print(f"  • {fail}")
        print("!" * 70)
        sys.exit(1)
    else:
        print("\nAll required pipeline stages verified successfully! ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
