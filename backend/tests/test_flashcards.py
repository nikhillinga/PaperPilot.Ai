import csv
import io
import json
import pytest
from unittest.mock import MagicMock, patch

from app.flashcards import generate_flashcards, export_flashcards_csv, _validate_item
from app.llm_client import LLMOutputError

SAMPLE_UNDERSTANDING = {
    "problem": {"text": "Recurrence prevents parallelisation.", "page": 1},
    "motivation": {"text": "Attention allows global dependencies.", "page": 2},
    "solution": {"text": "Transformer based solely on attention.", "page": 3},
    "dataset": {"text": "WMT 2014 translation tasks.", "page": 5},
    "methodology": {"text": "6-layer encoder-decoder.", "page": 4},
    "metrics": {"text": "BLEU score.", "page": 6},
    "key_results": {"text": "28.4 BLEU on EN-DE.", "page": 7},
    "limitations": {"text": "Context window limits.", "page": 8},
}

SAMPLE_FINDINGS = [
    {
        "claim": "Transformer achieves state-of-the-art 28.4 BLEU.",
        "evidence": "Table 2: 28.4 vs 26.3 prior best.",
        "page": 7,
    },
]


def test_validate_item_valid():
    item = {"question": "What is self-attention?", "answer": "A mechanism relating positions of a sequence."}
    assert _validate_item(item) == item


def test_validate_item_missing_keys():
    assert _validate_item({"question": "Only question?"}) is None
    assert _validate_item({"answer": "Only answer."}) is None
    assert _validate_item({}) is None


def test_validate_item_empty_or_whitespace_strings():
    assert _validate_item({"question": "", "answer": "Valid"}) is None
    assert _validate_item({"question": "   ", "answer": "Valid"}) is None
    assert _validate_item({"question": "Valid", "answer": ""}) is None
    assert _validate_item({"question": "Valid", "answer": "   "}) is None


def test_validate_item_non_string_values():
    assert _validate_item({"question": 123, "answer": "Valid"}) is None
    assert _validate_item({"question": "Valid", "answer": None}) is None
    assert _validate_item("not a dict") is None
    assert _validate_item(None) is None


def test_generate_flashcards_success():
    mock_cards = [
        {"question": "What is the core architecture?", "answer": "The Transformer model."},
        {"question": "What was the BLEU score achieved?", "answer": "28.4 BLEU on WMT 2014 EN-DE."},
    ]

    with patch("app.prompts.build_flashcards_prompt", return_value=("sys", "user")) as mock_prompt, \
         patch("app.llm_client.call_llm", return_value=mock_cards) as mock_call:
        result = generate_flashcards(SAMPLE_UNDERSTANDING, SAMPLE_FINDINGS)

        assert len(result) == 2
        assert result == mock_cards

        mock_prompt.assert_called_once()
        u_json, f_json, count = mock_prompt.call_args[0]
        assert json.loads(u_json) == SAMPLE_UNDERSTANDING
        assert json.loads(f_json) == SAMPLE_FINDINGS
        assert count == 12


def test_generate_flashcards_drops_invalid_items():
    mock_cards = [
        {"question": "Valid Q1?", "answer": "Valid A1."},
        {"question": "Missing answer?"},
        {"question": "Empty answer?", "answer": "   "},
        {"answer": "Missing question."},
        "not a dict",
        {"question": "Valid Q2?", "answer": "Valid A2."},
    ]

    with patch("app.prompts.build_flashcards_prompt", return_value=("sys", "user")), \
         patch("app.llm_client.call_llm", return_value=mock_cards):
        result = generate_flashcards(SAMPLE_UNDERSTANDING, SAMPLE_FINDINGS)
        assert len(result) == 2
        assert result[0]["question"] == "Valid Q1?"
        assert result[1]["question"] == "Valid Q2?"


def test_generate_flashcards_dict_wrapped_response():
    wrapped = {
        "flashcards": [
            {"question": "What is self-attention?", "answer": "An attention mechanism."},
            {"question": "What hardware was used?", "answer": "8 P100 GPUs."},
        ]
    }

    with patch("app.prompts.build_flashcards_prompt", return_value=("sys", "user")), \
         patch("app.llm_client.call_llm", return_value=wrapped):
        result = generate_flashcards(SAMPLE_UNDERSTANDING, SAMPLE_FINDINGS)
        assert len(result) == 2
        assert result[0]["question"] == "What is self-attention?"


def test_generate_flashcards_reraises_llmoutputerror():
    with patch("app.prompts.build_flashcards_prompt", return_value=("sys", "user")), \
         patch("app.llm_client.call_llm", side_effect=LLMOutputError("LLM failed")):
        with pytest.raises(LLMOutputError, match="LLM failed"):
            generate_flashcards(SAMPLE_UNDERSTANDING, SAMPLE_FINDINGS)


def test_generate_flashcards_uses_custom_config_target():
    with patch("app.prompts.build_flashcards_prompt", return_value=("sys", "user")) as mock_prompt, \
         patch("app.llm_client.call_llm", return_value=[]), \
         patch("app.config.FLASHCARD_COUNT_TARGET", 20):
        generate_flashcards(SAMPLE_UNDERSTANDING, SAMPLE_FINDINGS)
        _, _, count = mock_prompt.call_args[0]
        assert count == 20


def test_export_flashcards_csv_header_and_content():
    cards = [
        {"question": "What is attention?", "answer": "A weighting mechanism."},
        {"question": "How many heads?", "answer": "8 attention heads."},
    ]

    csv_text = export_flashcards_csv(cards)
    reader = list(csv.reader(io.StringIO(csv_text)))

    assert len(reader) == 3
    assert reader[0] == ["question", "answer"]
    assert reader[1] == ["What is attention?", "A weighting mechanism."]
    assert reader[2] == ["How many heads?", "8 attention heads."]


def test_export_flashcards_csv_quoting_and_special_chars():
    cards = [
        {
            "question": 'What is "self-attention", exactly?',
            "answer": "It relates different positions of a single sequence, e.g., words.",
        }
    ]

    csv_text = export_flashcards_csv(cards)

    # All fields should be quoted
    assert csv_text.startswith('"question","answer"')
    assert '""self-attention""' in csv_text
    assert '"It relates different positions of a single sequence, e.g., words."' in csv_text

    # Verify standard CSV round-trip parsing
    reader = list(csv.reader(io.StringIO(csv_text)))
    assert len(reader) == 2
    assert reader[1][0] == 'What is "self-attention", exactly?'
    assert reader[1][1] == "It relates different positions of a single sequence, e.g., words."


def test_export_flashcards_csv_empty():
    csv_text = export_flashcards_csv([])
    reader = list(csv.reader(io.StringIO(csv_text)))
    assert len(reader) == 1
    assert reader[0] == ["question", "answer"]
