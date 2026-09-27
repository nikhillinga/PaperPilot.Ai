## PaperPilot — AI Research Paper Study & Viva-Prep Agent

### What This Is
PaperPilot is a weekend-built system that turns a research paper PDF into a source-grounded study kit — structured understanding, formula explanations, key findings, revision notes, tiered viva questions, and exportable flashcards. Every generated fact links back to the page it came from, giving students and researchers an academically rigorous, hallucination-free preparation companion for examinations and thesis defenses.

---

### Architecture

```
                  ┌───────────────────────────────┐
                  │      Uploaded Research PDF     │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │    PDF Parser (PyMuPDF)       │
                  │ - Strips Running Headers/Footers│
                  │ - Truncates at References     │
                  └───────────────┬───────────────┘
                                  │ Page texts & metadata
                                  ▼
                  ┌───────────────────────────────┐
                  │     Section Detector          │
                  │ (Abstract, Intro, Method...)  │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Understanding   │    │Formula Extractor │    │ Finding Extractor│
│      Agent       │    │  (Regex Filter + │    │  (Quantitative & │
│ (8 Core Facets)  │    │    Context LLM)  │    │    Baselines)    │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
┌─────────────────────────────────┐             ┌──────────────────┐
│   Tiered Viva Defense Agent     │             │  Flashcards &    │
│ (Basic → Intermediate →         │             │  Revision Notes  │
│  Advanced → Research-Level)     │             │  Generators      │
└────────────────┬────────────────┘             └────────┬─────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │         FastAPI Backend             │
                  │   SQLite / SQLModel Persistence     │
                  │  Markdown / JSON / CSV Exporters    │
                  └──────────────────┬──────────────────┘
                                     │ HTTP / REST
                                     ▼
                  ┌─────────────────────────────────────┐
                  │     Next.js 14 App Router UI        │
                  │ TypeScript + Tailwind CSS Dashboard │
                  └─────────────────────────────────────┘
```

---

### Tech Stack

| Component | Tool / Technology |
| :--- | :--- |
| **Backend API** | FastAPI, Uvicorn, Python 3.11 |
| **Database & ORM** | SQLite, SQLModel |
| **PDF Extraction** | PyMuPDF (`fitz`) |
| **LLM Orchestration** | Custom Multi-Provider Client (Anthropic, OpenAI, OpenRouter) |
| **Testing** | Pytest, HTTPX |
| **Frontend Framework** | Next.js 14 (App Router), React 18 |
| **Frontend Language** | TypeScript |
| **Styling** | Tailwind CSS |
| **Markdown Rendering** | Marked |

---

### Setup

#### 1. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY or OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

#### 3. Open the app
Navigate to [http://localhost:3000](http://localhost:3000) in your browser.

---

### API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/papers` | Upload a multipart PDF, store the file, run the synchronous analysis pipeline, and return the paper record. |
| `GET` | `/papers/{paper_id}` | Fetch paper metadata and combined extracted artifacts (understanding, formulas, findings, viva, flashcards) when ready. |
| `GET` | `/papers/{paper_id}/notes` | Generate and stream full structured Markdown revision notes (`text/markdown`). |
| `GET` | `/papers/{paper_id}/viva` | Retrieve oral defense (viva voce) questions categorized across 4 difficulty tiers. |
| `GET` | `/papers/{paper_id}/flashcards.csv` | Export active-recall flashcards as an Anki-compatible CSV attachment (`text/csv`). |
| `GET` | `/health` | API health check status endpoint (`{"status": "ok"}`). |

---

### What Makes This Different From "Chat With Your PDF"

Standard "Chat with your PDF" tools rely on freeform retrieval-augmented generation (RAG) where users must already know what questions to ask. More critically, chat interfaces frequently hallucinate subtle numerical values, misattribute ablation results, or blend citations across distinct experiments — fatal flaws when preparing for an academic oral examination (*viva voce*).

In a defense setting, examiners do not accept loose summaries; they challenge specific claims, mathematical derivations, baseline improvements, and failure modes, asking: *"Where exactly is that demonstrated in the paper?"*

PaperPilot is engineered from the ground up for academic rigor:
1. **Deterministic Page-Level Grounding**: Every extracted concept, empirical finding, and formula is explicitly mapped to its physical page number (`p.N`).
2. **Structured Study Dossier**: Instead of an open chatbox, PaperPilot proactively extracts the eight core dimensions of academic work (problem, motivation, method, dataset, methodology, metrics, key results, limitations).
3. **Examiner-Grade Viva Simulation**: Generates four tiers of defense questions ranging from basic terminology to edge-case stress tests, accompanied by model answers.

---

### Known Limitations

- **Text-based PDFs only**: Scanned papers without embedded OCR layers are rejected (`SCANNED_OR_UNREADABLE_PDF`).
- **Best on papers under ~40 pages**: Context window limits and token caps are optimized for conference papers and standard journal articles.
- **Equations rendered as raster images**: Formulas embedded purely as bitmap graphics rather than text/vector math may not be extractable.
- **Single paper at a time**: Multi-paper comparative synthesis or cross-paper citation graphs are not supported in this version.

---

### Project Structure

```
PaperPilot.AI/
├── .env.example
├── .gitignore
├── README.md
├── decisions.md
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── findings.py
│   │   ├── flashcards.py
│   │   ├── formulas.py
│   │   ├── llm_client.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── notes.py
│   │   ├── parsing.py
│   │   ├── prompts.py
│   │   ├── sections.py
│   │   ├── understanding.py
│   │   └── viva.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_findings.py
│   │   ├── test_flashcards.py
│   │   ├── test_formulas.py
│   │   ├── test_llm_prompts.py
│   │   ├── test_notes.py
│   │   ├── test_parsing.py
│   │   ├── test_understanding.py
│   │   └── test_viva.py
│   └── uploads/
│       └── .gitkeep
├── frontend/
│   ├── .env.local.example
│   ├── next.config.mjs
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── app/
│       ├── globals.css
│       ├── layout.tsx
│       ├── page.tsx
│       ├── components/
│       │   ├── CitationBadge.tsx
│       │   ├── FindingCard.tsx
│       │   ├── FlashcardDeck.tsx
│       │   ├── FormulaCard.tsx
│       │   ├── UploadForm.tsx
│       │   └── VivaQuestionAccordion.tsx
│       ├── lib/
│       │   └── api.ts
│       └── paper/
│           └── [id]/
│               └── page.tsx
└── scripts/
    └── verify_pipeline.py
```

---

### Key Design Decisions

- **Page-Level Source Grounding**: Every extracted claim, formula, and finding links back to its exact source page (or `null`), ensuring academic defensibility and zero-hallucination tolerance for viva defense.
- **Automated References Truncation**: Downstream extraction stops before the References/Bibliography section, saving 20–40% token overhead and preventing citation clutter from polluting LLM context.
- **Frequency-Based Header/Footer Stripping**: Running headers and footers appearing across 3+ pages are automatically detected and pruned to preserve clean sentence and equation flow.
- **Two-Phase Heuristic Formula Filtering**: Local regex scans candidate pages for math symbols before calling the LLM, avoiding costly token calls on papers without equations.
- **Asymmetric Error Decoupling**: Non-critical steps (formulas, findings) fail soft to empty lists, whereas core comprehension (understanding, viva questions) fails hard to maintain study kit integrity.
- **Serialized JSON Persistence**: Database schema uses flat JSON columns in SQLite (`PaperData`) to maximize weekend iteration velocity without compromising query performance or export fidelity.

---

### V2 Roadmap

- **Optical Character Recognition (OCR)**: Integrate PaddleOCR or Tesseract fallback for scanned documents, legacy papers, and double-column archival PDFs.
- **Multi-Paper Comparative Synthesis**: Cross-paper literature matrix comparing methodology, datasets, and empirical results across multiple manuscripts.
- **Interactive LaTeX / MathJax Rendering**: Rich mathematical typography with interactive symbol inspection and step-by-step equation derivation breakdowns.
- **Native Anki Package (`.apkg`) & Notion/Obsidian Sync**: Direct export to Anki deck files with custom tags, alongside one-click export to personal knowledge bases.
- **Interactive Voice Viva Simulation**: Speech-to-text audio mode simulating an examination room with an AI panel questioning assumptions in real-time.
- **Side-by-Side Manuscript Highlighting**: In-browser dual-pane PDF viewer with bi-directional navigation between generated notes and exact highlighted coordinates on the PDF page.
