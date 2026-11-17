from pathlib import Path

from app.extraction.heuristic import extract_heuristic_from_pdf
from app.extraction.render import render_pdf_to_images
from app.extraction.text_layer import extract_text_from_pdf_bytes

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_text_layer_extraction_f01():
    pdf_path = FIXTURES_DIR / "F01_happy_path_sharma.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    text, has_text_layer, warnings = extract_text_from_pdf_bytes(pdf_bytes)
    assert has_text_layer is True
    assert len(text) >= 40
    assert "Sharma Packaging" in text
    assert "1,29,682.00" in text


def test_text_layer_extraction_f03_scanned():
    pdf_path = FIXTURES_DIR / "F03_scanned_implied_po_greenleaf.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    text, has_text_layer, warnings = extract_text_from_pdf_bytes(pdf_bytes)
    assert has_text_layer is False
    assert len(text.strip()) == 0


def test_render_pdf_to_images():
    pdf_path = FIXTURES_DIR / "F01_happy_path_sharma.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    images = render_pdf_to_images(pdf_bytes, dpi=100)
    assert len(images) == 1
    assert images[0].startswith(b"\x89PNG\r\n\x1a\n")


def test_heuristic_fallback_extraction():
    pdf_path = FIXTURES_DIR / "F01_happy_path_sharma.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    ext = extract_heuristic_from_pdf(pdf_bytes)
    assert ext.vendor_gstin == "29AAGCS7712R1ZI"
    assert ext.buyer_gstin == "29AAACK4521M1ZD"
    assert ext.invoice_number == "SPS/26-27/0512"
    assert ext.grand_total == 129682.00
    assert ext.field_confidence["grand_total"] == 0.60
