"""
prompts.py — LLM prompt construction for PaperPilot.

Contains prompt templates for extracting structured paper understanding,
formulas, key empirical findings, viva defense questions, and study flashcards.
All prompts enforce strict factual grounding against the provided paper text
and output valid JSON schemas.
"""

from __future__ import annotations

SHARED_GROUNDING_RULES = """
You are analyzing a research paper. Follow these rules strictly:
1. Only state facts that are explicitly present in the provided text. Do
   not use outside knowledge about this topic or paper.
2. The provided text contains [PAGE n] markers. For every fact you extract,
   identify which page it came from and include that page number.
3. If information for a requested field is genuinely not present in the
   text, use the value "Not specified in the provided text" rather than
   guessing.
4. Return ONLY valid JSON matching the schema given. No markdown code
   fences, no preamble, no explanation outside the JSON.
"""


def build_understanding_prompt(sections_text: str) -> tuple[str, str]:
    """Build system and user prompts to extract structured understanding of a paper.

    Extracts: problem, motivation, solution, dataset, methodology, metrics,
    key_results, limitations — each as {"text": str, "page": int | None}.
    """
    system_prompt = f"""{SHARED_GROUNDING_RULES}

Extract a comprehensive, structured understanding of the research paper across the following 8 fields:
- problem: The core problem, challenge, or task addressed.
- motivation: Why this problem is important and why prior approaches fall short.
- solution: The key proposed approach, system, algorithm, or model introduced.
- dataset: The benchmark datasets, corpora, or environments used.
- methodology: The technical implementation details, architecture, and training/evaluation setup.
- metrics: The specific evaluation metrics used (e.g. accuracy, BLEU, F1 score, latency).
- key_results: The primary experimental outcomes, benchmark numbers, or improvements.
- limitations: Acknowledged limitations, failure cases, or scope bounds.

Return a JSON object with this exact structure:
{{
  "problem": {{"text": "...", "page": 1}},
  "motivation": {{"text": "...", "page": 1}},
  "solution": {{"text": "...", "page": 1}},
  "dataset": {{"text": "...", "page": 1}},
  "methodology": {{"text": "...", "page": 1}},
  "metrics": {{"text": "...", "page": 1}},
  "key_results": {{"text": "...", "page": 1}},
  "limitations": {{"text": "...", "page": null}}
}}

For each field:
- "text": A concise factual summary directly grounded in the paper text.
- "page": The integer page number (from the preceding [PAGE n] marker) where the evidence appears. If the field is not present in the text, use "Not specified in the provided text" for "text" and null for "page".
"""
    user_prompt = sections_text
    return system_prompt, user_prompt


def build_formula_prompt(candidate_pages_text: str) -> tuple[str, str]:
    """Build system and user prompts to extract equations and formulas.

    Extracts a JSON array of:
    {"name": str, "equation_raw": str|null, "meaning": str,
     "variables": [{"symbol": str, "meaning": str}], "page": int}
    """
    system_prompt = f"""{SHARED_GROUNDING_RULES}

Identify and extract all significant mathematical equations, loss functions, objective functions, or formulas in the provided text.

Return a JSON array of objects:
[
  {{
    "name": "Descriptive name of the equation (e.g., Scaled Dot-Product Attention, Objective Function)",
    "equation_raw": "The raw equation text or LaTeX expression, or null",
    "meaning": "What this equation computes and how it functions in the paper",
    "variables": [
      {{"symbol": "x", "meaning": "Input representation"}},
      {{"symbol": "W", "meaning": "Weight matrix"}}
    ],
    "page": 1
  }}
]

Instructions:
- If a formula is referenced but the actual equation text is garbled or missing, set equation_raw to null and meaning to "Formula detected on this page but could not be extracted as text." — do NOT invent an equation.
- "page" must be the integer page number where the formula appears.
- If no equations are found in the text, return an empty array [].
"""
    user_prompt = candidate_pages_text
    return system_prompt, user_prompt


def build_findings_prompt(sections_text: str) -> tuple[str, str]:
    """Build system and user prompts to extract 3-6 key empirical findings.

    Returns a JSON array of {"finding": str, "page": int}.
    """
    system_prompt = f"""{SHARED_GROUNDING_RULES}

Extract 3 to 6 specific, empirical findings from the paper.

Focus on:
- Quantitative, numeric results (e.g., accuracy, speedup, error reduction percentages, benchmark scores).
- Direct comparisons against baselines or prior state-of-the-art.
- Major takeaways supported by the experimental data.

Return a JSON array of 3 to 6 objects:
[
  {{
    "finding": "Specific, numeric-where-possible finding statement describing the result and baseline comparison.",
    "page": 1
  }}
]

Each "page" must be the integer page number where the finding is reported.
"""
    user_prompt = sections_text
    return system_prompt, user_prompt


def build_viva_prompt(understanding_json: str, questions_per_tier: int) -> tuple[str, str]:
    """Build system and user prompts to generate oral defense (viva voce) questions.

    Generates questions_per_tier questions for tiers:
    ["basic", "intermediate", "advanced", "research_level"],
    each with a 2-4 sentence model_answer grounded in understanding_json.
    """
    system_prompt = f"""{SHARED_GROUNDING_RULES}

You are an academic examiner conducting an oral examination (viva voce) on a research paper.
Generate {questions_per_tier} questions for each of the following 4 tiers:
- "basic": Foundational concepts, problem definition, core terminology.
- "intermediate": Methodology details, dataset specifics, architecture choices.
- "advanced": Technical trade-offs, experimental nuances, failure modes, design justifications.
- "research_level": Critical critique, broader implications, unresolved limitations, future directions.

Requirements:
- Ground all questions and model answers in the provided understanding JSON (no page citation needed here — this is synthesis, not extraction).
- Each question must include a 2-4 sentence model_answer.
- Return a JSON array of objects with this schema:
[
  {{
    "tier": "basic",
    "question": "Clear examination question?",
    "model_answer": "A 2 to 4 sentence model answer explaining the key points."
  }}
]
"""
    user_prompt = understanding_json
    return system_prompt, user_prompt


def build_flashcards_prompt(understanding_json: str, findings_json: str, count: int) -> tuple[str, str]:
    """Build system and user prompts to generate flashcards.

    Generates `count` flashcard Q/A pairs testing understanding of the paper's
    problem, method, dataset, and results.
    """
    system_prompt = f"""{SHARED_GROUNDING_RULES}

Generate exactly {count} flashcard question-and-answer pairs testing understanding of the paper's problem, method, dataset, and results.

Requirements:
- Questions should test active recall of core concepts, architectural choices, and key empirical takeaways.
- Answers should be concise, factual, and informative (1-3 sentences).
- Ground all flashcards strictly in the provided understanding and findings.

Return a JSON array of exactly {count} objects:
[
  {{
    "question": "Focused question testing a core concept or finding?",
    "answer": "Concise, factual answer."
  }}
]
"""
    user_prompt = f"Paper Understanding:\n{understanding_json}\n\nKey Findings:\n{findings_json}"
    return system_prompt, user_prompt
