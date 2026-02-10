"""Smoke test — verifica que o servidor sobe e /health responde."""


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_status(client):
    response = client.get("/health")
    data = response.json()
    assert data == {"status": "ok"}
