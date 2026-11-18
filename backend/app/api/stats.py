import statistics
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Run
from app.rules.money import format_money

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    """Compute aggregate AP metrics per doc 08 §8.4."""
    all_runs = db.query(Run).all()
    total_runs = len(all_runs)

    completed_runs = [r for r in all_runs if r.status == "COMPLETED"]
    completed_count = len(completed_runs)

    by_decision = {
        "APPROVE": sum(1 for r in completed_runs if r.decision == "APPROVE"),
        "REVIEW": sum(1 for r in completed_runs if r.decision == "REVIEW"),
        "HOLD": sum(1 for r in completed_runs if r.decision == "HOLD"),
        "REJECT": sum(1 for r in completed_runs if r.decision == "REJECT"),
    }

    auto_approval_rate = round(by_decision["APPROVE"] / completed_count, 3) if completed_count > 0 else 0.0

    awaiting_action = sum(1 for r in all_runs if r.review_status == "PENDING")

    # Value processed: sum grand_total of completed runs
    # Extract from ledger or runs.result
    total_val_paise = sum(r.grand_total_paise or 0 for r in completed_runs)
    if total_val_paise == 0:
        # Sum from completed runs' results if grand_total_paise was null on run
        for r in completed_runs:
            if r.result and isinstance(r.result, dict):
                norm = r.result.get("normalized")
                if norm and isinstance(norm, dict) and norm.get("grand_total"):
                    try:
                        total_val_paise += int(Decimal(str(norm["grand_total"])) * 100)
                    except Exception:
                        pass

    value_processed = format_money(Decimal(total_val_paise) / Decimal("100"))

    # Median duration
    durations = [r.duration_ms for r in completed_runs if r.duration_ms is not None]
    median_duration_ms = int(statistics.median(durations)) if durations else None

    # Runs last 7 days
    today = datetime.now(UTC).date()
    runs_last_7_days = []
    for day_offset in range(6, -1, -1):
        target_date = today - timedelta(days=day_offset)
        target_str = target_date.isoformat()
        count = sum(1 for r in all_runs if r.created_at and r.created_at.date() == target_date)
        runs_last_7_days.append({"date": target_str, "count": count})

    return {
        "total_runs": total_runs,
        "completed_runs": completed_count,
        "by_decision": by_decision,
        "auto_approval_rate": auto_approval_rate,
        "awaiting_action": awaiting_action,
        "value_processed": value_processed,
        "median_duration_ms": median_duration_ms,
        "runs_last_7_days": runs_last_7_days,
    }
