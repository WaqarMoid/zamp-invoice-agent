from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import InvoiceLedger, Run
from app.pipeline.events import emit_event


def apply_human_review(
    session: Session,
    run_id: str,
    action: Literal["approve", "reject"],
    note: str,
    reviewer: str = "AP reviewer",
    bank_verified: bool = False,
) -> Run:
    """
    Apply human review decision per docs/07_PIPELINE_AND_RULES.md §7.8.
    """
    run_obj = session.query(Run).filter(Run.id == run_id).first()
    if not run_obj:
        raise HTTPException(status_code=404, detail="Run not found")

    if run_obj.review_status != "PENDING" or run_obj.decision not in {"REVIEW", "HOLD"}:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Review not allowed: run is in decision {run_obj.decision} "
                f"with review status {run_obj.review_status}"
            ),
        )

    if not note or len(note.strip()) < 5:
        raise HTTPException(
            status_code=422,
            detail="Review note must be at least 5 characters long.",
        )

    if action == "approve" and run_obj.decision == "HOLD" and not bank_verified:
        raise HTTPException(
            status_code=422,
            detail="Bank change must be verified by calling vendor before approving a run on HOLD.",
        )

    now = datetime.now(UTC)
    now_iso = now.isoformat()
    reviewer_name = reviewer or "AP reviewer"

    # Update ledger entry
    ledger = session.query(InvoiceLedger).filter(InvoiceLedger.run_id == run_id).first()
    if ledger:
        ledger.status = "APPROVED" if action == "approve" else "REJECTED"

    # Update run record
    run_obj.review_status = "APPROVED" if action == "approve" else "REJECTED"
    run_obj.reviewer = reviewer_name
    run_obj.review_note = note.strip()
    run_obj.reviewed_at = now
    session.commit()

    emit_event(
        session,
        run_id,
        "run.reviewed",
        {
            "review_status": run_obj.review_status,
            "reviewer": reviewer_name,
            "note": note.strip(),
            "reviewed_at": now_iso,
        },
    )
    session.commit()

    return run_obj
