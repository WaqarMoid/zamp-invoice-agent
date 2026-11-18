import json
import logging
from decimal import Decimal
from pathlib import Path

from app.config import get_settings
from app.extraction.gemini import GeminiExtractor
from app.extraction.render import render_pdf_to_images
from app.extraction.text_layer import extract_text_from_pdf_bytes
from app.schemas import ExtractedInvoice

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_extraction")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = ROOT_DIR / "backend" / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
REPORTS_DIR = ROOT_DIR / "backend" / "reports"
SEED_DATA_DIR = ROOT_DIR / "backend" / "app" / "seed_data"


def compare_field(actual, expected) -> bool:
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
    if isinstance(expected, Decimal):
        try:
            return abs(Decimal(str(actual)) - expected) <= Decimal("1.00")
        except Exception:
            return False
    if isinstance(expected, bool):
        return actual == expected
    return str(actual).strip() == str(expected).strip()


def evaluate_fixture(extractor: GeminiExtractor, fix: dict) -> dict[str, bool]:
    fid = fix["fixture_id"]
    pdf_path = FIXTURES_DIR / fix["filename"]
    golden_path = GOLDEN_DIR / f"{fid}.json"

    with open(golden_path, encoding="utf-8") as f:
        golden_data = json.load(f)
    golden = ExtractedInvoice.model_validate(golden_data)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Route per doc 06 §6.2
    if fix.get("scanned"):
        images = render_pdf_to_images(pdf_bytes, dpi=200)
        extracted = extractor.extract_from_images(images)
    else:
        text, has_text, _ = extract_text_from_pdf_bytes(pdf_bytes)
        if has_text:
            extracted = extractor.extract_from_text(text)
        else:
            images = render_pdf_to_images(pdf_bytes, dpi=200)
            extracted = extractor.extract_from_images(images)

    results = {}
    results["vendor_gstin"] = compare_field(extracted.vendor_gstin, golden.vendor_gstin)
    results["buyer_gstin"] = compare_field(extracted.buyer_gstin, golden.buyer_gstin)
    results["invoice_number"] = compare_field(extracted.invoice_number, golden.invoice_number)
    results["invoice_date"] = compare_field(extracted.invoice_date, golden.invoice_date)
    results["po_number"] = compare_field(extracted.po_number, golden.po_number)
    results["amounts_include_tax"] = compare_field(extracted.amounts_include_tax, golden.amounts_include_tax)
    results["grand_total"] = compare_field(extracted.grand_total, golden.grand_total)
    results["total_tax"] = compare_field(extracted.total_tax, golden.total_tax)

    # Bank details comparison
    g_bank = golden.bank_details
    e_bank = extracted.bank_details
    if g_bank is None:
        results["bank_details"] = True
    elif e_bank is None:
        results["bank_details"] = False
    else:
        ifsc_ok = compare_field(e_bank.ifsc, g_bank.ifsc)
        acc_ok = compare_field(e_bank.account_number, g_bank.account_number)
        results["bank_details"] = ifsc_ok and acc_ok

    results["line_count"] = len(extracted.line_items) == len(golden.line_items)

    return results


def main():
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        print("\n" + "=" * 60)
        print("ERROR: GEMINI_API_KEY is not set.")
        print("Please add GEMINI_API_KEY to backend/.env and re-run.")
        print("=" * 60 + "\n")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEED_DATA_DIR / "fixtures.json", encoding="utf-8") as f:
        fixtures = json.load(f)

    model_id = settings.GEMINI_MODEL or "gemini-2.5-flash"
    extractor = GeminiExtractor(model=model_id, api_key=settings.GEMINI_API_KEY)

    logger.info("Evaluating extraction accuracy for F01..F09 using %s...", model_id)
    all_evals = {}
    total_checks = 0
    passed_checks = 0

    for fix in fixtures:
        fid = fix["fixture_id"]
        logger.info("Evaluating %s (%s)...", fid, fix["filename"])
        res = evaluate_fixture(extractor, fix)
        all_evals[fid] = res
        for field, ok in res.items():
            total_checks += 1
            if ok:
                passed_checks += 1

    accuracy_pct = (passed_checks / total_checks) * 100 if total_checks > 0 else 0.0

    # Build markdown report
    fields = [
        "vendor_gstin",
        "buyer_gstin",
        "invoice_number",
        "invoice_date",
        "po_number",
        "amounts_include_tax",
        "grand_total",
        "total_tax",
        "bank_details",
        "line_count",
    ]

    lines = [
        "# Extraction Accuracy Evaluation Report",
        "",
        f"- **Model:** `{model_id}`",
        f"- **Overall accuracy:** `{accuracy_pct:.1f}%` ({passed_checks}/{total_checks} checks passed)",
        "",
        "| Fixture | " + " | ".join(fields) + " | Score |",
        "|---|" + "|".join(["---" for _ in fields]) + "|---|",
    ]

    for fix in fixtures:
        fid = fix["fixture_id"]
        res = all_evals.get(fid, {})
        row = [fid]
        row_pass = 0
        for fld in fields:
            ok = res.get(fld, False)
            if ok:
                row.append("✓")
                row_pass += 1
            else:
                row.append("✗")
        score_str = f"{row_pass}/{len(fields)}"
        row.append(score_str)
        lines.append("| " + " | ".join(row) + " |")

    report_content = "\n".join(lines) + "\n"
    report_file = REPORTS_DIR / "extraction_eval.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print("\n" + report_content)
    logger.info("Report written to %s", report_file)


if __name__ == "__main__":
    main()
