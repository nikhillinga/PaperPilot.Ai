"""
test_api.py — Integration and unit tests for PaperPilot FastAPI endpoints, db, and models.
"""

import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app import db
from app.main import app
from app.models import Paper, PaperData


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, tmp_path):
    def get_session_override():
        return session

    app.dependency_overrides[db.get_session] = get_session_override
    with patch("app.config.UPLOAD_DIR", tmp_path):
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_non_pdf_rejected(client: TestClient):
    response = client.post(
        "/papers",
        files={"file": ("test.txt", b"plain text content", "text/plain")},
    )
    assert response.status_code == 400
    assert "application/pdf" in response.json()["detail"]


@patch("app.parsing.extract_pages")
@patch("app.parsing.extract_metadata")
@patch("app.sections.detect_sections")
@patch("app.understanding.generate_understanding")
@patch("app.formulas.extract_formulas")
@patch("app.findings.extract_findings")
@patch("app.viva.generate_viva_questions")
@patch("app.flashcards.generate_flashcards")
def test_upload_success(
    mock_flashcards,
    mock_viva,
    mock_findings,
    mock_formulas,
    mock_understanding,
    mock_sections,
    mock_metadata,
    mock_pages,
    client: TestClient,
    session: Session,
):
    mock_pages.return_value = [{"page_number": 1, "text": "Page content"}]
    mock_metadata.return_value = {
        "title": "Attention Is All You Need",
        "authors": "Vaswani et al.",
    }
    mock_sections.return_value = {"abstract": [{"page_number": 1, "text": "Abstract text"}]}
    mock_understanding.return_value = {
        "problem": {"text": "Recurrence is slow", "page": 1},
        "motivation": {"text": "Attention works better", "page": 1},
        "solution": {"text": "Transformer", "page": 1},
        "dataset": {"text": "WMT 2014", "page": 1},
        "methodology": {"text": "Multi-head attention", "page": 1},
        "metrics": {"text": "BLEU", "page": 1},
        "key_results": {"text": "28.4 BLEU", "page": 1},
        "limitations": {"text": "Long context", "page": 1},
    }
    mock_formulas.return_value = [
        {"name": "Attention", "formula": "softmax(QK^T / sqrt(d))V", "meaning": "Scaled dot product", "page": 1}
    ]
    mock_findings.return_value = [
        {"claim": "Transformer is fast", "evidence": "Table 1", "page": 1}
    ]
    mock_viva.return_value = [
        {"tier": "basic", "question": "What is self-attention?", "model_answer": "Attending to itself"}
    ]
    mock_flashcards.return_value = [
        {"question": "What is Transformer?", "answer": "An attention-based model"}
    ]

    pdf_bytes = b"%PDF-1.4 mock pdf data"
    response = client.post(
        "/papers",
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["title"] == "Attention Is All You Need"
    assert data["authors"] == "Vaswani et al."
    paper_id = data["id"]

    # Verify db records
    paper_in_db = session.get(Paper, paper_id)
    assert paper_in_db is not None
    assert paper_in_db.status == "ready"
    paper_data_in_db = session.get(PaperData, paper_id)
    assert paper_data_in_db is not None
    assert json.loads(paper_data_in_db.understanding_json)["solution"]["text"] == "Transformer"


@patch("app.parsing.extract_pages")
def test_upload_scanned_pdf_failure_returns_200(mock_pages, client: TestClient, session: Session):
    mock_pages.side_effect = ValueError("SCANNED_OR_UNREADABLE_PDF")

    pdf_bytes = b"%PDF-1.4 unreadable pdf"
    response = client.post(
        "/papers",
        files={"file": ("scanned.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "SCANNED_OR_UNREADABLE_PDF"

    paper_id = data["id"]
    paper_in_db = session.get(Paper, paper_id)
    assert paper_in_db is not None
    assert paper_in_db.status == "failed"
    assert paper_in_db.error_message == "SCANNED_OR_UNREADABLE_PDF"


def test_get_paper_not_found(client: TestClient):
    response = client.get("/papers/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Paper not found"


def test_get_paper_failed_omits_paper_data(client: TestClient, session: Session):
    paper = Paper(
        id="failed-paper",
        title="",
        authors="",
        status="failed",
        error_message="SCANNED_OR_UNREADABLE_PDF",
    )
    session.add(paper)
    session.commit()

    response = client.get("/papers/failed-paper")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "id": "failed-paper",
        "title": "",
        "authors": "",
        "status": "failed",
        "error_message": "SCANNED_OR_UNREADABLE_PDF",
    }
    assert "understanding" not in data


def test_get_paper_ready_includes_paper_data(client: TestClient, session: Session):
    paper = Paper(
        id="ready-paper",
        title="Sample Title",
        authors="Sample Author",
        status="ready",
        error_message=None,
    )
    paper_data = PaperData(
        paper_id="ready-paper",
        understanding_json=json.dumps({"problem": {"text": "A problem", "page": 1}}),
        formulas_json=json.dumps([{"name": "F1", "formula": "x=y", "meaning": "m", "page": 2}]),
        findings_json=json.dumps([{"claim": "C1", "evidence": "E1", "page": 3}]),
        viva_json=json.dumps([{"tier": "basic", "question": "Q1", "model_answer": "A1"}]),
        flashcards_json=json.dumps([{"question": "Q1", "answer": "A1"}]),
    )
    session.add(paper)
    session.add(paper_data)
    session.commit()

    response = client.get("/papers/ready-paper")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "ready-paper"
    assert data["status"] == "ready"
    assert data["understanding"] == {"problem": {"text": "A problem", "page": 1}}
    assert data["formulas"][0]["name"] == "F1"
    assert data["findings"][0]["claim"] == "C1"
    assert data["viva"][0]["question"] == "Q1"
    assert data["flashcards"][0]["answer"] == "A1"


def test_get_paper_notes(client: TestClient, session: Session):
    paper = Paper(
        id="notes-paper",
        title="Test Notes Title",
        authors="Author",
        status="ready",
    )
    paper_data = PaperData(
        paper_id="notes-paper",
        understanding_json=json.dumps({
            "problem": {"text": "Problem text", "page": 1},
            "motivation": {"text": "Motivation text", "page": 2},
            "solution": {"text": "Solution text", "page": 3},
            "dataset": {"text": "Dataset text", "page": 4},
            "methodology": {"text": "Methodology text", "page": 5},
            "metrics": {"text": "Metrics text", "page": 6},
            "key_results": {"text": "Results text", "page": 7},
            "limitations": {"text": "Limitations text", "page": 8},
        }),
        formulas_json=json.dumps([]),
        findings_json=json.dumps([]),
        viva_json=json.dumps([]),
        flashcards_json=json.dumps([]),
    )
    session.add(paper)
    session.add(paper_data)
    session.commit()

    # 404 for nonexistent
    res_404 = client.get("/papers/no-paper/notes")
    assert res_404.status_code == 404

    # 200 when ready
    res_200 = client.get("/papers/notes-paper/notes")
    assert res_200.status_code == 200
    assert "text/markdown" in res_200.headers["content-type"]
    assert "# Quick Revision Notes — Test Notes Title" in res_200.text

    # 409 when not ready
    paper.status = "processing"
    session.add(paper)
    session.commit()
    res_409 = client.get("/papers/notes-paper/notes")
    assert res_409.status_code == 409


def test_get_paper_viva(client: TestClient, session: Session):
    paper = Paper(
        id="viva-paper",
        title="Viva Paper",
        authors="Author",
        status="ready",
    )
    viva_list = [
        {"tier": "basic", "question": "Q1", "model_answer": "A1"},
        {"tier": "advanced", "question": "Q2", "model_answer": "A2"},
    ]
    paper_data = PaperData(
        paper_id="viva-paper",
        understanding_json="{}",
        formulas_json="[]",
        findings_json="[]",
        viva_json=json.dumps(viva_list),
        flashcards_json="[]",
    )
    session.add(paper)
    session.add(paper_data)
    session.commit()

    res = client.get("/papers/viva-paper/viva")
    assert res.status_code == 200
    assert res.json() == viva_list

    # 409 when failed
    paper.status = "failed"
    session.add(paper)
    session.commit()
    assert client.get("/papers/viva-paper/viva").status_code == 409


def test_get_paper_flashcards_csv(client: TestClient, session: Session):
    paper = Paper(
        id="fc-paper",
        title="Flashcards Paper",
        authors="Author",
        status="ready",
    )
    cards = [
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2, with comma", "answer": 'A2 "with quotes"'},
    ]
    paper_data = PaperData(
        paper_id="fc-paper",
        understanding_json="{}",
        formulas_json="[]",
        findings_json="[]",
        viva_json="[]",
        flashcards_json=json.dumps(cards),
    )
    session.add(paper)
    session.add(paper_data)
    session.commit()

    res = client.get("/papers/fc-paper/flashcards.csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert res.headers["content-disposition"] == 'attachment; filename="flashcards.csv"'
    assert '"question","answer"' in res.text
    assert '"Q2, with comma"' in res.text

    # 409 when processing
    paper.status = "processing"
    session.add(paper)
    session.commit()
    assert client.get("/papers/fc-paper/flashcards.csv").status_code == 409
