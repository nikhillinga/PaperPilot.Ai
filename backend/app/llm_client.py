"""
llm_client.py — Unified LLM client for PaperPilot.

Supports both Anthropic and OpenAI behind a single call_llm interface, with
automatic JSON extraction, markdown code-fence stripping, one-shot retry on
malformed JSON, and clean error wrapping via LLMOutputError.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

try:
    from app import config
except ImportError:
    import config


class LLMOutputError(Exception):
    """Raised when an LLM call fails or returns unparseable output."""
    pass


def _strip_markdown_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ``` or ``` ... ```) from text."""
    stripped = text.strip()

    # Match fenced block spanning the entire or majority of text
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(fence_pattern, stripped, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Search for an embedded fenced block
    fence_search = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
    if fence_search:
        return fence_search.group(1).strip()

    # Fallback line-by-line strip if starts with ```
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    return stripped


def _invoke_provider(
    system_prompt: str,
    messages: list[dict[str, str]],
    provider: str,
) -> str:
    """Execute raw provider API call and return the response text.

    Catches any SDK / network / authentication errors and raises LLMOutputError.
    """
    prov = (provider or "").strip().lower()

    if prov == "anthropic":
        if anthropic is None:
            raise LLMOutputError(
                "The 'anthropic' package is not installed. Please install it via requirements.txt."
            )
        if not config.ANTHROPIC_API_KEY:
            raise LLMOutputError("ANTHROPIC_API_KEY is not configured.")

        try:
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=config.LLM_MODEL,
                max_tokens=config.LLM_MAX_TOKENS,
                temperature=config.LLM_TEMPERATURE,
                system=system_prompt,
                messages=messages,
            )
            if not response.content:
                raise LLMOutputError("Anthropic API returned an empty response.")
            return response.content[0].text
        except LLMOutputError:
            raise
        except Exception as exc:
            raise LLMOutputError(f"Anthropic API call failed: {exc}") from exc

    elif prov == "openai":
        if openai is None:
            raise LLMOutputError(
                "The 'openai' package is not installed. Please install it via requirements.txt."
            )
        if not config.OPENAI_API_KEY:
            raise LLMOutputError("OPENAI_API_KEY is not configured.")

        # Build the list of models to try: primary first, then any fallbacks.
        primary_model = config.LLM_MODEL
        fallback_models: list[str] = getattr(config, "LLM_FALLBACK_MODELS", [])
        models_to_try = [primary_model] + fallback_models

        # Retry settings for transient empty/overload responses from free-tier pools.
        _MAX_ATTEMPTS = 3
        _RETRY_SLEEP = 2  # seconds

        last_exc: Exception | None = None
        for model_id in models_to_try:
            for attempt in range(1, _MAX_ATTEMPTS + 1):
                try:
                    base_url = getattr(config, "OPENAI_BASE_URL", "") or None
                    kwargs: dict[str, Any] = {"api_key": config.OPENAI_API_KEY}
                    if base_url:
                        kwargs["base_url"] = base_url
                    client = openai.OpenAI(**kwargs)
                    openai_messages = [{"role": "system", "content": system_prompt}] + messages
                    response = client.chat.completions.create(
                        model=model_id,
                        max_tokens=config.LLM_MAX_TOKENS,
                        temperature=config.LLM_TEMPERATURE,
                        messages=openai_messages,
                    )
                    choice = response.choices[0]
                    content = choice.message.content if choice.message else None
                    if not content:
                        logger.warning(
                            "OpenAI/OpenRouter returned empty content on attempt %d/%d "
                            "for model '%s'. Retrying in %ds...",
                            attempt, _MAX_ATTEMPTS, model_id, _RETRY_SLEEP,
                        )
                        last_exc = LLMOutputError(
                            f"Model '{model_id}' returned empty response (attempt {attempt}/{_MAX_ATTEMPTS})."
                        )
                        if attempt < _MAX_ATTEMPTS:
                            time.sleep(_RETRY_SLEEP)
                        continue
                    return content
                except LLMOutputError:
                    raise
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "OpenAI API call failed on attempt %d/%d for model '%s': %s",
                        attempt, _MAX_ATTEMPTS, model_id, exc,
                    )
                    if attempt < _MAX_ATTEMPTS:
                        time.sleep(_RETRY_SLEEP)

        raise LLMOutputError(
            f"OpenAI API call failed after all attempts across models {models_to_try}. "
            f"Last error: {last_exc}"
        ) from last_exc

    else:
        raise LLMOutputError(
            f"Unsupported LLM provider '{provider}'. Must be 'anthropic' or 'openai'."
        )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    expect_json: bool = True,
) -> dict[str, Any] | list[Any] | str:
    """
    Routes to Anthropic or OpenAI based on config.LLM_PROVIDER.

    Anthropic: use anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY).messages.create(
        model=config.LLM_MODEL, max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE, system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}])
    Extract text from response.content[0].text

    OpenAI: use openai.OpenAI(api_key=config.OPENAI_API_KEY).chat.completions.create(
        model=config.LLM_MODEL, max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}])
    Extract text from response.choices[0].message.content

    If expect_json is True:
    - Strip markdown code fences (```json ... ``` or ``` ... ```) from the
      response text before parsing
    - json.loads() the result
    - If parsing fails, retry ONCE: re-call the LLM with the same messages
      plus an appended user message: "Your previous response was not valid
      JSON. Return ONLY the JSON object, no markdown formatting, no
      preamble, no explanation."
    - If the retry also fails to parse, raise LLMOutputError with the raw
      response text included in the exception message

    If expect_json is False, return the raw text response.

    Wrap the actual API call in try/except and raise LLMOutputError on any
    provider-side failure (auth error, rate limit, timeout) with a clear
    message — never let a raw SDK exception propagate to the API layer.
    """
    messages: list[dict[str, str]] = [{"role": "user", "content": user_prompt}]
    raw_response = _invoke_provider(system_prompt, messages, config.LLM_PROVIDER)

    if not expect_json:
        return raw_response

    # Try parsing JSON on primary response
    cleaned = _strip_markdown_code_fences(raw_response)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Parsing failed: retry ONCE with appended instruction
    retry_prompt = (
        "Your previous response was not valid JSON. "
        "Return ONLY the JSON object, no markdown formatting, no preamble, no explanation."
    )
    retry_messages = [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": raw_response or ""},
        {"role": "user", "content": retry_prompt},
    ]

    retry_raw = _invoke_provider(system_prompt, retry_messages, config.LLM_PROVIDER)
    retry_cleaned = _strip_markdown_code_fences(retry_raw)
    try:
        return json.loads(retry_cleaned)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise LLMOutputError(
            f"Failed to parse JSON from LLM response after retry. Error: {exc}\nRaw response:\n{retry_raw}"
        ) from exc


if __name__ == "__main__":
    print(f"Testing LLM Client...")
    print(f"  Provider: {config.LLM_PROVIDER}")
    print(f"  Model:    {config.LLM_MODEL}")

    test_system = "You are a helpful assistant. Return ONLY valid JSON."
    test_user = 'Return JSON: {"ok": true}'

    try:
        result = call_llm(test_system, test_user, expect_json=True)
        print("Success! Parsed response:")
        print(result)
    except LLMOutputError as err:
        print(f"Verification call failed as expected or due to configuration:\n{err}")
        sys.exit(1)
