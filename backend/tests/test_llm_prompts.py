import json
import pytest
from unittest.mock import MagicMock, patch

from app import prompts
from app import llm_client
from app.llm_client import LLMOutputError, _strip_markdown_code_fences, call_llm


def test_shared_grounding_rules():
    assert "Only state facts that are explicitly present in the provided text" in prompts.SHARED_GROUNDING_RULES
    assert "The provided text contains [PAGE n] markers" in prompts.SHARED_GROUNDING_RULES
    assert "Return ONLY valid JSON" in prompts.SHARED_GROUNDING_RULES


def test_build_understanding_prompt():
    s, u = prompts.build_understanding_prompt("section sample text")
    assert prompts.SHARED_GROUNDING_RULES in s
    assert u == "section sample text"
    for key in ["problem", "motivation", "solution", "dataset", "methodology", "metrics", "key_results", "limitations"]:
        assert key in s


def test_build_formula_prompt():
    s, u = prompts.build_formula_prompt("math equations page text")
    assert prompts.SHARED_GROUNDING_RULES in s
    assert u == "math equations page text"
    assert "equation_raw" in s
    assert "Formula detected on this page but could not be extracted as text." in s


def test_build_findings_prompt():
    s, u = prompts.build_findings_prompt("sections text for findings")
    assert prompts.SHARED_GROUNDING_RULES in s
    assert u == "sections text for findings"
    assert "3 to 6" in s


def test_build_viva_prompt():
    s, u = prompts.build_viva_prompt('{"summary": "test"}', 3)
    assert prompts.SHARED_GROUNDING_RULES in s
    assert "basic" in s and "intermediate" in s and "advanced" in s and "research_level" in s
    assert "3 questions" in s or "3" in s
    assert '{"summary": "test"}' in u


def test_build_flashcards_prompt():
    s, u = prompts.build_flashcards_prompt('{"summary": "test"}', '[{"finding": "f"}]', 12)
    assert prompts.SHARED_GROUNDING_RULES in s
    assert "12" in s
    assert '{"summary": "test"}' in u
    assert '[{"finding": "f"}]' in u


def test_strip_markdown_code_fences():
    case1 = '```json\n{"ok": true}\n```'
    assert _strip_markdown_code_fences(case1) == '{"ok": true}'

    case2 = '```\n{"ok": true}\n```'
    assert _strip_markdown_code_fences(case2) == '{"ok": true}'

    case3 = '{"ok": true}'
    assert _strip_markdown_code_fences(case3) == '{"ok": true}'

    case4 = 'Here is the JSON:\n```json\n{"ok": true}\n```\nHope it helps.'
    assert _strip_markdown_code_fences(case4) == '{"ok": true}'


def test_call_llm_anthropic_success():
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = '```json\n{"ok": true}\n```'
    mock_response.content = [mock_block]

    with patch("app.config.LLM_PROVIDER", "anthropic"), \
         patch("app.config.ANTHROPIC_API_KEY", "test-key"), \
         patch("app.llm_client.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        res = call_llm("system", "user", expect_json=True)
        assert res == {"ok": True}


def test_call_llm_openai_success():
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"ok": true}\n```'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.config.LLM_PROVIDER", "openai"), \
         patch("app.config.OPENAI_API_KEY", "test-key"), \
         patch("app.llm_client.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        res = call_llm("system", "user", expect_json=True)
        assert res == {"ok": True}


def test_call_llm_raw_text():
    mock_choice = MagicMock()
    mock_choice.message.content = "Plain text response."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.config.LLM_PROVIDER", "openai"), \
         patch("app.config.OPENAI_API_KEY", "test-key"), \
         patch("app.llm_client.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        res = call_llm("system", "user", expect_json=False)
        assert res == "Plain text response."


def test_call_llm_retry_on_bad_json_success():
    mock_choice1 = MagicMock()
    mock_choice1.message.content = "Not JSON initially"

    mock_choice2 = MagicMock()
    mock_choice2.message.content = '{"retry": "success"}'

    mock_response1 = MagicMock()
    mock_response1.choices = [mock_choice1]

    mock_response2 = MagicMock()
    mock_response2.choices = [mock_choice2]

    with patch("app.config.LLM_PROVIDER", "openai"), \
         patch("app.config.OPENAI_API_KEY", "test-key"), \
         patch("app.llm_client.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]

        res = call_llm("system", "user", expect_json=True)
        assert res == {"retry": "success"}
        assert mock_client.chat.completions.create.call_count == 2


def test_call_llm_retry_failure_raises_llmoutputerror():
    mock_choice1 = MagicMock()
    mock_choice1.message.content = "Not JSON initially"

    mock_choice2 = MagicMock()
    mock_choice2.message.content = "Still not JSON after retry"

    mock_response1 = MagicMock()
    mock_response1.choices = [mock_choice1]

    mock_response2 = MagicMock()
    mock_response2.choices = [mock_choice2]

    with patch("app.config.LLM_PROVIDER", "openai"), \
         patch("app.config.OPENAI_API_KEY", "test-key"), \
         patch("app.llm_client.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]

        with pytest.raises(LLMOutputError) as exc_info:
            call_llm("system", "user", expect_json=True)
        assert "Still not JSON after retry" in str(exc_info.value)


def test_call_llm_provider_error_wrapping():
    with patch("app.config.LLM_PROVIDER", "openai"), \
         patch("app.config.OPENAI_API_KEY", "test-key"), \
         patch("app.config.LLM_FALLBACK_MODELS", []), \
         patch("app.llm_client.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("Connection timeout")

        with pytest.raises(LLMOutputError) as exc_info:
            call_llm("system", "user", expect_json=True)
        assert "Connection timeout" in str(exc_info.value)
