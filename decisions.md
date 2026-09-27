# Architecture & Design Decisions

### 1. Mandatory Page-Level Source Grounding
- **Decision**: Every extracted understanding field, empirical finding, and formula must retain a `page` number attribute pointing directly to where it originates in the PDF.
- **Rationale**: Viva voce defense requires students to defend assertions with exact page citations. Hallucinations or ungrounded facts can disqualify a student in an academic defense. If a fact cannot be linked to a specific page, `page` is set to `null` rather than guessing.

### 2. Truncation at References & Bibliography
- **Decision**: Page parsing automatically detects the start of the References / Bibliography section and truncates downstream text extraction at that boundary.
- **Rationale**: Academic bibliographies consume 20–40% of a paper's token budget and introduce noise (author names, paper titles) that can pollute LLM section detection, understanding extraction, and finding summaries.

### 3. Running Header and Footer Stripping via Repetition Heuristics
- **Decision**: Lines that repeat identically across 3 or more pages are identified as running headers/footers (journal names, conference headers, authors) and stripped from the body text.
- **Rationale**: Headers breaking in the middle of sentences or equations disrupt LLM context and paragraph flow. Frequency-based detection works across varying publication formats (ACM, IEEE, NeurIPS, Springer) without hardcoded templates.

### 4. Two-Phase Heuristic Candidate Filtering for Formula Extraction
- **Decision**: Formula extraction first runs a local regex heuristic scanning for mathematical symbols (`=`, `\Sigma`, `\int`, `\le`, `\ge`, Greek letters, subscripts) across pages. Only candidate pages (and their immediate preceding context page) are sent to the LLM.
- **Rationale**: Many empirical or qualitative papers contain zero formulas. Sending the entire document to the LLM for formula extraction wastes API latency, cost, and token limits.

### 5. Asymmetric Error Handling Across Pipeline Steps
- **Decision**: Softer steps (formulas, empirical findings) degrade gracefully into empty arrays if an LLM error occurs. In contrast, core comprehension steps (understanding, viva defense questions) raise `LLMOutputError` and fail hard.
- **Rationale**: A study kit without formulas is still useful if the paper has no math, but a study kit without structured understanding or viva defense preparation fails its fundamental purpose.

### 6. Serialized JSON Column Persistence in SQLite
- **Decision**: Store structured extraction outputs as `*_json` string columns in a dedicated `PaperData` table rather than creating dozens of relational tables for nested items.
- **Rationale**: For a weekend-scoped MVP, serialized JSON guarantees high development velocity, eliminates complex database migrations, and allows instant serialization/deserialization to and from FastAPI responses.
