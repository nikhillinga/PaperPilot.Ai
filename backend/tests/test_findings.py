import pytest
from unittest.mock import MagicMock, patch

from app.findings import _is_findings_section, extract_findings
from app.llm_client import LLMOutputError


def test_is_findings_section():
    assert _is_findings_section("Results") is True
    assert _is_findings_section("Results (2)") is True
    assert _is_findings_section("4. Results") is True
    assert _is_findings_section("Evaluation") is True
    assert _is_findings_section("Discussion") is True
    assert _is_findings_section("Conclusion") is True
    assert _is_findings_section("Introduction") is False
    assert _is_findings_section("Methodology") is False
    assert _is_findings_section("Abstract") is False


def test_extract_findings_empty_sections():
    assert extract_findings({}) == []


def test_extract_findings_success():
    sections = {
        "Introduction": "Introductory content.",
        "Methodology": "Methodology content.",
        "Results": "The model achieves 95.5% accuracy, beating baseline by 3.2%.",
        "Discussion": "Discussion on latency and efficiency improvements.",
    }

    mock_llm_response = [
        {"finding": "Achieves 95.5% accuracy, exceeding baseline by 3.2%", "page": 6},
        {"finding": "Inference latency reduced by 40% on GPU benchmarks", "page": 7},
    ]

    with patch("app.prompts.build_findings_prompt") as mock_prompt, \
         patch("app.llm_client.call_llm", return_value=mock_llm_response) as mock_call:
        mock_prompt.return_value = ("sys prompt", "user prompt")

        res = extract_findings(sections)
        assert res == mock_llm_response

        # Check prompt was built with Results and Discussion text, but NOT Intro or Methodology
        mock_prompt.assert_called_once()
        passed_text = mock_prompt.call_args[0][0]
        assert "Results" in passed_text
        assert "Discussion" in passed_text
        assert "Introduction" not in passed_text
        assert "Methodology" not in passed_text


def test_extract_findings_fallback_to_full_text():
    sections = {
        "Full Text": "All paper text containing some results.",
    }

    mock_llm_response = [
        {"finding": "Full text result finding.", "page": 1}
    ]

    with patch("app.prompts.build_findings_prompt") as mock_prompt, \
         patch("app.llm_client.call_llm", return_value=mock_llm_response):
        mock_prompt.return_value = ("sys prompt", "user prompt")

        res = extract_findings(sections)
        assert res == mock_llm_response
        passed_text = mock_prompt.call_args[0][0]
        assert "Full Text" in passed_text


def test_extract_findings_llmoutputerror_returns_empty_list(capsys):
    sections = {
        "Results": "Some results text.",
    }

    with patch("app.llm_client.call_llm", side_effect=LLMOutputError("LLM failed")):
        res = extract_findings(sections)
        assert res == []

        captured = capsys.readouterr()
        assert "Warning: Findings extraction failed with LLMOutputError" in captured.out
