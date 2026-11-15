from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["docs"] == "/docs"


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_items_crud():
    # List items
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)

    # Create item
    new_item = {
        "title": "Test 3D Print",
        "description": "Filament test cube",
        "is_completed": False,
    }
    create_response = client.post("/api/v1/items", json=new_item)
    assert create_response.status_code == 201
    created_data = create_response.json()
    assert created_data["title"] == new_item["title"]
    item_id = created_data["id"]

    # Get created item
    get_response = client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == item_id

    # Update item
    update_payload = {"is_completed": True}
    update_response = client.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["is_completed"] is True

    # Delete item
    delete_response = client.delete(f"/api/v1/items/{item_id}")
    assert delete_response.status_code == 204

    # Confirm 404 after deletion
    not_found_response = client.get(f"/api/v1/items/{item_id}")
    assert not_found_response.status_code == 404
