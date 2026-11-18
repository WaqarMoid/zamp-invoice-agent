import asyncio
import hashlib
import json
import logging
import uuid
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pymupdf
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db import get_db
from app.models import Document, Run, RunEvent, RunStage
from app.pipeline.events import subscribe, unsubscribe
from app.pipeline.runner import STAGE_SPECS, execute_run
from app.rules.money import format_money
from app.rules.review import apply_human_review

logger = logging.getLogger("kestrel-ap.api.runs")

router = APIRouter(prefix="/api/runs", tags=["runs"])

# Set of strong references to running background tasks to avoid garbage collection
_BACKGROUND_TASKS: set[asyncio.Task] = set()

# LRU Cache for rendered page PNGs (max 64 entries)
_PAGE_CACHE: OrderedDict[tuple[str, int, int], bytes] = OrderedDict()
_PAGE_CACHE_MAX = 64

SEED_DATA_PATH = Path(__file__).resolve().parent.parent / "seed_data" / "fixtures.json"
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"

STAGE_META = {
    "ingest": ("Ingest", "Stores the file, fingerprints it and checks whether it has a text layer."),
    "extract": ("Extract", "Reads the invoice into structured fields using the text layer or vision."),
    "normalize": (
        "Normalize & validate",
        "Cleans dates, amounts and IDs, then checks the document is complete and adds up.",
    ),
    "vendor": (
        "Verify vendor",
        "Identifies the vendor in the master and checks status, GSTIN and bank details.",
    ),
    "duplicates": ("Detect duplicates", "Compares against every invoice already in the ledger."),
    "po_match": (
        "Match PO",
        "Finds the purchase order, explicitly or by inference, and pairs invoice lines to PO lines.",
    ),
    "reconcile": ("Reconcile", "Checks price, quantity against what is still unbilled on the PO, and tax."),
    "decide": ("Decide", "Combines every check into one decision with reasons and next actions."),
}


class SampleRunRequest(BaseModel):
    sample_id: str
    use_cache: bool = True


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    note: str
    reviewer: str | None = None
    bank_verified: bool = False


def validate_file_bytes(content: bytes) -> tuple[str, str]:
    """
    Validate file magic bytes and size.
    Returns (mime_type, extension).
    """
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    if content.startswith(b"%PDF"):
        return "application/pdf", ".pdf"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    elif content.startswith(b"\xff\xd8"):
        return "image/jpeg", ".jpg"
    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format. Only PDF, PNG, or JPEG files are accepted.",
        )


def build_run_summary(run: Run) -> dict[str, Any]:
    doc = run.document
    filename = doc.filename if doc else "invoice.pdf"

    gt_str = None
    vendor_name = run.vendor_name
    inv_num = run.invoice_number
    po_num = run.po_number
    po_method = run.po_method

    if run.result and isinstance(run.result, dict):
        norm = run.result.get("normalized")
        if norm and isinstance(norm, dict):
            if not vendor_name:
                vendor_name = norm.get("vendor_name")
            if not inv_num:
                inv_num = norm.get("invoice_number")
            if not po_num:
                po_num = norm.get("po_number")
            if norm.get("grand_total") is not None:
                gt_str = format_money(Decimal(str(norm["grand_total"])))
        dec = run.result.get("decision")
        if dec and isinstance(dec, dict):
            kf = dec.get("key_facts", {})
            if not po_method:
                po_method = kf.get("po_method")

    if not gt_str and run.grand_total_paise is not None:
        gt_str = format_money(Decimal(run.grand_total_paise) / Decimal("100"))

    label = None
    if run.decision:
        label_map = {
            "APPROVE": "Approved",
            "REVIEW": "Needs review",
            "HOLD": "On hold",
            "REJECT": "Rejected",
        }
        label = label_map.get(run.decision, run.decision)
        if run.result and isinstance(run.result, dict):
            dec = run.result.get("decision")
            if dec and isinstance(dec, dict) and dec.get("label"):
                label = dec["label"]

    return {
        "id": run.id,
        "short_id": run.id[:8],
        "status": run.status,
        "current_stage": run.current_stage,
        "decision": run.decision,
        "label": label,
        "headline": run.headline,
        "vendor_name": vendor_name,
        "invoice_number": inv_num,
        "po_number": po_num,
        "po_method": po_method,
        "grand_total": gt_str,
        "flags_count": run.flags_count,
        "sample_id": run.sample_id,
        "filename": filename,
        "review_status": run.review_status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_ms": run.duration_ms,
    }


def build_run_detail(run: Run) -> dict[str, Any]:
    summary = build_run_summary(run)
    doc = run.document

    doc_info = {
        "filename": doc.filename if doc else "",
        "mime": doc.mime if doc else "application/pdf",
        "size_bytes": doc.size_bytes if doc else 0,
        "page_count": doc.page_count if doc else 1,
        "has_text_layer": doc.has_text_layer if doc else False,
        "sha256": doc.sha256 if doc else "",
    }

    # Group checks by stage_key
    checks_by_stage: dict[str, list[dict[str, Any]]] = {}
    for chk in run.checks:
        if chk.stage_key not in checks_by_stage:
            checks_by_stage[chk.stage_key] = []
        checks_by_stage[chk.stage_key].append(
            {
                "stage_key": chk.stage_key,
                "check_id": chk.check_id,
                "name": chk.name,
                "outcome": chk.outcome,
                "severity": chk.severity,
                "message": chk.message,
                "evidence": chk.evidence or {},
            }
        )

    # Build stages array
    stages_map = {s.stage_key: s for s in run.stages}
    stages_out = []
    for pos, key, default_label, default_desc, _ in STAGE_SPECS:
        st_row = stages_map.get(key)
        label, desc = STAGE_META.get(key, (default_label, default_desc))
        stages_out.append(
            {
                "stage_key": key,
                "position": pos,
                "label": label,
                "description": desc,
                "status": st_row.status if st_row else "PENDING",
                "summary": st_row.summary if st_row else None,
                "started_at": st_row.started_at.isoformat() if (st_row and st_row.started_at) else None,
                "completed_at": st_row.completed_at.isoformat() if (st_row and st_row.completed_at) else None,
                "duration_ms": st_row.duration_ms if st_row else None,
                "output": st_row.output if st_row else None,
                "checks": checks_by_stage.get(key, []),
            }
        )

    detail = dict(summary)
    detail.update(
        {
            "document": doc_info,
            "use_cache": run.use_cache,
            "extraction_method": run.extraction_method,
            "stages": stages_out,
            "result": run.result,
            "reviewer": run.reviewer,
            "review_note": run.review_note,
            "reviewed_at": run.reviewed_at.isoformat() if run.reviewed_at else None,
        }
    )
    return detail


@router.post("", status_code=202)
async def create_run(
    request: Request,
    file: UploadFile | None = File(None),
    use_cache: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Initiate an invoice processing run from file upload or sample ID per doc 08 §8.1.
    """
    content_type = request.headers.get("content-type", "")
    sample_id = None
    use_cache_bool = True

    if "application/json" in content_type:
        # JSON body with sample_id
        try:
            body = await request.json()
            sample_req = SampleRunRequest.model_validate(body)
            sample_id = sample_req.sample_id
            use_cache_bool = sample_req.use_cache
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON body: {e}")

        # Look up sample
        with open(SEED_DATA_PATH, encoding="utf-8") as f:
            fixtures = json.load(f)
        fix = next((item for item in fixtures if item["fixture_id"] == sample_id), None)
        if not fix:
            raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found.")

        pdf_path = FIXTURES_DIR / fix["filename"]
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Sample file missing on disk.")

        file_bytes = pdf_path.read_bytes()
        filename = fix["filename"]
        mime = "application/pdf"

    elif file:
        filename = file.filename or "invoice.pdf"
        file_bytes = await file.read()
        mime, _ = validate_file_bytes(file_bytes)
        if use_cache is not None:
            use_cache_bool = use_cache.lower() in ("true", "1", "yes")
    else:
        raise HTTPException(
            status_code=422,
            detail="Either 'file' multipart or JSON with 'sample_id' must be provided.",
        )

    sha256 = hashlib.sha256(file_bytes).hexdigest()

    # Create Document record
    doc = Document(
        filename=filename,
        mime=mime,
        content=file_bytes,
        size_bytes=len(file_bytes),
        page_count=1,
        has_text_layer=True,
        sha256=sha256,
    )
    db.add(doc)
    db.flush()

    # Create Run record
    run_id = str(uuid.uuid4())
    run = Run(
        id=run_id,
        document_id=doc.id,
        sample_id=sample_id,
        use_cache=use_cache_bool,
        status="QUEUED",
    )
    db.add(run)

    # Pre-create stages
    for pos, key, default_label, default_desc, _ in STAGE_SPECS:
        stage_row = RunStage(
            run_id=run_id,
            stage_key=key,
            position=pos,
            status="PENDING",
        )
        db.add(stage_row)

    db.commit()

    # Launch background run execution
    task = asyncio.create_task(execute_run(run_id))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)

    return {"run_id": run_id, "status": "QUEUED"}


@router.get("")
def list_runs(
    decision: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List runs with optional filtering and search."""
    query = db.query(Run)

    if decision:
        query = query.filter(Run.decision == decision)
    if status:
        query = query.filter(Run.status == status)

    if q and q.strip():
        search_pattern = f"%{q.strip().lower()}%"
        query = query.join(Document, Run.document_id == Document.id).filter(
            or_(
                func.lower(Run.vendor_name).like(search_pattern),
                func.lower(Run.invoice_number).like(search_pattern),
                func.lower(Run.po_number).like(search_pattern),
                func.lower(Document.filename).like(search_pattern),
            )
        )

    total = query.count()
    runs = query.order_by(Run.created_at.desc()).offset(offset).limit(limit).all()

    items = [build_run_summary(r) for r in runs]
    return {"items": items, "total": total}


@router.get("/{id}")
def get_run(id: str, db: Session = Depends(get_db)):
    """Fetch complete details of a specific run."""
    run = db.query(Run).filter(Run.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return build_run_detail(run)


@router.get("/{id}/events")
async def stream_run_events(
    id: str,
    request: Request,
    after_seq: int = Query(0, ge=0),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
    db: Session = Depends(get_db),
):
    """Server-Sent Events streaming endpoint per doc 08 §8.3."""
    run = db.query(Run).filter(Run.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    last_seq = after_seq
    if last_event_id:
        try:
            last_seq = max(last_seq, int(last_event_id))
        except ValueError:
            pass

    # Subscribe to broker first to prevent missing events
    client_queue = await subscribe(id)

    async def event_generator():
        last_seen = last_seq
        try:
            # 1. Replay past events from DB where seq > last_seq
            past_events = (
                db.query(RunEvent)
                .filter(RunEvent.run_id == id, RunEvent.seq > last_seq)
                .order_by(RunEvent.seq.asc())
                .all()
            )
            for evt in past_events:
                last_seen = max(last_seen, evt.seq)
                yield {
                    "id": str(evt.seq),
                    "event": evt.type,
                    "data": json.dumps(evt.payload),
                }

            # If run was already finished and no more live events expected:
            db.refresh(run)
            if run.status in ("COMPLETED", "FAILED") and client_queue.empty():
                return

            # 2. Stream new live events from queue with 15s ping
            while True:
                if await request.is_disconnected():
                    break

                try:
                    seq, evt_type, data = await asyncio.wait_for(client_queue.get(), timeout=15.0)
                    if seq > last_seen:
                        last_seen = seq
                        yield {
                            "id": str(seq),
                            "event": evt_type,
                            "data": json.dumps(data),
                        }
                        if evt_type in ("run.completed", "run.failed"):
                            break
                except TimeoutError:
                    # Send comment ping every 15s
                    yield {"comment": "ping"}

        finally:
            await unsubscribe(id, client_queue)

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{id}/document")
def get_run_document(id: str, db: Session = Depends(get_db)):
    """Return raw invoice document bytes with its MIME type."""
    run = db.query(Run).filter(Run.id == id).first()
    if not run or not run.document:
        raise HTTPException(status_code=404, detail="Document not found.")

    return Response(content=run.document.content, media_type=run.document.mime)


@router.get("/{id}/pages/{n}.png")
def get_run_page_image(
    id: str,
    n: int,
    dpi: int = Query(110, ge=50, le=300),
    db: Session = Depends(get_db),
):
    """
    Render page n (1-based) as PNG using PyMuPDF with in-memory caching.
    """
    if n < 1:
        raise HTTPException(status_code=400, detail="Page number must be >= 1.")

    cache_key = (id, n, dpi)
    if cache_key in _PAGE_CACHE:
        return Response(content=_PAGE_CACHE[cache_key], media_type="image/png")

    run = db.query(Run).filter(Run.id == id).first()
    if not run or not run.document:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc = run.document
    mime = doc.mime

    if mime in ("image/png", "image/jpeg"):
        if n != 1:
            raise HTTPException(status_code=404, detail="Image document only has page 1.")
        # If it's already an image, return PNG bytes
        try:
            pdf_doc = pymupdf.open(stream=doc.content, filetype="png" if "png" in mime else "jpeg")
            pix = pdf_doc[0].get_pixmap(dpi=dpi)
            png_bytes = pix.tobytes("png")
        except Exception:
            png_bytes = doc.content
    else:
        try:
            pdf_doc = pymupdf.open(stream=doc.content, filetype="pdf")
            if n > len(pdf_doc):
                raise HTTPException(status_code=404, detail=f"Document only has {len(pdf_doc)} pages.")
            page = pdf_doc[n - 1]
            pix = page.get_pixmap(dpi=dpi)
            png_bytes = pix.tobytes("png")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to render page: {e}")

    # Store in LRU cache
    if len(_PAGE_CACHE) >= _PAGE_CACHE_MAX:
        _PAGE_CACHE.popitem(last=False)
    _PAGE_CACHE[cache_key] = png_bytes

    return Response(content=png_bytes, media_type="image/png")


@router.post("/{id}/review")
def review_run(
    id: str,
    req: ReviewRequest,
    db: Session = Depends(get_db),
):
    """Submit human review decision per doc 07 §7.8."""
    run = apply_human_review(
        session=db,
        run_id=id,
        action=req.action,
        note=req.note,
        reviewer=req.reviewer or "AP reviewer",
        bank_verified=req.bank_verified,
    )
    return build_run_detail(run)
