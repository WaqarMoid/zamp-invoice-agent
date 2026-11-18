import hashlib
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Run
from app.pipeline.runner import execute_run
from app.schemas import ExtractedInvoice
from app.seed import seed

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = ROOT_DIR / "backend" / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
SEED_DATA_DIR = ROOT_DIR / "backend" / "app" / "seed_data"


class GoldenExtractor:
    def __init__(self, mapping: dict[str, ExtractedInvoice]):
        self.mapping = mapping
        self.current_sha = None

    def set_current_sha(self, sha: str):
        self.current_sha = sha

    def extract_from_text(self, text: str):
        return self.mapping[self.current_sha]

    def extract_from_images(self, images: list[bytes]):
        return self.mapping[self.current_sha]


@pytest.fixture(scope="session")
def golden_map():
    with open(SEED_DATA_DIR / "fixtures.json", encoding="utf-8") as f:
        fixtures = json.load(f)
    mapping = {}
    for fix in fixtures:
        fid = fix["fixture_id"]
        pdf_bytes = (FIXTURES_DIR / fix["filename"]).read_bytes()
        sha = hashlib.sha256(pdf_bytes).hexdigest()
        with open(GOLDEN_DIR / f"{fid}.json", encoding="utf-8") as gf:
            data = json.load(gf)
        mapping[sha] = ExtractedInvoice.model_validate(data)
    return mapping


@pytest.fixture
def api_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        seed(session, force=True)

        def override_get_db():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        yield session
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_samples_endpoints(api_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List samples
        resp = await client.get("/api/samples")
        assert resp.status_code == 200
        samples = resp.json()
        assert len(samples) == 9
        f01 = next(s for s in samples if s["id"] == "F01")
        assert f01["group"] == "Happy path"

        # Download sample file
        resp_file = await client.get("/api/samples/F01/file")
        assert resp_file.status_code == 200
        assert resp_file.headers["content-type"] == "application/pdf"
        assert resp_file.content.startswith(b"%PDF")


@pytest.mark.anyio
async def test_upload_validations(api_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Invalid mime (txt file) -> 415
        resp_txt = await client.post(
            "/api/runs",
            files={"file": ("test.txt", b"Hello world text file", "text/plain")},
        )
        assert resp_txt.status_code == 415

        # 2. File too large (>10MB) -> 413
        large_bytes = b"%PDF" + b"0" * (11 * 1024 * 1024)
        resp_large = await client.post(
            "/api/runs",
            files={"file": ("large.pdf", large_bytes, "application/pdf")},
        )
        assert resp_large.status_code == 413

        # 3. Unknown sample -> 404
        resp_bad_sample = await client.post(
            "/api/runs",
            json={"sample_id": "F99", "use_cache": True},
        )
        assert resp_bad_sample.status_code == 404


@pytest.mark.anyio
async def test_sample_run_lifecycle_and_details(api_test_db, golden_map):
    session = api_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start F01 via sample_id
        resp = await client.post(
            "/api/runs",
            json={"sample_id": "F01", "use_cache": False},
        )
        assert resp.status_code == 202
        data = resp.json()
        run_id = data["run_id"]
        assert data["status"] == "QUEUED"

        # Execute run with golden extractor
        run = session.query(Run).filter(Run.id == run_id).first()
        doc = run.document
        extractor = GoldenExtractor(golden_map)
        extractor.set_current_sha(doc.sha256)
        await execute_run(run_id, db_session=session, extractor=extractor)

        # GET /api/runs/{id}
        resp_detail = await client.get(f"/api/runs/{run_id}")
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["status"] == "COMPLETED"
        assert detail["decision"] == "APPROVE"
        assert detail["document"]["filename"] == "F01_happy_path_sharma.pdf"
        assert len(detail["stages"]) == 8

        # GET /api/runs (list and search)
        resp_list = await client.get("/api/runs?decision=APPROVE")
        assert resp_list.status_code == 200
        list_data = resp_list.json()
        assert list_data["total"] >= 1
        assert list_data["items"][0]["id"] == run_id

        resp_search = await client.get("/api/runs?q=sharma")
        assert resp_search.status_code == 200
        assert resp_search.json()["total"] >= 1

        # GET /api/runs/{id}/document
        resp_doc = await client.get(f"/api/runs/{run_id}/document")
        assert resp_doc.status_code == 200
        assert resp_doc.content.startswith(b"%PDF")

        # GET /api/runs/{id}/pages/1.png
        resp_page = await client.get(f"/api/runs/{run_id}/pages/1.png")
        assert resp_page.status_code == 200
        assert resp_page.headers["content-type"] == "image/png"
        assert resp_page.content.startswith(b"\x89PNG")


@pytest.mark.anyio
async def test_human_review_and_stats(api_test_db, golden_map):
    session = api_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create F02 run
        resp = await client.post(
            "/api/runs",
            json={"sample_id": "F02", "use_cache": False},
        )
        run_id = resp.json()["run_id"]
        run = session.query(Run).filter(Run.id == run_id).first()
        extractor = GoldenExtractor(golden_map)
        extractor.set_current_sha(run.document.sha256)
        await execute_run(run_id, db_session=session, extractor=extractor)

        # Review validation: note < 5 chars -> 422
        resp_bad_note = await client.post(
            f"/api/runs/{run_id}/review",
            json={"action": "approve", "note": "ok"},
        )
        assert resp_bad_note.status_code == 422

        # Valid review -> 200
        resp_rev = await client.post(
            f"/api/runs/{run_id}/review",
            json={
                "action": "approve",
                "note": "Approved overrun approved by AP manager",
                "reviewer": "AP Specialist",
            },
        )
        assert resp_rev.status_code == 200
        rev_data = resp_rev.json()
        assert rev_data["review_status"] == "APPROVED"
        assert rev_data["reviewer"] == "AP Specialist"

        # Review again when already reviewed -> 409
        resp_again = await client.post(
            f"/api/runs/{run_id}/review",
            json={"action": "approve", "note": "Another note here"},
        )
        assert resp_again.status_code == 409

        # GET /api/stats
        resp_stats = await client.get("/api/stats")
        assert resp_stats.status_code == 200
        stats = resp_stats.json()
        assert stats["total_runs"] >= 1
        assert "by_decision" in stats
        assert len(stats["runs_last_7_days"]) == 7


@pytest.mark.anyio
async def test_admin_reset(api_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid confirm -> 422
        resp_bad = await client.post("/api/admin/reset", json={"confirm": "NO"})
        assert resp_bad.status_code == 422

        # Valid reset -> 200
        resp_ok = await client.post("/api/admin/reset", json={"confirm": "RESET"})
        assert resp_ok.status_code == 200
        assert resp_ok.json() == {"ok": True}
