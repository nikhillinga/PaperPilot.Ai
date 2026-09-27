import json
import pytest
from unittest.mock import MagicMock, patch

from app.viva import generate_viva_questions, _validate_item, VALID_TIERS
from app.llm_client import LLMOutputError

SAMPLE_UNDERSTANDING = {
    "problem": {"text": "Problem text.", "page": 1},
    "motivation": {"text": "Motivation text.", "page": 2},
    "solution": {"text": "Solution text.", "page": 3},
    "dataset": {"text": "Dataset text.", "page": 4},
    "methodology": {"text": "Methodology text.", "page": 5},
    "metrics": {"text": "Metrics text.", "page": 6},
    "key_results": {"text": "Results text.", "page": 7},
    "limitations": {"text": "Limitations text.", "page": 8},
}


def _make_question(tier: str, n: int = 1) -> dict:
    return {
        "tier": tier,
        "question": f"Q{n} for {tier}?",
        "model_answer": f"Answer {n} for {tier}.",
    }


def test_validate_item_valid():
    item = {"tier": "basic", "question": "Q?", "model_answer": "A."}
    assert _validate_item(item) == item


def test_validate_item_invalid_tier():
    item = {"tier": "expert", "question": "Q?", "model_answer": "A."}
    assert _validate_item(item) is None


def test_validate_item_missing_key():
    item = {"tier": "basic", "question": "Q?"}  # missing model_answer
    assert _validate_item(item) is None


def test_validate_item_not_a_dict():
    assert _validate_item("not a dict") is None
    assert _validate_item(42) is None
    assert _validate_item(None) is None


def test_generate_viva_questions_success():
    mock_response = [
        _make_question("basic", 1),
        _make_question("intermediate", 1),
        _make_question("advanced", 1),
        _make_question("research_level", 1),
    ]

    with patch("app.prompts.build_viva_prompt") as mock_prompt, \
         patch("app.llm_client.call_llm", return_value=mock_response) as mock_call:
        mock_prompt.return_value = ("sys", "user")

        result = generate_viva_questions(SAMPLE_UNDERSTANDING)

        assert len(result) == 4
        tiers = {q["tier"] for q in result}
        assert tiers == {"basic", "intermediate", "advanced", "research_level"}

        # Understanding should be serialised to JSON string for the prompt
        mock_prompt.assert_called_once()
        understanding_json_arg = mock_prompt.call_args[0][0]
        assert json.loads(understanding_json_arg) == SAMPLE_UNDERSTANDING


def test_generate_viva_questions_drops_invalid_items():
    mock_response = [
        _make_question("basic"),
        {"tier": "unknown_tier", "question": "Q?", "model_answer": "A."},  # bad tier
        {"tier": "advanced", "question": "Q?"},                             # missing model_answer
        _make_question("research_level"),
    ]

    with patch("app.prompts.build_viva_prompt", return_value=("sys", "user")), \
         patch("app.llm_client.call_llm", return_value=mock_response):
        result = generate_viva_questions(SAMPLE_UNDERSTANDING)
        assert len(result) == 2
        tiers = {q["tier"] for q in result}
        assert tiers == {"basic", "research_level"}


def test_generate_viva_questions_dict_wrapped_response():
    """LLM may wrap list inside a 'questions' key."""
    wrapped = {
        "questions": [
            _make_question("basic"),
            _make_question("intermediate"),
        ]
    }

    with patch("app.prompts.build_viva_prompt", return_value=("sys", "user")), \
         patch("app.llm_client.call_llm", return_value=wrapped):
        result = generate_viva_questions(SAMPLE_UNDERSTANDING)
        assert len(result) == 2


def test_generate_viva_questions_reraises_llmoutputerror():
    """LLMOutputError must propagate — viva is a mandatory feature."""
    with patch("app.prompts.build_viva_prompt", return_value=("sys", "user")), \
         patch("app.llm_client.call_llm", side_effect=LLMOutputError("API failure")):
        with pytest.raises(LLMOutputError, match="API failure"):
            generate_viva_questions(SAMPLE_UNDERSTANDING)


def test_generate_viva_questions_uses_config_per_tier():
    with patch("app.prompts.build_viva_prompt") as mock_prompt, \
         patch("app.llm_client.call_llm", return_value=[]), \
         patch("app.config.VIVA_QUESTIONS_PER_TIER", 5):
        mock_prompt.return_value = ("sys", "user")
        generate_viva_questions(SAMPLE_UNDERSTANDING)
        _, questions_per_tier_arg = mock_prompt.call_args[0]
        assert questions_per_tier_arg == 5
