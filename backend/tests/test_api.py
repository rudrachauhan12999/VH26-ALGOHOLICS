from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_troubleshoot_success_machine_a():
    response = client.post(
        "/api/troubleshoot",
        json={"query": "E101", "machine": "Machine A", "model": "X200"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["answer"]["error_code"] == "E101"
    assert data["answer"]["meaning"] == "Motor overheating"


def test_troubleshoot_success_machine_b():
    response = client.post(
        "/api/troubleshoot",
        json={"query": "E101", "machine": "Machine B", "model": "H500"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["answer"]["meaning"] == "Hydraulic pressure low"


def test_troubleshoot_ambiguous():
    response = client.post("/api/troubleshoot", json={"query": "E101"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ambiguous"
    assert len(data["options"]) == 2


def test_troubleshoot_insufficient():
    response = client.post(
        "/api/troubleshoot", json={"query": "it's making a weird noise"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient"


def test_troubleshoot_invalid_request():
    response = client.post("/api/troubleshoot", json={})
    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_machines_endpoint():
    response = client.get("/api/machines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["machine"] == "Machine A"


def test_manuals_endpoint():
    response = client.get("/api/manuals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["manual"] == "Machine_A_Manual.pdf"
