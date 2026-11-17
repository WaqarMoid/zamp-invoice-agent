from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert "llm_configured" in data
    assert "model" in data
    assert "version" in data


def test_config_endpoint():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["buyer"]["name"] == "Kestrel Foods Pvt. Ltd."
    assert data["buyer"]["gstin"] == "29AAACK4521M1ZD"
    assert data["price_tolerance_pct"] == 1.0
