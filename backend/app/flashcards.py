"""
flashcards.py — Active-recall flashcard generation and export for PaperPilot.

Generates flashcards testing core concepts, architectural choices, and key empirical
takeaways grounded in the paper's understanding and findings. Also provides CSV export
formatted for Anki import.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
from typing import Any

try:
    from app import config, llm_client, prompts
except ImportError:
    import config, llm_client, prompts

logger = logging.getLogger(__name__)

REQUIRED_KEYS = frozenset({"question", "answer"})


def _validate_item(item: Any) -> dict | None:
    """Return the item if it has required keys and non-empty string values, else None."""
    if not isinstance(item, dict):
        logger.warning("Flashcard item is not a dict, dropping: %r", item)
        return None

    missing = REQUIRED_KEYS - item.keys()
    if missing:
        logger.warning(
            "Flashcard item missing required keys %s, dropping: %r", missing, item
        )
        return None

    question = item.get("question")
    answer = item.get("answer")

    if not isinstance(question, str) or not question.strip():
        logger.warning(
            "Flashcard item has invalid or empty question, dropping: %r", item
        )
        return None

    if not isinstance(answer, str) or not answer.strip():
        logger.warning(
            "Flashcard item has invalid or empty answer, dropping: %r", item
        )
        return None

    return item


def generate_flashcards(understanding: dict, findings: list[dict]) -> list[dict]:
    """
    Serializes understanding and findings to JSON strings.
    Calls prompts.build_flashcards_prompt(understanding_json, findings_json,
    config.FLASHCARD_COUNT_TARGET).
    Calls llm_client.call_llm(), expects a JSON array of
    {"question": str, "answer": str}.
    Validates each item has both keys and non-empty string values; drop
    invalid items rather than crashing.
    Re-raises LLMOutputError on total failure (mandatory feature, same
    reasoning as viva.py).
    """
    understanding_json = json.dumps(understanding, ensure_ascii=False)
    findings_json = json.dumps(findings, ensure_ascii=False)

    target_count = getattr(config, "FLASHCARD_COUNT_TARGET", 12)
    system_prompt, user_prompt = prompts.build_flashcards_prompt(
        understanding_json, findings_json, target_count
    )

    # Re-raise LLMOutputError on total failure — flashcards are a mandatory feature
    raw_result = llm_client.call_llm(system_prompt, user_prompt, expect_json=True)

    if isinstance(raw_result, dict):
        # Unwrap if LLM wrapped array in a common key
        for key in ("flashcards", "cards", "items", "deck", "questions"):
            if key in raw_result and isinstance(raw_result[key], list):
                raw_result = raw_result[key]
                break
        else:
            raw_result = [raw_result]

    if not isinstance(raw_result, list):
        logger.warning("Flashcards LLM response was not a list; got %r", type(raw_result))
        raw_result = []

    validated: list[dict] = []
    for item in raw_result:
        clean = _validate_item(item)
        if clean is not None:
            validated.append(clean)

    return validated


def export_flashcards_csv(flashcards: list[dict]) -> str:
    """
    Returns a CSV-formatted string with header row "question,answer",
    using Python's csv module with quoting=csv.QUOTE_ALL and a
    io.StringIO buffer, so commas/quotes inside questions or answers
    don't break the file. This format should import cleanly into Anki's
    "Basic" note type (question,answer columns).
    """
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(["question", "answer"])
    for card in flashcards:
        if isinstance(card, dict):
            writer.writerow([card.get("question", ""), card.get("answer", "")])
    return buf.getvalue()


if __name__ == "__main__":
    sample_understanding = {
        "problem": {
            "text": "Existing sequence models rely on recurrence, limiting parallelism.",
            "page": 1,
        },
        "motivation": {
            "text": "Attention mechanisms allow modelling dependencies regardless of distance.",
            "page": 2,
        },
        "solution": {
            "text": "The Transformer: a model architecture based entirely on self-attention.",
            "page": 3,
        },
        "dataset": {
            "text": "WMT 2014 English-German and English-French translation tasks.",
            "page": 5,
        },
        "methodology": {
            "text": "6-layer encoder-decoder, 8 attention heads, d_model=512, trained on 8×P100 GPUs.",
            "page": 4,
        },
        "metrics": {"text": "BLEU score on held-out test sets.", "page": 6},
        "key_results": {
            "text": "28.4 BLEU on EN-DE, surpassing all prior single models.",
            "page": 7,
        },
        "limitations": {
            "text": "Performance on very long sequences not fully explored.",
            "page": 8,
        },
    }

    sample_findings = [
        {
            "claim": "Transformer achieves 28.4 BLEU on WMT 2014 English-to-German, outperforming existing models by over 2.0 BLEU.",
            "evidence": "Table 2: 28.4 BLEU vs 26.3 BLEU for previous best ensemble.",
            "page": 7,
        },
        {
            "claim": "Training time is reduced by an order of magnitude compared to recurrent or convolutional models.",
            "evidence": "Trained for 3.5 days on 8 P100 GPUs.",
            "page": 7,
        },
    ]

    try:
        cards = generate_flashcards(sample_understanding, sample_findings)
    except llm_client.LLMOutputError as exc:
        print(f"LLMOutputError: {exc}")
        sys.exit(1)

    print(f"Generated {len(cards)} flashcards:\n")
    for i, card in enumerate(cards, 1):
        print(f"[{i}] Q: {card['question']}")
        print(f"    A: {card['answer']}\n")

    csv_output = export_flashcards_csv(cards)
    print("CSV Export:\n")
    print(csv_output)
