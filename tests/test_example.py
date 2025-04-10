from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_items():
    response = client.get("/example/")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_read_item():
    response = client.get("/example/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Item 1"

def test_create_item():
    response = client.post(
        "/example/",
        json={"id": 3, "name": "Item 3", "description": "This is item 3"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == 3
    assert response.json()["name"] == "Item 3" 