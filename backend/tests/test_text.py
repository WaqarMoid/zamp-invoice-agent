from app.rules.text import (
    desc_similarity,
    normalize_invoice_number,
    normalize_po_number,
)


def test_invoice_number_normalization_doc_examples():
    # 5 examples from doc 07 §7.4.0
    assert normalize_invoice_number("BIS-INV-2026-0089") == "BIS-INV-26-89"
    assert normalize_invoice_number("BIS/INV/26/89") == "BIS-INV-26-89"
    assert normalize_invoice_number("SPS/26-27/0512") == "SPS-26-27-512"
    assert normalize_invoice_number("DCC/2627/0788") == "DCC-2627-788"
    assert normalize_invoice_number("INV0045") == "INV-45"


def test_po_number_normalization():
    # PO normalization examples from doc 07 §7.4.0
    assert normalize_po_number("PO 2026/412") == "PO-26-412"
    assert normalize_po_number("po-2026-0412") == "PO-26-412"
    assert normalize_po_number("PO#2026-0412") == "PO-26-412"


def test_desc_similarity():
    score = desc_similarity(
        "5-ply corrugated box 18x12x12 in",
        "Corrugated Box 5 Ply (18x12x12 inch)",
    )
    assert score >= 0.75, f"Expected similarity >= 0.75, got {score}"
