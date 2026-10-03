"""Integration tests for AgriSys FastAPI endpoints and WebSocket /ws/chat.

Fulfills Stage 1h & 1i.
"""

import pytest
from fastapi.testclient import TestClient
from agrisys.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_api_health(client: TestClient):
    """Verify health endpoint returns status ok and correct stage."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["stage"] == "Stage 1 (Foundation)"


def test_api_readiness(client: TestClient):
    """Verify readiness probe."""
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_api_providers_list(client: TestClient):
    """Verify registered providers listing."""
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "openai" in data["llm_providers"]
    assert "groq" in data["llm_providers"]
    assert "ollama" in data["llm_providers"]
    assert "openrouter" in data["llm_providers"]
    assert "local" in data["embedding_providers"]


def test_api_ingest_and_query(client: TestClient):
    """Verify ingesting text knowledge via API and querying it with grounded citations."""
    # 1. Ingest knowledge
    ingest_payload = {
        "content": "ICAR Advisory: Tomato late blight caused by Phytophthora infestans requires spraying Metalaxyl 8% + Mancozeb 64% WP at 2.5g per liter.",
        "source": "icar",
        "crop": "tomato",
        "state": "UP",
        "domain": "disease",
    }
    resp_ingest = client.post("/api/ingest/text", json=ingest_payload)
    assert resp_ingest.status_code == 200
    assert resp_ingest.json()["status"] == "success"
    assert resp_ingest.json()["indexed_chunks"] >= 1

    # 2. Query knowledge
    query_payload = {
        "query": "How to treat late blight in tomato in UP?",
        "crop": "tomato",
        "state": "UP",
        "domain": "disease",
    }
    resp_query = client.post("/api/query", json=query_payload)
    assert resp_query.status_code == 200
    res_data = resp_query.json()
    assert len(res_data["sources"]) > 0
    assert "Metalaxyl" in res_data["sources"][0]["text"]
    assert res_data["hallucination_score"] >= 0.70
    assert res_data["verdict"] == "pass"


def test_websocket_chat(client: TestClient):
    """Verify WebSocket /ws/chat streaming protocol."""
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text('{"message": "What is the spray for tomato late blight?"}')

        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("type") == "done":
                break

        types = [m.get("type") for m in messages]
        assert "status" in types
        assert "sources" in types
        assert "token" in types
        assert "guard" in types
        assert "done" in types


def test_api_crop_recommendation(client: TestClient):
    """Verify POST /api/crop/recommend endpoint."""
    payload = {
        "N": 90.0,
        "P": 42.0,
        "K": 43.0,
        "temperature": 25.0,
        "humidity": 82.0,
        "ph": 6.5,
        "rainfall": 200.0,
        "season": "kharif",
        "water_availability": "canal_irrigated",
        "state": "Punjab",
    }
    resp = client.post("/api/crop/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "top_recommendations" in data
    assert len(data["top_recommendations"]) > 0
    assert "winning_crop" in data
    assert "shap_attributions" in data


def test_api_crop_simulation(client: TestClient):
    """Verify POST /api/crop/simulate endpoint."""
    payload = {
        "base_features": {
            "N": 90.0,
            "P": 42.0,
            "K": 43.0,
            "temperature": 25.0,
            "humidity": 82.0,
            "ph": 6.5,
            "rainfall": 200.0,
        },
        "delta_features": {
            "rainfall": -150.0,
            "N": -50.0,
        }
    }
    resp = client.post("/api/crop/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "simulated_winner" in data
    assert "agronomic_verdict" in data


def test_api_diagram_generation(client: TestClient):
    """Verify POST /api/diagram/generate endpoint for 2D SVG schematics."""
    payload = {
        "query": "drip irrigation layout pipe",
        "visual_type": "drip_irrigation",
        "language": "hi",
    }
    resp = client.post("/api/diagram/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["engine_used"] == "svg_2d"
    assert "<svg" in data["raw_code"]


def test_api_orchestrate(client: TestClient):
    """Verify POST /api/orchestrate endpoint executing LangGraph StateGraph."""
    payload = {
        "query": "recommend crop for alluvial soil with high rain and show layout diagram",
        "sensor_data": {"N": 90.0, "P": 42.0, "K": 43.0, "ph": 6.5, "rainfall": 220.0},
        "language": "en",
    }
    resp = client.post("/api/orchestrate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "intents" in data
    assert "merged_response" in data
    assert len(data["merged_response"]) > 20


def test_prometheus_metrics_endpoint(client: TestClient):
    """Verify GET /metrics endpoint exports standard Prometheus exposition format."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert "agrisys_requests_total" in text
    assert "agrisys_request_duration_seconds" in text
    assert "agrisys_hallucination_guard_score" in text

