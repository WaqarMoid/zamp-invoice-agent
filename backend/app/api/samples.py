import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/api/samples", tags=["samples"])

SEED_DATA_PATH = Path(__file__).resolve().parent.parent / "seed_data" / "fixtures.json"
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def get_group(fid: str) -> str:
    if fid == "F01":
        return "Happy path"
    if fid in ("F02", "F03", "F04", "F05"):
        return "Edge cases"
    return "More scenarios"


@router.get("")
def list_samples():
    """List available invoice samples per doc 05 §5.5."""
    with open(SEED_DATA_PATH, encoding="utf-8") as f:
        fixtures = json.load(f)

    samples = []
    for fix in fixtures:
        fid = fix["fixture_id"]
        samples.append(
            {
                "id": fid,
                "filename": fix["filename"],
                "title": fix.get("title", f"Sample {fid}"),
                "scenario": fix.get("scenario", ""),
                "description": fix.get("description", ""),
                "expected_decision": fix.get("expected_decision", "REVIEW"),
                "group": get_group(fid),
            }
        )

    return sorted(samples, key=lambda s: s["id"])


@router.get("/{id}/file")
def get_sample_file(id: str):
    """Download the raw PDF for a specific sample."""
    with open(SEED_DATA_PATH, encoding="utf-8") as f:
        fixtures = json.load(f)

    fix = next((item for item in fixtures if item["fixture_id"] == id), None)
    if not fix:
        raise HTTPException(status_code=404, detail="Sample not found")

    pdf_path = FIXTURES_DIR / fix["filename"]
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Sample file not found on disk")

    return Response(content=pdf_path.read_bytes(), media_type="application/pdf")
