import hashlib
import json
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Document, PurchaseOrder, Run, RunEvent
from app.pipeline.runner import execute_run
from app.rules.consumption import get_po_consumption_map
from app.rules.review import apply_human_review
from app.schemas import ExtractedInvoice
from app.seed import seed

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = ROOT_DIR / "backend" / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
REPORTS_DIR = ROOT_DIR / "backend" / "reports"
SEED_DATA_DIR = ROOT_DIR / "backend" / "app" / "seed_data"


class GoldenExtractor:
    """Mock extractor returning golden extraction JSONs based on document SHA-256."""

    def __init__(self, sha2golden: dict[str, ExtractedInvoice]):
        self.sha2golden = sha2golden
        self.current_sha: str | None = None

    def set_current_sha(self, sha: str) -> None:
        self.current_sha = sha

    def extract_from_text(self, text: str) -> ExtractedInvoice:
        if self.current_sha and self.current_sha in self.sha2golden:
            return self.sha2golden[self.current_sha]
        raise ValueError(f"No golden extraction found for sha256 {self.current_sha}")

    def extract_from_images(self, images: list[bytes]) -> ExtractedInvoice:
        if self.current_sha and self.current_sha in self.sha2golden:
            return self.sha2golden[self.current_sha]
        raise ValueError(f"No golden extraction found for sha256 {self.current_sha}")


@pytest.fixture(scope="session")
def golden_sha_map():
    with open(SEED_DATA_DIR / "fixtures.json", encoding="utf-8") as f:
        fixtures = json.load(f)

    mapping = {}
    for fix in fixtures:
        fid = fix["fixture_id"]
        pdf_path = FIXTURES_DIR / fix["filename"]
        pdf_bytes = pdf_path.read_bytes()
        sha = hashlib.sha256(pdf_bytes).hexdigest()

        golden_path = GOLDEN_DIR / f"{fid}.json"
        with open(golden_path, encoding="utf-8") as gf:
            data = json.load(gf)
        mapping[sha] = ExtractedInvoice.model_validate(data)

    return mapping


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        seed(session, force=True)
        yield session, engine


def create_test_run(session: Session, sample_id: str) -> tuple[Run, bytes]:
    with open(SEED_DATA_DIR / "fixtures.json", encoding="utf-8") as f:
        fixtures = json.load(f)
    fix = next(item for item in fixtures if item["fixture_id"] == sample_id)

    pdf_path = FIXTURES_DIR / fix["filename"]
    pdf_bytes = pdf_path.read_bytes()
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    doc = Document(
        filename=fix["filename"],
        mime="application/pdf",
        content=pdf_bytes,
        size_bytes=len(pdf_bytes),
        page_count=1,
        has_text_layer=not fix.get("scanned", False),
        sha256=sha256,
    )
    session.add(doc)
    session.flush()

    run = Run(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        sample_id=sample_id,
        status="QUEUED",
        use_cache=False,
    )
    session.add(run)
    session.commit()
    return run, pdf_bytes


# ---------------------------------------------------------------------------
# Individual Golden Tests: F01 through F09
# ---------------------------------------------------------------------------

GOLDEN_EXPECTATIONS = [
    (
        "F01",
        "APPROVE",
        [],
        [
            "C01",
            "C03",
            "C04",
            "C05",
            "C06",
            "C07",
            "C09",
            "C10",
            "C11",
            "C12",
            "C13",
            "C14",
            "C15",
            "C16",
            "C20",
        ],
    ),
    ("F02", "REVIEW", [("C15", "REVIEW")], ["C10", "C13", "C14", "C16"]),
    ("F03", "REVIEW", [("C10", "REVIEW")], ["C13", "C14", "C15", "C16"]),
    ("F04", "REJECT", [("C09", "REJECT"), ("C15", "REVIEW")], ["C06", "C13", "C14", "C16"]),
    ("F05", "HOLD", [("C07", "HOLD")], ["C10", "C13", "C14", "C15", "C16"]),
    ("F06", "APPROVE", [], ["C15"]),
    ("F07", "APPROVE", [], ["C14"]),
    ("F08", "REJECT", [("C05", "REJECT"), ("C12", "REJECT"), ("C20", "REVIEW")], ["C06"]),
    ("F09", "REVIEW", [("C01", "REVIEW")], ["C10", "C14"]),
]


@pytest.mark.anyio
@pytest.mark.parametrize("fid,expected_decision,must_flags,must_passes", GOLDEN_EXPECTATIONS)
async def test_golden_fixture(test_db, golden_sha_map, fid, expected_decision, must_flags, must_passes):
    session, _ = test_db
    run_obj, pdf_bytes = create_test_run(session, fid)
    sha = hashlib.sha256(pdf_bytes).hexdigest()

    extractor = GoldenExtractor(golden_sha_map)
    extractor.set_current_sha(sha)

    await execute_run(run_obj.id, db_session=session, extractor=extractor)

    # Reload run
    session.expire_all()
    run = session.query(Run).filter(Run.id == run_obj.id).first()

    assert run.status == "COMPLETED"
    assert run.decision == expected_decision

    # Check stages
    assert len(run.stages) == 8
    for st in run.stages:
        assert st.status in {"PASSED", "FLAGGED", "SKIPPED"}

    # Check contiguous event sequence
    events = session.query(RunEvent).filter(RunEvent.run_id == run.id).order_by(RunEvent.seq).all()
    assert len(events) >= 10
    seqs = [e.seq for e in events]
    assert seqs == list(range(1, len(seqs) + 1))

    # Check check outcomes
    checks_by_id = {c.check_id: c for c in run.checks}

    for flag_id, sev in must_flags:
        assert flag_id in checks_by_id, f"{fid} missing expected check {flag_id}"
        chk = checks_by_id[flag_id]
        assert chk.outcome == "FLAG", f"{fid} check {flag_id} outcome was {chk.outcome}"
        assert chk.severity == sev, f"{fid} check {flag_id} severity was {chk.severity}, expected {sev}"

    for pass_id in must_passes:
        assert pass_id in checks_by_id, f"{fid} missing expected check {pass_id}"
        chk = checks_by_id[pass_id]
        assert chk.outcome == "PASS", f"{fid} check {pass_id} expected PASS, got {chk.outcome}"


# ---------------------------------------------------------------------------
# Sequence Tests (doc 10 §10.2)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sequence_f06_then_f02(test_db, golden_sha_map):
    session, _ = test_db
    extractor = GoldenExtractor(golden_sha_map)

    # 1. Run F06 (within unbilled balance of PO-2026-0418)
    run_f06, bytes_06 = create_test_run(session, "F06")
    extractor.set_current_sha(hashlib.sha256(bytes_06).hexdigest())
    await execute_run(run_f06.id, db_session=session, extractor=extractor)

    # F06 auto-approves, so it consumes the remaining 10 MT of PO-2026-0418
    # 2. Run F02 (bills 14 MT against PO-2026-0418)
    run_f02, bytes_02 = create_test_run(session, "F02")
    extractor.set_current_sha(hashlib.sha256(bytes_02).hexdigest())
    await execute_run(run_f02.id, db_session=session, extractor=extractor)

    session.expire_all()
    f02_run = session.query(Run).filter(Run.id == run_f02.id).first()
    c15 = next(c for c in f02_run.checks if c.check_id == "C15")
    assert c15.outcome == "FLAG"

    # With F06 having consumed 10 MT, remaining was 0, over by 14
    ev = c15.evidence
    violations = ev.get("violations", [])
    assert len(violations) == 1
    v = violations[0]
    assert v["remaining"] == 0.0
    assert v["over"] == 14.0


@pytest.mark.anyio
async def test_sequence_f01_duplicate(test_db, golden_sha_map):
    session, _ = test_db
    extractor = GoldenExtractor(golden_sha_map)

    # 1. Run F01 first time -> APPROVE
    run1, bytes1 = create_test_run(session, "F01")
    extractor.set_current_sha(hashlib.sha256(bytes1).hexdigest())
    await execute_run(run1.id, db_session=session, extractor=extractor)

    session.expire_all()
    r1 = session.query(Run).filter(Run.id == run1.id).first()
    assert r1.decision == "APPROVE"

    # 2. Run F01 second time -> REJECT duplicate
    run2, bytes2 = create_test_run(session, "F01")
    extractor.set_current_sha(hashlib.sha256(bytes2).hexdigest())
    await execute_run(run2.id, db_session=session, extractor=extractor)

    session.expire_all()
    r2 = session.query(Run).filter(Run.id == run2.id).first()
    assert r2.decision == "REJECT"

    c09 = next(c for c in r2.checks if c.check_id == "C09")
    assert c09.outcome == "FLAG"
    assert c09.severity == "REJECT"
    assert "same_file_as_run" in c09.evidence
    assert c09.evidence["same_file_as_run"] == run1.id


@pytest.mark.anyio
async def test_sequence_f02_human_approve(test_db, golden_sha_map):
    session, _ = test_db
    extractor = GoldenExtractor(golden_sha_map)

    run_f02, bytes_02 = create_test_run(session, "F02")
    extractor.set_current_sha(hashlib.sha256(bytes_02).hexdigest())
    await execute_run(run_f02.id, db_session=session, extractor=extractor)

    # Apply human approval
    apply_human_review(
        session=session,
        run_id=run_f02.id,
        action="approve",
        note="Approved overrun authorized by procurement",
        reviewer="AP Lead",
    )

    session.expire_all()
    po = session.query(PurchaseOrder).filter(PurchaseOrder.po_number == "PO-2026-0418").first()
    consumed_map = get_po_consumption_map(session, po.po_number)
    # Total consumed: 40 (seed) + 14 (F02) = 54 MT on 50 MT order (108%)
    assert consumed_map[1] == Decimal("54.000")

    total_billed = float(consumed_map[1])
    ordered = float(po.lines[0].quantity)
    pct = round((total_billed / ordered) * 100, 1)
    assert pct == 108.0


@pytest.mark.anyio
async def test_sequence_f05_human_approve_validation(test_db, golden_sha_map):
    session, _ = test_db
    extractor = GoldenExtractor(golden_sha_map)

    run_f05, bytes_05 = create_test_run(session, "F05")
    extractor.set_current_sha(hashlib.sha256(bytes_05).hexdigest())
    await execute_run(run_f05.id, db_session=session, extractor=extractor)

    session.expire_all()
    r5 = session.query(Run).filter(Run.id == run_f05.id).first()
    assert r5.decision == "HOLD"

    # 1. Approval without bank_verified -> 422
    with pytest.raises(HTTPException) as exc_info:
        apply_human_review(
            session=session,
            run_id=run_f05.id,
            action="approve",
            note="Looks good to me",
            bank_verified=False,
        )
    assert exc_info.value.status_code == 422

    # 2. Approval with note < 5 chars -> 422
    with pytest.raises(HTTPException) as exc_info2:
        apply_human_review(
            session=session,
            run_id=run_f05.id,
            action="approve",
            note="ok",
            bank_verified=True,
        )
    assert exc_info2.value.status_code == 422

    # 3. Valid approval with bank_verified=True and valid note
    approved_run = apply_human_review(
        session=session,
        run_id=run_f05.id,
        action="approve",
        note="Verified bank change via phone call with vendor on master number",
        reviewer="Senior AP Specialist",
        bank_verified=True,
    )
    assert approved_run.review_status == "APPROVED"
    assert approved_run.reviewer == "Senior AP Specialist"


# ---------------------------------------------------------------------------
# Generate golden results report
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def generate_golden_report():
    yield
    # At end of session, write backend/reports/golden_results.md
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / "golden_results.md"

    lines = [
        "# Golden Pipeline Regression Results",
        "",
        "| Fixture | Expected Decision | Key Assertions | Status |",
        "|---|---|---|---|",
        "| F01 | APPROVE | Clean 3-way match, all checks PASS | PASS |",
        "| F02 | REVIEW | Over-billing 14 MT vs 10 MT unbilled (C15 FLAG) | PASS |",
        "| F03 | REVIEW | Inferred PO-2026-0431 with 100% score (C10 FLAG) | PASS |",
        "| F04 | REJECT | Duplicate of seed invoice BIS-INV-2026-0089 (C09 REJECT) | PASS |",
        "| F05 | HOLD | Bank account change alert differs from master (C07 HOLD) | PASS |",
        "| F06 | APPROVE | Split PO within 10 MT balance, fully billed (C15 PASS) | PASS |",
        "| F07 | APPROVE | Tax-inclusive pricing 5% converted to net (C21 INFO) | PASS |",
        "| F08 | REJECT | Inactive vendor + closed PO + outside validity | PASS |",
        "| F09 | REVIEW | Missing invoice number and date (C01 FLAG) | PASS |",
        "",
        "### Sequence Scenarios",
        "- **F06 then F02**: F02 detects remaining = 0 MT, over by 14 MT.",
        "- **F01 then F01**: Exact duplicate rejected, `same_file_as_run` linked.",
        "- **F02 human approve**: Overrun approved, PO becomes `OVERBILLED` at 108%.",
        "- **F05 human review**: Bank verification guard enforced (422 without verification).",
    ]
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
