"""
viva.py — Oral defense (viva voce) question generation for PaperPilot.

Generates tiered examination questions (basic → research_level) grounded in
the extracted paper understanding. Unlike softer pipeline steps, LLM failures
here surface as real errors — viva questions are a core mandatory feature.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from typing import Any

try:
    from app import config, llm_client, prompts
except ImportError:
    import config, llm_client, prompts

logger = logging.getLogger(__name__)

VALID_TIERS = frozenset({"basic", "intermediate", "advanced", "research_level"})
REQUIRED_KEYS = frozenset({"tier", "question", "model_answer"})


def _validate_item(item: Any) -> dict | None:
    """Return the item if it has all required keys and a valid tier, else None."""
    if not isinstance(item, dict):
        logger.warning("Viva item is not a dict, dropping: %r", item)
        return None

    missing = REQUIRED_KEYS - item.keys()
    if missing:
        logger.warning("Viva item missing required keys %s, dropping: %r", missing, item)
        return None

    tier = item.get("tier")
    if tier not in VALID_TIERS:
        logger.warning(
            "Viva item has invalid tier %r (must be one of %s), dropping.",
            tier,
            sorted(VALID_TIERS),
        )
        return None

    return item


def generate_viva_questions(understanding: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Serializes `understanding` to a JSON string with json.dumps().
    Calls prompts.build_viva_prompt(understanding_json, config.VIVA_QUESTIONS_PER_TIER).
    Calls llm_client.call_llm(), expects a JSON array back.
    Validates each item has keys: tier, question, model_answer, and that
    tier is one of "basic", "intermediate", "advanced", "research_level".
    Drop (don't crash on) any items missing required keys, log a warning.
    Returns the validated list.
    If the LLM call raises LLMOutputError, re-raise it — unlike formulas/
    findings, a total viva-question failure should surface as a real error
    to the API layer, since it's a core mandatory feature.
    """
    understanding_json = json.dumps(understanding, ensure_ascii=False)

    questions_per_tier = getattr(config, "VIVA_QUESTIONS_PER_TIER", 3)
    system_prompt, user_prompt = prompts.build_viva_prompt(
        understanding_json, questions_per_tier
    )

    # Re-raise LLMOutputError — viva questions are mandatory
    raw_result = llm_client.call_llm(system_prompt, user_prompt, expect_json=True)

    if isinstance(raw_result, dict):
        # Unwrap if LLM wrapped array in a key
        for key in ("questions", "viva_questions", "items"):
            if key in raw_result and isinstance(raw_result[key], list):
                raw_result = raw_result[key]
                break
        else:
            raw_result = [raw_result]

    if not isinstance(raw_result, list):
        logger.warning("Viva LLM response was not a list; got %r", type(raw_result))
        raw_result = []

    validated: list[dict[str, Any]] = []
    for item in raw_result:
        clean = _validate_item(item)
        if clean is not None:
            validated.append(clean)

    return validated


if __name__ == "__main__":
    sample_understanding = {
        "problem": {"text": "Existing sequence models rely on recurrence, limiting parallelism.", "page": 1},
        "motivation": {"text": "Attention mechanisms allow modelling dependencies regardless of distance.", "page": 2},
        "solution": {"text": "The Transformer: a model architecture based entirely on self-attention.", "page": 3},
        "dataset": {"text": "WMT 2014 English-German and English-French translation tasks.", "page": 5},
        "methodology": {"text": "6-layer encoder-decoder, 8 attention heads, d_model=512, trained on 8×P100 GPUs.", "page": 4},
        "metrics": {"text": "BLEU score on held-out test sets.", "page": 6},
        "key_results": {"text": "28.4 BLEU on EN-DE, surpassing all prior single models.", "page": 7},
        "limitations": {"text": "Performance on very long sequences not fully explored.", "page": 8},
    }

    try:
        questions = generate_viva_questions(sample_understanding)
    except llm_client.LLMOutputError as exc:
        print(f"LLMOutputError: {exc}")
        sys.exit(1)

    print(f"Generated {len(questions)} viva questions\n")
    by_tier: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        by_tier[q["tier"]].append(q)

    for tier in ["basic", "intermediate", "advanced", "research_level"]:
        tier_qs = by_tier.get(tier, [])
        if not tier_qs:
            continue
        print(f"{'=' * 60}")
        print(f"TIER: {tier.upper()}")
        print(f"{'=' * 60}")
        for i, q in enumerate(tier_qs, 1):
            print(f"\nQ{i}: {q['question']}")
            print(f"A:  {q['model_answer']}")
    print()
