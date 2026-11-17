from datetime import UTC, date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(String(8), primary_key=True)  # e.g. V001
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    pan: Mapped[str] = mapped_column(String(10), nullable=False)
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ACTIVE | INACTIVE
    deactivated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_ifsc: Mapped[str] = mapped_column(String(11), nullable=False)
    bank_account_number: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_email: Mapped[str] = mapped_column(String(200), nullable=False)

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="vendor")
    ledger_entries: Mapped[list["InvoiceLedger"]] = relationship("InvoiceLedger", back_populates="vendor")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_number: Mapped[str] = mapped_column(String(20), primary_key=True)
    vendor_id: Mapped[str] = mapped_column(String(8), ForeignKey("vendors.vendor_id"), nullable=False)
    po_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # OPEN | CLOSED | CANCELLED
    po_number_norm: Mapped[str] = mapped_column(String(40), index=True, nullable=False)

    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="purchase_orders")
    lines: Mapped[list["POLine"]] = relationship(
        "POLine",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="POLine.line_no",
    )


class POLine(Base):
    __tablename__ = "po_lines"
    __table_args__ = (UniqueConstraint("po_number", "line_no", name="uq_po_line_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("purchase_orders.po_number"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hsn_sac: Mapped[str | None] = mapped_column(String(10), nullable=True)
    uom: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    has_text_layer: Mapped[bool] = mapped_column(Boolean, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    runs: Mapped[list["Run"]] = relationship("Run", back_populates="document")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid4
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False)
    sample_id: Mapped[str | None] = mapped_column(String(4), nullable=True)  # F01..F09
    use_cache: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="QUEUED")
    current_stage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor_id: Mapped[str | None] = mapped_column(String(8), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    po_method: Mapped[str | None] = mapped_column(String(10), nullable=True)  # explicit | inferred | none
    grand_total_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # text | vision | heuristic
    extraction_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    flags_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    review_status: Mapped[str] = mapped_column(String(16), default="NOT_REQUIRED", nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="runs")
    stages: Mapped[list["RunStage"]] = relationship(
        "RunStage",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunStage.position",
    )
    checks: Mapped[list["RunCheck"]] = relationship(
        "RunCheck",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunCheck.position",
    )
    events: Mapped[list["RunEvent"]] = relationship(
        "RunEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunEvent.seq",
    )


class RunStage(Base):
    __tablename__ = "run_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), index=True, nullable=False)
    stage_key: Mapped[str] = mapped_column(String(16), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..8
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    summary: Mapped[str | None] = mapped_column(String(140), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    run: Mapped["Run"] = relationship("Run", back_populates="stages")


class RunCheck(Base):
    __tablename__ = "run_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), index=True, nullable=False)
    stage_key: Mapped[str] = mapped_column(String(16), nullable=False)
    check_id: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)  # PASS | INFO | FLAG | SKIP
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)  # REVIEW | HOLD | REJECT
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    run: Mapped["Run"] = relationship("Run", back_populates="checks")


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "seq", name="uq_run_event_seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), index=True, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run: Mapped["Run"] = relationship("Run", back_populates="events")


class InvoiceLedger(Base):
    __tablename__ = "invoice_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False)  # seed | run
    run_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("runs.id"), nullable=True)
    vendor_id: Mapped[str | None] = mapped_column(String(8), ForeignKey("vendors.vendor_id"), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    invoice_number_norm: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    net_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    grand_total_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # APPROVED | IN_REVIEW | ON_HOLD | REJECTED
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", back_populates="ledger_entries")
    lines: Mapped[list["LedgerLine"]] = relationship(
        "LedgerLine",
        back_populates="ledger_entry",
        cascade="all, delete-orphan",
    )


class LedgerLine(Base):
    __tablename__ = "ledger_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("invoice_ledger.id"), nullable=False)
    po_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    po_line_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    net_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    ledger_entry: Mapped["InvoiceLedger"] = relationship("InvoiceLedger", back_populates="lines")


class ExtractionCache(Base):
    __tablename__ = "extraction_cache"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
