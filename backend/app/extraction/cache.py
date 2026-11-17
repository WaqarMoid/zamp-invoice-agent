import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExtractionCache
from app.schemas import ExtractedInvoice

logger = logging.getLogger("kestrel-ap.extraction.cache")


def compute_sha256(content: bytes) -> str:
    """Compute hex SHA-256 digest of binary content."""
    return hashlib.sha256(content).hexdigest()


def get_cached_extraction(
    session: Session, sha256: str
) -> tuple[ExtractedInvoice, str, str] | None:
    """
    Look up extraction cache by document SHA-256.
    Returns (ExtractedInvoice, method, model) or None if not cached.
    """
    stmt = select(ExtractionCache).where(ExtractionCache.sha256 == sha256)
    cached = session.execute(stmt).scalar_one_or_none()
    if not cached:
        return None

    try:
        inv = ExtractedInvoice.model_validate(cached.payload)
        return inv, cached.method, cached.model
    except Exception as e:
        logger.warning("Failed to deserialise cached extraction for %s: %s", sha256, e)
        return None


def store_cached_extraction(
    session: Session,
    sha256: str,
    method: str,
    model: str,
    extraction: ExtractedInvoice,
) -> None:
    """
    Store an extracted invoice into extraction_cache.
    If already exists, update payload.
    """
    stmt = select(ExtractionCache).where(ExtractionCache.sha256 == sha256)
    existing = session.execute(stmt).scalar_one_or_none()

    payload = extraction.model_dump(mode="json")

    if existing:
        existing.method = method
        existing.model = model
        existing.payload = payload
    else:
        new_cache = ExtractionCache(
            sha256=sha256,
            method=method,
            model=model,
            payload=payload,
        )
        session.add(new_cache)

    session.commit()
    logger.debug("Stored extraction in cache for %s (method=%s, model=%s)", sha256, method, model)
