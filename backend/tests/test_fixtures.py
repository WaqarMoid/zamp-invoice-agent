import json
from decimal import Decimal
from pathlib import Path

import pdfplumber
import pymupdf

from app.rules.money import parse_money
from app.schemas import ExtractedInvoice
from scripts.generate_fixtures import format_indian_number

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "seed_data"

with open(SEED_DATA_DIR / "fixtures.json", encoding="utf-8") as f:
    FIXTURES_SPECS = json.load(f)


def test_nine_pdfs_exist():
    assert len(FIXTURES_SPECS) == 9
    for fix in FIXTURES_SPECS:
        pdf_path = FIXTURES_DIR / fix["filename"]
        assert pdf_path.exists(), f"Missing PDF fixture: {fix['filename']}"


def test_f03_has_no_text_layer():
    f03 = next(f for f in FIXTURES_SPECS if f["fixture_id"] == "F03")
    pdf_path = FIXTURES_DIR / f03["filename"]
    doc = pymupdf.open(str(pdf_path))
    page = doc[0]
    text = page.get_text().strip()
    doc.close()
    assert len(text) == 0, f"Expected F03 to have 0 text chars, found {len(text)}"


def test_non_scanned_pdfs_have_text_and_correct_totals():
    for fix in FIXTURES_SPECS:
        fid = fix["fixture_id"]
        if fix.get("scanned"):
            continue
        pdf_path = FIXTURES_DIR / fix["filename"]
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "".join(page.extract_text() or "" for page in pdf.pages)
            assert len(full_text) >= 40, f"Fixture {fid} text too short: {len(full_text)}"

            # Verify printed grand total is in text
            gt = fix["printed_totals"]["grand_total"]
            dec_gt = parse_money(gt)
            fmt_gt = format_indian_number(dec_gt)
            assert fmt_gt in full_text, f"Grand total {fmt_gt} not found in {fid} text"


def test_golden_json_valid_and_complete():
    for fix in FIXTURES_SPECS:
        fid = fix["fixture_id"]
        golden_file = GOLDEN_DIR / f"{fid}.json"
        assert golden_file.exists(), f"Missing golden JSON for {fid}"

        with open(golden_file, encoding="utf-8") as f:
            data = json.load(f)

        ext = ExtractedInvoice.model_validate(data)
        assert ext.field_confidence["grand_total"] == 0.99

        if fid == "F09":
            assert ext.invoice_number is None
            assert ext.invoice_date is None
        elif fid == "F03":
            assert ext.po_number is None
            assert ext.po_reference_text == "As per your order dated 02-Nov-2026"
        elif fid == "F07":
            assert ext.amounts_include_tax is True
            assert ext.grand_total == Decimal("45675.00")
        else:
            assert ext.invoice_number == fix["invoice_number"]
            assert ext.grand_total == Decimal(str(fix["printed_totals"]["grand_total"]))
