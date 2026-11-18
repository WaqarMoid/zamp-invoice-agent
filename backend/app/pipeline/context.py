from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import Document, PurchaseOrder, Run, Vendor
from app.schemas import CheckResult, ExtractedInvoice, NormalizedInvoice, NormalizedLine


@dataclass
class RunContext:
    run_id: str
    session: Session
    run: Run
    document: Document
    extractor: Any = None  # Extractor protocol or None (uses default GeminiExtractor)
    use_cache: bool = True

    # Dynamic stage data populated during pipeline execution
    stage_outputs: dict[str, Any] = field(default_factory=dict)
    all_checks: list[CheckResult] = field(default_factory=list)

    # Specific stage products
    has_text_layer: bool = True
    extraction: ExtractedInvoice | None = None
    extraction_method: str | None = None
    normalized: NormalizedInvoice | None = None
    vendor: Vendor | None = None
    vendor_match_method: str = "none"
    po: PurchaseOrder | None = None
    po_method: str = "none"
    matched_pairs: list[dict[str, Any]] = field(default_factory=list)
    unmatched_lines: list[NormalizedLine] = field(default_factory=list)
