"""
Check names and message templates per docs/07_PIPELINE_AND_RULES.md §7.3.
"""

CHECK_NAMES: dict[str, str] = {
    "C01": "Required fields",
    "C02": "Extraction confidence",
    "C03": "Billed to us",
    "C04": "Arithmetic",
    "C05": "Vendor status",
    "C06": "Vendor identity",
    "C07": "Bank details",
    "C08": "Invoice date",
    "C09": "Duplicate check",
    "C10": "PO identified",
    "C11": "PO belongs to vendor",
    "C12": "PO status",
    "C13": "Line matching",
    "C14": "Price variance",
    "C15": "Quantity vs unbilled",
    "C16": "Tax",
    "C17": "Currency",
    "C20": "PO validity window",
    "C21": "Tax-inclusive pricing",
}

STAGE_KEYS: dict[str, str] = {
    "C01": "normalize",
    "C02": "normalize",
    "C03": "normalize",
    "C04": "normalize",
    "C08": "normalize",
    "C17": "normalize",
    "C21": "normalize",
    "C05": "vendor",
    "C06": "vendor",
    "C07": "vendor",
    "C09": "duplicates",
    "C10": "po_match",
    "C11": "po_match",
    "C12": "po_match",
    "C13": "po_match",
    "C20": "po_match",
    "C14": "reconcile",
    "C15": "reconcile",
    "C16": "reconcile",
}
