from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_examples():
    response = client.get("/api/v1/examples")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
