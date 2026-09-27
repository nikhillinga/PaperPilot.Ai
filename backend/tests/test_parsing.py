import pytest
from unittest.mock import MagicMock, patch

from app.parsing import (
    _find_references_start,
    extract_pages,
    extract_metadata,
)


def test_find_references_start():
    # References at line 0
    text1 = "References\n[1] Author, Title, 2020\n[2] Another Author, 2021"
    assert _find_references_start(text1) == 0

    # References mid-page at line 3
    text2 = "Line 0: Methods\nLine 1: Discussion\nLine 2: Acknowledgements\nReferences\n[1] Paper"
    assert _find_references_start(text2) == 3

    # Numbered and variant references
    text3 = "Discussion\n8. References\n[1] Paper"
    assert _find_references_start(text3) == 1

    text4 = "Discussion\nBibliography:\n[1] Paper"
    assert _find_references_start(text4) == 1

    # Not references
    text5 = "This is a regular paper page without any bibliography."
    assert _find_references_start(text5) is None


def test_extract_pages_mid_page_reference_truncation():
    # Mock fitz document with 3 pages
    # Page 1: normal
    # Page 2: Methods, Acknowledgements, and at line 2: References
    # Page 3: purely references (should be skipped completely)
    page1_text = "Page 1 intro content.\n" + ("More content line.\n" * 10)
    page2_text = "Line 0: Methods\nLine 1: Acknowledgements\nReferences\n[1] Ref 1\n[2] Ref 2"
    page3_text = "[3] Ref 3\n[4] Ref 4"

    mock_doc = MagicMock()
    mock_doc.page_count = 3
    mock_p1 = MagicMock()
    mock_p1.get_text.return_value = page1_text
    mock_p2 = MagicMock()
    mock_p2.get_text.return_value = page2_text
    mock_p3 = MagicMock()
    mock_p3.get_text.return_value = page3_text

    mock_doc.__getitem__.side_effect = [mock_p1, mock_p2, mock_p3]

    with patch("fitz.open", return_value=mock_doc):
        pages = extract_pages("dummy.pdf")

        # Page 1 and Page 2 should be included, Page 3 should NOT
        assert len(pages) == 2
        assert pages[0]["page_number"] == 1
        assert "Page 1 intro content." in pages[0]["text"]

        assert pages[1]["page_number"] == 2
        assert "Line 0: Methods" in pages[1]["text"]
        assert "Line 1: Acknowledgements" in pages[1]["text"]
        # References and citations must be truncated
        assert "References" not in pages[1]["text"]
        assert "[1] Ref 1" not in pages[1]["text"]


def test_extract_pages_uses_sort_true():
    mock_doc = MagicMock()
    mock_doc.page_count = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Content " * 50
    mock_doc.__getitem__.return_value = mock_page

    with patch("fitz.open", return_value=mock_doc):
        extract_pages("dummy.pdf")
        mock_page.get_text.assert_called_with("text", sort=True)


def test_extract_metadata_suspect_title_and_author():
    mock_doc = MagicMock()
    mock_doc.page_count = 1
    # Cairo as lowercase single-word author, trailing colon in title
    mock_doc.metadata = {
        "title": "Sebuah Kajian Pustaka:",
        "author": "cairo",
    }
    mock_page = MagicMock()
    mock_page.get_text.return_value = {
        "blocks": [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {"size": 24.0, "text": "Real Deep Learning Paper Title"}
                        ]
                    }
                ],
            }
        ]
    }
    mock_doc.__getitem__.return_value = mock_page

    with patch("fitz.open", return_value=mock_doc):
        meta = extract_metadata("dummy.pdf")
        # Title ending in ':' falls back to largest span
        assert meta["title"] == "Real Deep Learning Paper Title"
        # Author 'cairo' falls back to Unknown
        assert meta["authors"] == "Unknown"


def test_extract_metadata_short_title_falls_back():
    mock_doc = MagicMock()
    mock_doc.page_count = 1
    mock_doc.metadata = {
        "title": "Short Title",  # 11 chars < 15
        "author": "Alice Smith",
    }
    mock_page = MagicMock()
    mock_page.get_text.return_value = {
        "blocks": [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {"size": 20.0, "text": "Comprehensive Study on Machine Learning"}
                        ]
                    }
                ],
            }
        ]
    }
    mock_doc.__getitem__.return_value = mock_page

    with patch("fitz.open", return_value=mock_doc):
        meta = extract_metadata("dummy.pdf")
        assert meta["title"] == "Comprehensive Study on Machine Learning"
        assert meta["authors"] == "Alice Smith"


def test_extract_metadata_valid_metadata_kept():
    mock_doc = MagicMock()
    mock_doc.page_count = 1
    mock_doc.metadata = {
        "title": "Attention Is All You Need",
        "author": "Ashish Vaswani, Noam Shazeer",
    }
    mock_doc.__getitem__.return_value = MagicMock()

    with patch("fitz.open", return_value=mock_doc):
        meta = extract_metadata("dummy.pdf")
        assert meta["title"] == "Attention Is All You Need"
        assert meta["authors"] == "Ashish Vaswani, Noam Shazeer"
