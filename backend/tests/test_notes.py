import pytest
from app.notes import generate_notes, _field, _page_suffix


def test_page_suffix_with_valid_int():
    assert _page_suffix(3) == "  (p.3)"


def test_page_suffix_with_none():
    assert _page_suffix(None) == ""


def test_page_suffix_with_non_int():
    assert _page_suffix("3") == ""  # strings should not produce suffix


def test_field_normal():
    und = {"problem": {"text": "Some problem.", "page": 2}}
    text, page = _field(und, "problem")
    assert text == "Some problem."
    assert page == 2


def test_field_missing_key():
    text, page = _field({}, "problem")
    assert text == "Not specified in the provided text"
    assert page is None


def test_field_none_text():
    und = {"problem": {"text": None, "page": 5}}
    text, page = _field(und, "problem")
    assert text == "Not specified in the provided text"
    assert page == 5


def test_generate_notes_full():
    understanding = {
        "problem": {"text": "The problem.", "page": 1},
        "motivation": {"text": "The motivation.", "page": 2},
        "solution": {"text": "The method.", "page": 3},
        "dataset": {"text": "The dataset.", "page": 4},
        "methodology": {"text": "The methodology.", "page": 5},
        "metrics": {"text": "The metrics.", "page": 6},
        "key_results": {"text": "The results.", "page": 7},
        "limitations": {"text": "The limitations.", "page": 8},
    }
    formulas = [
        {
            "name": "Attention",
            "equation_raw": "softmax(QK^T)",
            "meaning": "Scaled attention.",
            "page": 3,
        }
    ]
    findings = [
        {"finding": "Achieved 90% accuracy.", "page": 7},
    ]

    md = generate_notes("Test Paper", understanding, formulas, findings)

    assert "# Quick Revision Notes — Test Paper" in md
    assert "## Problem\nThe problem.  (p.1)" in md
    assert "## Motivation\nThe motivation.  (p.2)" in md
    assert "## Method\nThe method.  (p.3)" in md
    assert "## Dataset\nThe dataset.  (p.4)" in md
    assert "## Methodology\nThe methodology.  (p.5)" in md
    assert "## Metrics\nThe metrics.  (p.6)" in md
    assert "## Key Results\nThe results.  (p.7)" in md
    assert "## Limitations\nThe limitations.  (p.8)" in md
    assert "- **Attention**: Scaled attention.  (p.3)" in md
    assert "- Achieved 90% accuracy.  (p.7)" in md


def test_generate_notes_none_page_no_suffix():
    understanding = {
        "problem": {"text": "A problem.", "page": None},
        "motivation": {"text": "A motivation.", "page": 1},
        "solution": {"text": "A solution.", "page": None},
        "dataset": {"text": "A dataset.", "page": None},
        "methodology": {"text": "A method.", "page": None},
        "metrics": {"text": "Some metrics.", "page": None},
        "key_results": {"text": "Some results.", "page": None},
        "limitations": {"text": "Some limitations.", "page": None},
    }
    md = generate_notes("Test", understanding, [], [])
    assert "## Problem\nA problem.\n" in md           # no "(p.None)"
    assert "(p.None)" not in md
    assert "(p.1)" in md                               # motivation page present


def test_generate_notes_null_equation_raw():
    understanding = {
        "problem": {"text": "P.", "page": 1},
        "motivation": {"text": "M.", "page": 1},
        "solution": {"text": "S.", "page": 1},
        "dataset": {"text": "D.", "page": 1},
        "methodology": {"text": "Me.", "page": 1},
        "metrics": {"text": "Met.", "page": 1},
        "key_results": {"text": "R.", "page": 1},
        "limitations": {"text": "L.", "page": 1},
    }
    formulas = [
        {"name": "PositionalEncoding", "equation_raw": None, "meaning": "Anything.", "page": 2}
    ]
    md = generate_notes("Title", understanding, formulas, [])
    assert "formula not machine-readable, see paper" in md
    assert "PositionalEncoding" in md


def test_generate_notes_empty_formulas_and_findings():
    understanding = {k: {"text": "x", "page": 1} for k in [
        "problem", "motivation", "solution", "dataset",
        "methodology", "metrics", "key_results", "limitations"
    ]}
    md = generate_notes("Empty Paper", understanding, [], [])
    assert "_No formulas detected._" in md
    assert "_No findings detected._" in md
