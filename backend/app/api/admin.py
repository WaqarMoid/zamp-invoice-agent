from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.seed import seed

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ResetRequest(BaseModel):
    confirm: str = "RESET"


@router.post("/reset")
def reset_database(req: ResetRequest, db: Session = Depends(get_db)):
    """Reset database to initial seed state. Gated by DEMO_MODE."""
    settings = get_settings()
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Database reset is only permitted when DEMO_MODE is true.",
        )

    if req.confirm != "RESET":
        raise HTTPException(
            status_code=422,
            detail="Confirmation payload must equal 'RESET'.",
        )

    seed(db, force=True)
    return {"ok": True}
