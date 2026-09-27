import pytest
from unittest.mock import MagicMock, patch

from app.understanding import (
    EXPECTED_KEYS,
    FALLBACK_VALUE,
    _is_relevant_section,
    _truncate_sections_text,
    generate_understanding,
)


def test_is_relevant_section():
    assert _is_relevant_section("Introduction") is True
    assert _is_relevant_section("1. Introduction") is True
    assert _is_relevant_section("Methodology") is True
    assert _is_relevant_section("Method") is True
    assert _is_relevant_section("Approach") is True
    assert _is_relevant_section("Results") is True
    assert _is_relevant_section("Results (2)") is True
    assert _is_relevant_section("Evaluation") is True
    assert _is_relevant_section("Discussion") is True
    assert _is_relevant_section("Conclusion") is True
    assert _is_relevant_section("Limitations") is True
    assert _is_relevant_section("Appendix") is False
    assert _is_relevant_section("References") is False


def test_truncate_sections_text_within_budget():
    sections = [
        ("Introduction", "Short intro text."),
        ("Methodology", "Short methodology text."),
    ]
    out = _truncate_sections_text(sections, max_chars=1000)
    assert "Short intro text." in out
    assert "Short methodology text." in out
    assert len(out) <= 1000


def test_truncate_sections_text_exceeding_budget(caplog):
    sections = [
        ("Introduction", "A" * 500),
        ("Methodology", "B" * 500),
        ("Results", "C" * 500),
    ]
    # Set limit lower than 1500 + overhead
    out = _truncate_sections_text(sections, max_chars=600)
    assert len(out) <= 600
    # Make sure all sections are represented
    assert "=== Introduction ===" in out
    assert "=== Methodology ===" in out
    assert "=== Results ===" in out


def test_generate_understanding_full_keys():
    mock_llm_response = {
        "problem": {"text": "A problem", "page": 1},
        "motivation": {"text": "A motivation", "page": 1},
        "solution": {"text": "A solution", "page": 2},
        "dataset": {"text": "A dataset", "page": 3},
        "methodology": {"text": "A methodology", "page": 4},
        "metrics": {"text": "A metric", "page": 5},
        "key_results": {"text": "A key result", "page": 6},
        "limitations": {"text": "A limitation", "page": 7},
    }

    sections = {
        "Introduction": "Introduction content with [PAGE 1]",
        "Methodology": "Methodology content with [PAGE 4]",
    }

    with patch("app.llm_client.call_llm", return_value=mock_llm_response) as mock_call:
        res = generate_understanding(sections)
        mock_call.assert_called_once()
        assert res == mock_llm_response
        for k in EXPECTED_KEYS:
            assert k in res


def test_generate_understanding_missing_keys_backfilled():
    # LLM returned only 3 keys
    mock_llm_response = {
        "problem": {"text": "A problem", "page": 1},
        "solution": {"text": "A solution", "page": 2},
        "key_results": {"text": "A key result", "page": 3},
    }

    sections = {"Introduction": "Intro text"}

    with patch("app.llm_client.call_llm", return_value=mock_llm_response):
        res = generate_understanding(sections)
        assert len(res) == 8
        assert res["problem"] == {"text": "A problem", "page": 1}
        assert res["motivation"] == {"text": "Not specified in the provided text", "page": None}
        assert res["dataset"] == {"text": "Not specified in the provided text", "page": None}
        assert res["methodology"] == {"text": "Not specified in the provided text", "page": None}
        assert res["metrics"] == {"text": "Not specified in the provided text", "page": None}
        assert res["limitations"] == {"text": "Not specified in the provided text", "page": None}


def test_generate_understanding_empty_sections():
    res = generate_understanding({})
    assert len(res) == 8
    for k in EXPECTED_KEYS:
        assert res[k] == FALLBACK_VALUE


def test_generate_understanding_unrecognized_sections_fallback():
    # When paper has "Full Text" only
    sections = {"Full Text": "All paper text here."}
    mock_llm_response = {k: {"text": f"val {k}", "page": 1} for k in EXPECTED_KEYS}

    with patch("app.llm_client.call_llm", return_value=mock_llm_response) as mock_call:
        res = generate_understanding(sections)
        mock_call.assert_called_once()
        assert res["problem"]["text"] == "val problem"
