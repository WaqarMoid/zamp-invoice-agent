import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.extraction.cache import compute_sha256, get_cached_extraction, store_cached_extraction
from app.schemas import ExtractedInvoice

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "golden"

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def test_extraction_cache_store_and_lookup():
    with open(GOLDEN_DIR / "F01.json", encoding="utf-8") as f:
        data = json.load(f)
    ext = ExtractedInvoice.model_validate(data)

    dummy_bytes = b"PDF_SAMPLE_CONTENT_F01"
    sha = compute_sha256(dummy_bytes)

    with Session() as session:
        # Before storing, cache is None
        assert get_cached_extraction(session, sha) is None

        # Store in cache
        store_cached_extraction(
            session=session,
            sha256=sha,
            method="text",
            model="gemini-2.5-flash",
            extraction=ext,
        )

        # Lookup in cache
        cached_result = get_cached_extraction(session, sha)
        assert cached_result is not None
        cached_ext, method, model = cached_result

        assert method == "text"
        assert model == "gemini-2.5-flash"
        assert cached_ext.vendor_gstin == ext.vendor_gstin
        assert cached_ext.grand_total == ext.grand_total
