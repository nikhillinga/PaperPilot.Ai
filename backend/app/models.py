"""
models.py — SQLModel database models for PaperPilot.

Defines Paper (metadata and pipeline execution status) and PaperData
(stores parsed pipeline artifacts serialized as JSON strings).
"""

from __future__ import annotations

from datetime import datetime
from sqlmodel import Column, DateTime, Field, SQLModel


class Paper(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str = Field(default="")
    authors: str = Field(default="")
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime),
    )
    status: str = Field(default="processing")  # "processing" | "ready" | "failed"
    error_message: str | None = Field(default=None)


class PaperData(SQLModel, table=True):
    paper_id: str = Field(primary_key=True, foreign_key="paper.id")
    understanding_json: str
    formulas_json: str
    findings_json: str
    viva_json: str
    flashcards_json: str
