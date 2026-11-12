"""
Tests for Layer 3: REST API Service.
"""
import pytest
from src.app.api import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"

def test_overview_endpoint(client):
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.get_json()
    assert "campaigns" in data
    assert "contacts" in data
    assert "touchpoints" in data
    assert data["campaigns"] > 0

def test_models_comparison_endpoint(client):
    res = client.get("/api/models/comparison")
    assert res.status_code == 200
    models = res.get_json()
    assert len(models) == 5
    model_names = {m["model_name"] for m in models}
    assert model_names == {"First-Touch", "Last-Touch", "Linear", "U-Shaped", "Time-Decay"}

def test_campaigns_roi_endpoint(client):
    res = client.get("/api/campaigns?model=U-Shaped")
    assert res.status_code == 200
    camps = res.get_json()
    assert len(camps) > 0
    assert "attributed_revenue" in camps[0]

def test_anomalies_endpoint(client):
    res = client.get("/api/anomalies")
    assert res.status_code == 200
    anomalies = res.get_json()
    assert len(anomalies) > 0

def test_identity_verification_endpoint(client):
    res = client.get("/api/identity/verification")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_web_sessions" in data
    assert "identified_sessions" in data

def test_reconciliation_endpoint(client):
    res = client.get("/api/reconciliation")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "PASSED"
