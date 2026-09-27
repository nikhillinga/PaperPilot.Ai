import pytest
from unittest.mock import MagicMock, patch

from app.formulas import _is_candidate_page, extract_formulas
from app.llm_client import LLMOutputError


def test_is_candidate_page():
    # 2+ tokens: = and √ and subscript
    line1 = "Attention(Q, K, V) = softmax(QK^T / √d_k) V"
    assert _is_candidate_page(line1) is True

    # 2+ tokens: ∑ and =
    line2 = "The loss is defined as L = - ∑ y_i log(p_i)"
    assert _is_candidate_page(line2) is True

    # Greek letters and comparison: α and ≤ and β
    line3 = "Subject to constraint: α ≤ β"
    assert _is_candidate_page(line3) is True

    # Subscripts and indexed symbols: x_i and y(i)
    line4 = "Where x_i denotes the input and y(i) denotes target"
    assert _is_candidate_page(line4) is True

    # Only 1 token: not enough
    line5 = "We set the value a = 5 in our experiment."
    assert _is_candidate_page(line5) is False

    # Plain narrative text: 0 tokens
    line6 = "In this section we discuss previous works on image processing."
    assert _is_candidate_page(line6) is False


def test_extract_formulas_empty_pages():
    assert extract_formulas([]) == []


def test_extract_formulas_no_candidate_pages_skips_llm():
    pages = [
        {"page_number": 1, "text": "[PAGE 1]\nIntroduction to our work."},
        {"page_number": 2, "text": "[PAGE 2]\nWe present results of the survey."},
    ]
    with patch("app.llm_client.call_llm") as mock_call:
        res = extract_formulas(pages)
        assert res == []
        mock_call.assert_not_called()


def test_extract_formulas_candidate_and_prior_context():
    # Page 1: normal prose introducing method
    # Page 2: contains formula (candidate)
    # Page 3: normal prose without formula
    pages = [
        {"page_number": 1, "text": "[PAGE 1]\nIntroducing our model architecture."},
        {"page_number": 2, "text": "[PAGE 2]\nFormula: Attention(Q, K) = softmax(Q K^T / √d_k)"},
        {"page_number": 3, "text": "[PAGE 3]\nEvaluation on standard benchmarks."},
    ]

    mock_llm_response = [
        {
            "name": "Scaled Dot-Product Attention",
            "equation_raw": "Attention(Q, K) = softmax(Q K^T / √d_k)",
            "meaning": "Calculates attention weights",
            "variables": [{"symbol": "Q", "meaning": "Queries"}],
            "page": 2,
        }
    ]

    with patch("app.prompts.build_formula_prompt") as mock_prompt, \
         patch("app.llm_client.call_llm", return_value=mock_llm_response) as mock_call:
        mock_prompt.return_value = ("system prompt", "user prompt")

        res = extract_formulas(pages)
        assert res == mock_llm_response

        # Check prompt was built with page 1 and page 2 text (context + candidate), but not page 3
        mock_prompt.assert_called_once()
        passed_text = mock_prompt.call_args[0][0]
        assert "[PAGE 1]" in passed_text
        assert "[PAGE 2]" in passed_text
        assert "[PAGE 3]" not in passed_text


def test_extract_formulas_llmoutputerror_returns_empty_list(capsys):
    pages = [
        {"page_number": 1, "text": "[PAGE 1]\nL = - ∑ y_i log(p_i) where y_i is ground truth."}
    ]

    with patch("app.llm_client.call_llm", side_effect=LLMOutputError("Failed to parse JSON")):
        res = extract_formulas(pages)
        assert res == []

        captured = capsys.readouterr()
        assert "Warning: Formula extraction failed with LLMOutputError" in captured.out
