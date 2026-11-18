import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Document, Run, RunCheck, RunStage
from app.pipeline.context import RunContext
from app.pipeline.events import emit_event
from app.pipeline.stages.decide import run as run_decide
from app.pipeline.stages.duplicates import run as run_duplicates
from app.pipeline.stages.extract import run as run_extract
from app.pipeline.stages.ingest import run as run_ingest
from app.pipeline.stages.normalize import run as run_normalize
from app.pipeline.stages.po_match import run as run_po_match
from app.pipeline.stages.reconcile import run as run_reconcile
from app.pipeline.stages.vendor import run as run_vendor
from app.rules.checks import mask_account
from app.schemas import StageOutcome

logger = logging.getLogger("kestrel-ap.pipeline.runner")

# Global pipeline lock ensuring one execution at a time per doc 07 §7.7
PIPELINE_LOCK = asyncio.Lock()

STAGE_SPECS = [
    (
        1,
        "ingest",
        "Ingest",
        "Stores the file, fingerprints it and checks whether it has a text layer.",
        run_ingest,
    ),
    (
        2,
        "extract",
        "Extract",
        "Reads the invoice into structured fields using the text layer or vision.",
        run_extract,
    ),
    (
        3,
        "normalize",
        "Normalize & validate",
        "Cleans dates, amounts and IDs, then checks the document is complete and adds up.",
        run_normalize,
    ),
    (
        4,
        "vendor",
        "Verify vendor",
        "Identifies the vendor in the master and checks status, GSTIN and bank details.",
        run_vendor,
    ),
    (
        5,
        "duplicates",
        "Detect duplicates",
        "Compares against every invoice already in the ledger.",
        run_duplicates,
    ),
    (
        6,
        "po_match",
        "Match PO",
        "Finds the purchase order, explicitly or by inference, and pairs invoice lines to PO lines.",
        run_po_match,
    ),
    (
        7,
        "reconcile",
        "Reconcile",
        "Checks price, quantity against what is still unbilled on the PO, and tax.",
        run_reconcile,
    ),
    (
        8,
        "decide",
        "Decide",
        "Combines every check into one decision with reasons and next actions.",
        run_decide,
    ),
]


def mask_extraction_dict(ext_dict: dict[str, Any] | None) -> dict[str, Any] | None:
    """Ensure bank account number in extraction is masked before storage per doc 04 §4.5."""
    if not ext_dict:
        return None
    res = dict(ext_dict)
    bank = res.get("bank_details")
    if bank and isinstance(bank, dict):
        bank_copy = dict(bank)
        if bank_copy.get("account_number"):
            bank_copy["account_number"] = mask_account(bank_copy["account_number"])
        res["bank_details"] = bank_copy
    return res


async def execute_run(
    run_id: str,
    db_session: Session | None = None,
    extractor: Any = None,
) -> None:
    """
    Sequential pipeline execution per docs/07_PIPELINE_AND_RULES.md §7.7.
    """
    async with PIPELINE_LOCK:
        owns_session = False
        session = db_session
        if session is None:
            session = SessionLocal()
            owns_session = True

        try:
            run_obj = session.query(Run).filter(Run.id == run_id).first()
            if not run_obj:
                logger.error("Run %s not found in DB.", run_id)
                return

            doc_obj = session.query(Document).filter(Document.id == run_obj.document_id).first()
            if not doc_obj:
                logger.error("Document for run %s not found in DB.", run_id)
                return

            ctx = RunContext(
                run_id=run_id,
                session=session,
                run=run_obj,
                document=doc_obj,
                extractor=extractor,
                use_cache=run_obj.use_cache,
            )

            # Start run
            now_iso = datetime.now(UTC).isoformat()
            run_obj.status = "RUNNING"
            run_obj.started_at = datetime.now(UTC)
            session.commit()

            emit_event(session, run_id, "run.started", {"run_id": run_id, "started_at": now_iso})
            session.commit()

            t_run_start = time.perf_counter()

            # Ensure run_stages rows exist
            existing_stages = {s.stage_key: s for s in run_obj.stages}
            for pos, key, label, desc, _ in STAGE_SPECS:
                if key not in existing_stages:
                    stage_row = RunStage(
                        run_id=run_id,
                        stage_key=key,
                        position=pos,
                        status="PENDING",
                    )
                    session.add(stage_row)
                    existing_stages[key] = stage_row
            session.commit()

            # Execute stages in order
            for pos, key, label, desc, stage_fn in STAGE_SPECS:
                stage_row = existing_stages[key]

                # Check prerequisites per doc 07 §7.7
                prereq_ok = True
                skip_reason = None
                if key == "extract" and "ingest" not in ctx.stage_outputs:
                    prereq_ok = False
                    skip_reason = "Skipped: needs output from Ingest"
                elif key == "normalize" and ctx.extraction is None:
                    prereq_ok = False
                    skip_reason = "Skipped: needs output from Extract"
                elif key in ("vendor", "duplicates", "po_match") and ctx.normalized is None:
                    prereq_ok = False
                    skip_reason = "Skipped: needs output from Normalize"
                elif key == "reconcile" and ctx.po is None:
                    prereq_ok = False
                    skip_reason = "Skipped: needs output from Match PO"

                if not prereq_ok and key != "decide":
                    stage_row.status = "SKIPPED"
                    stage_row.summary = skip_reason
                    session.commit()
                    emit_event(
                        session,
                        run_id,
                        "stage.completed",
                        {
                            "stage_key": key,
                            "position": pos,
                            "status": "SKIPPED",
                            "summary": skip_reason,
                            "duration_ms": 0,
                            "output": {},
                        },
                    )
                    session.commit()
                    continue

                # Stage RUNNING
                t_stage_start = time.perf_counter()
                stage_started_iso = datetime.now(UTC).isoformat()
                stage_row.status = "RUNNING"
                stage_row.started_at = datetime.now(UTC)
                run_obj.current_stage = key
                session.commit()

                emit_event(
                    session,
                    run_id,
                    "stage.started",
                    {
                        "stage_key": key,
                        "position": pos,
                        "label": label,
                        "started_at": stage_started_iso,
                    },
                )
                session.commit()

                # Run stage logic
                try:
                    outcome: StageOutcome = await stage_fn(ctx)
                except Exception as e:
                    logger.exception("Stage %s failed with exception: %s", key, e)
                    outcome = StageOutcome(
                        status="FAILED",
                        summary=f"Error: {str(e)[:60]}",
                        output={"error": repr(e)},
                        checks=[],
                    )

                duration_ms = int((time.perf_counter() - t_stage_start) * 1000)

                # Persist checks and emit check events
                for chk_idx, chk in enumerate(outcome.checks, start=1):
                    chk_row = RunCheck(
                        run_id=run_id,
                        stage_key=chk.stage_key,
                        check_id=chk.check_id,
                        name=chk.name,
                        outcome=chk.outcome,
                        severity=chk.severity,
                        message=chk.message,
                        evidence=chk.evidence,
                        position=chk_idx,
                    )
                    session.add(chk_row)
                    emit_event(
                        session,
                        run_id,
                        "check.result",
                        {
                            "stage_key": chk.stage_key,
                            "check_id": chk.check_id,
                            "name": chk.name,
                            "outcome": chk.outcome,
                            "severity": chk.severity,
                            "message": chk.message,
                        },
                    )

                # Persist stage row
                stage_row.status = outcome.status
                stage_row.summary = outcome.summary
                stage_row.duration_ms = duration_ms
                stage_row.completed_at = datetime.now(UTC)
                stage_row.output = outcome.output
                session.commit()

                emit_event(
                    session,
                    run_id,
                    "stage.completed",
                    {
                        "stage_key": key,
                        "position": pos,
                        "status": outcome.status,
                        "summary": outcome.summary,
                        "duration_ms": duration_ms,
                        "output": outcome.output,
                    },
                )
                session.commit()

            # Finalize run
            total_duration_ms = int((time.perf_counter() - t_run_start) * 1000)
            decide_output = ctx.stage_outputs.get("decide", {})
            decision_val = decide_output.get("decision", "REVIEW")
            label_val = decide_output.get("label", "Needs review")
            headline_val = decide_output.get("headline", "")

            flag_count = sum(1 for c in ctx.all_checks if c.outcome == "FLAG")

            run_obj.status = "COMPLETED"
            run_obj.current_stage = None
            run_obj.completed_at = datetime.now(UTC)
            run_obj.duration_ms = total_duration_ms
            run_obj.decision = decision_val
            run_obj.decision_label = label_val
            run_obj.headline = headline_val
            run_obj.flags_count = flag_count
            run_obj.review_status = "PENDING" if decision_val in ("REVIEW", "HOLD") else "NOT_REQUIRED"

            # Mask extraction for result JSON
            ext_masked = mask_extraction_dict(
                ctx.extraction.model_dump(mode="json") if ctx.extraction else None
            )
            norm_dump = ctx.normalized.model_dump(mode="json") if ctx.normalized else None

            run_obj.result = {
                "extraction": ext_masked,
                "normalized": norm_dump,
                "decision": decide_output,
            }
            session.commit()

            emit_event(
                session,
                run_id,
                "run.completed",
                {
                    "decision": decision_val,
                    "label": label_val,
                    "headline": headline_val,
                    "duration_ms": total_duration_ms,
                },
            )
            session.commit()

        except Exception as e:
            logger.exception("Run %s failed completely: %s", run_id, e)
            try:
                run_obj = session.query(Run).filter(Run.id == run_id).first()
                if run_obj:
                    run_obj.status = "FAILED"
                    run_obj.completed_at = datetime.now(UTC)
                    session.commit()
                emit_event(session, run_id, "run.failed", {"message": str(e)})
                session.commit()
            except Exception:
                pass
            raise
        finally:
            if owns_session:
                session.close()
