"""
main.py — FastAPI application and HTTP routes for PaperPilot.

Provides PDF upload and pipeline processing, as well as endpoints for
retrieving extracted papers, revision notes, viva questions, and flashcards CSV.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

try:
    from app import (
        config,
        db,
        findings,
        flashcards,
        formulas,
        notes,
        parsing,
        sections,
        understanding,
        viva,
    )
    from app.models import Paper, PaperData
except ImportError:
    import config
    import db
    import findings
    import flashcards
    import formulas
    import notes
    import parsing
    import sections
    import understanding
    import viva
    from models import Paper, PaperData

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and ensure upload directory exists."""
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    db.init_db()
    yield


app = FastAPI(title="PaperPilot API", lifespan=lifespan)

# ── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Endpoint ──────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# ── Papers Endpoints ─────────────────────────────────────────────────────────
@app.post("/papers", response_model=Paper)
def upload_paper(
    file: UploadFile = File(...),
    session: Session = Depends(db.get_session),
) -> Paper:
    """
    Accepts a multipart PDF upload, stores the file, and runs the extraction
    pipeline synchronously. Returns the Paper record with status 'ready' or 'failed'.
    """
    if not file.content_type or (
        file.content_type != "application/pdf"
        and not file.content_type.startswith("application/pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only application/pdf is accepted.",
        )

    paper_id = str(uuid.uuid4())
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    pdf_path = config.UPLOAD_DIR / f"{paper_id}.pdf"

    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.exception("Failed to write uploaded PDF to disk: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded PDF: {exc}",
        )

    paper = Paper(
        id=paper_id,
        title="",
        authors="",
        status="processing",
        error_message=None,
    )
    session.add(paper)
    session.commit()
    session.refresh(paper)

    try:
        pages = parsing.extract_pages(pdf_path)
        metadata = parsing.extract_metadata(pdf_path)
        section_map = sections.detect_sections(pages)
        understanding_data = understanding.generate_understanding(section_map)
        formulas_result = formulas.extract_formulas(pages)
        findings_result = findings.extract_findings(section_map)
        viva_result = viva.generate_viva_questions(understanding_data)
        flashcards_result = flashcards.generate_flashcards(
            understanding_data, findings_result
        )

        paper.title = metadata.get("title", "") or ""
        paper.authors = metadata.get("authors", "") or ""
        paper.status = "ready"
        paper.error_message = None

        paper_data = PaperData(
            paper_id=paper.id,
            understanding_json=json.dumps(understanding_data),
            formulas_json=json.dumps(formulas_result),
            findings_json=json.dumps(findings_result),
            viva_json=json.dumps(viva_result),
            flashcards_json=json.dumps(flashcards_result),
        )
        session.add(paper)
        session.add(paper_data)
        session.commit()
        session.refresh(paper)
    except Exception as exc:
        logger.exception("Pipeline failed for paper %s: %s", paper_id, exc)
        session.rollback()
        paper = session.get(Paper, paper_id) or paper
        paper.status = "failed"
        paper.error_message = str(exc)
        session.add(paper)
        session.commit()
        session.refresh(paper)

    return paper


@app.get("/papers/{paper_id}")
def get_paper(
    paper_id: str,
    session: Session = Depends(db.get_session),
) -> dict[str, Any]:
    """
    Returns paper details. When status is 'ready', includes parsed pipeline
    outputs (understanding, formulas, findings, viva, flashcards).
    """
    paper = session.get(Paper, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    response: dict[str, Any] = {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "status": paper.status,
        "error_message": paper.error_message,
    }

    if paper.status == "ready":
        paper_data = session.get(PaperData, paper_id)
        if paper_data:
            response.update(
                {
                    "understanding": json.loads(paper_data.understanding_json),
                    "formulas": json.loads(paper_data.formulas_json),
                    "findings": json.loads(paper_data.findings_json),
                    "viva": json.loads(paper_data.viva_json),
                    "flashcards": json.loads(paper_data.flashcards_json),
                }
            )

    return response


@app.get("/papers/{paper_id}/notes", response_class=PlainTextResponse)
def get_paper_notes(
    paper_id: str,
    session: Session = Depends(db.get_session),
) -> PlainTextResponse:
    """
    Generates and returns formatted Markdown revision notes for a ready paper.
    """
    paper = session.get(Paper, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )
    if paper.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper is not ready (status: {paper.status})",
        )

    paper_data = session.get(PaperData, paper_id)
    if not paper_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper data not found",
        )

    understanding_data = json.loads(paper_data.understanding_json)
    formulas_data = json.loads(paper_data.formulas_json)
    findings_data = json.loads(paper_data.findings_json)

    markdown_notes = notes.generate_notes(
        paper.title,
        understanding_data,
        formulas_data,
        findings_data,
    )
    return PlainTextResponse(content=markdown_notes, media_type="text/markdown")


@app.get("/papers/{paper_id}/viva")
def get_paper_viva(
    paper_id: str,
    session: Session = Depends(db.get_session),
) -> list[dict[str, Any]]:
    """
    Returns the generated viva questions array for a ready paper.
    """
    paper = session.get(Paper, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )
    if paper.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper is not ready (status: {paper.status})",
        )

    paper_data = session.get(PaperData, paper_id)
    if not paper_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper data not found",
        )

    return json.loads(paper_data.viva_json)


@app.get("/papers/{paper_id}/flashcards.csv", response_class=PlainTextResponse)
def get_paper_flashcards_csv(
    paper_id: str,
    session: Session = Depends(db.get_session),
) -> PlainTextResponse:
    """
    Exports flashcards as a downloadable CSV for Anki import.
    """
    paper = session.get(Paper, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )
    if paper.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper is not ready (status: {paper.status})",
        )

    paper_data = session.get(PaperData, paper_id)
    if not paper_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper data not found",
        )

    flashcards_data = json.loads(paper_data.flashcards_json)
    csv_content = flashcards.export_flashcards_csv(flashcards_data)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="flashcards.csv"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
