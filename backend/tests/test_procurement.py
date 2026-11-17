from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.seed import seed

# Use in-memory SQLite with StaticPool so all connections share the DB
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
with TestingSessionLocal() as session:
    seed(session, force=True)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_vendors_endpoint():
    res = client.get("/api/vendors")
    assert res.status_code == 200
    vendors = res.json()
    assert len(vendors) == 6

    # Verify bank account masking: never sent to UI unmasked; API sends '••••' + last 4
    for v in vendors:
        assert "bank_account_number" not in v
        assert v["bank_account_masked"].startswith("••••")
        assert len(v["bank_account_masked"]) == 8  # 4 bullets + 4 digits

    # Verify V006 is INACTIVE
    v006 = next(v for v in vendors if v["vendor_id"] == "V006")
    assert v006["status"] == "INACTIVE"
    assert v006["deactivated_on"] == "2026-09-30"


def test_purchase_orders_consumption_matches_doc_05():
    res = client.get("/api/purchase-orders")
    assert res.status_code == 200
    pos = {p["po_number"]: p for p in res.json()}
    assert len(pos) == 8

    # Table in doc 05 §5.2:
    # PO-2026-0377 | V006 Metro Office | 100 reams | 0 | 100 (but PO CLOSED)
    p377 = pos["PO-2026-0377"]
    assert p377["status"] == "CLOSED"
    assert p377["billing_state"] == "UNBILLED"
    assert p377["lines"][0]["billed_quantity"] == "0"
    assert p377["lines"][0]["remaining_quantity"] == "100"

    # PO-2026-0398 | V003 Bluepeak | 120 licences + 1 LS | 120 + 1 | 0 (fully billed)
    p398 = pos["PO-2026-0398"]
    assert p398["billing_state"] == "FULLY_BILLED"
    assert p398["lines"][0]["billed_quantity"] == "120"
    assert p398["lines"][0]["remaining_quantity"] == "0"
    assert p398["lines"][1]["billed_quantity"] == "1"
    assert p398["lines"][1]["remaining_quantity"] == "0"

    # PO-2026-0412 | V001 Sharma | 2000 / 2000 / 300 | 0 | all
    p412 = pos["PO-2026-0412"]
    assert p412["billing_state"] == "UNBILLED"
    assert p412["lines"][0]["remaining_quantity"] == "2000"
    assert p412["lines"][1]["remaining_quantity"] == "2000"
    assert p412["lines"][2]["remaining_quantity"] == "300"

    # PO-2026-0418 | V002 Deccan | 50 trips | 40 (DCC/2627/0611, DCC/2627/0702) | 10 trips
    p418 = pos["PO-2026-0418"]
    assert p418["billing_state"] == "PARTIALLY_BILLED"
    assert p418["lines"][0]["billed_quantity"] == "40"
    assert p418["lines"][0]["remaining_quantity"] == "10"


def test_single_po_detail_with_invoices():
    res = client.get("/api/purchase-orders/PO-2026-0418")
    assert res.status_code == 200
    data = res.json()
    assert data["po_number"] == "PO-2026-0418"
    assert len(data["invoices"]) == 2  # DCC/2627/0611 and DCC/2627/0702
    inv_numbers = [inv["invoice_number"] for inv in data["invoices"]]
    assert "DCC/2627/0611" in inv_numbers
    assert "DCC/2627/0702" in inv_numbers
