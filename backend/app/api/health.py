import subprocess

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


def get_git_version() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip() or "dev"
    except Exception:
        return "dev"


@router.get("/health")
def get_health():
    settings = get_settings()
    llm_configured = bool(settings.GEMINI_API_KEY)
    return {
        "status": "ok",
        "db": "ok",
        "llm_configured": llm_configured,
        "model": settings.GEMINI_MODEL,
        "version": get_git_version(),
    }


@router.get("/config")
def get_app_config():
    settings = get_settings()
    return {
        "price_tolerance_pct": settings.PRICE_TOLERANCE_PCT,
        "price_tolerance_abs_inr": settings.PRICE_TOLERANCE_ABS_INR,
        "rounding_tolerance_inr": settings.ROUNDING_TOLERANCE_INR,
        "extraction_min_confidence": settings.EXTRACTION_MIN_CONFIDENCE,
        "vendor_name_match_min": settings.VENDOR_NAME_MATCH_MIN,
        "line_match_min_score": settings.LINE_MATCH_MIN_SCORE,
        "po_infer_min_score": settings.PO_INFER_MIN_SCORE,
        "po_infer_min_margin": settings.PO_INFER_MIN_MARGIN,
        "near_dup_window_days": settings.NEAR_DUP_WINDOW_DAYS,
        "max_invoice_age_days": settings.MAX_INVOICE_AGE_DAYS,
        "auto_approve_inferred_po": settings.AUTO_APPROVE_INFERRED_PO,
        "buyer": {
            "name": "Kestrel Foods Pvt. Ltd.",
            "gstin": settings.BUYER_GSTIN,
        },
        "llm": {
            "provider": settings.LLM_PROVIDER,
            "model": settings.GEMINI_MODEL,
        },
        "demo_mode": settings.DEMO_MODE,
    }
