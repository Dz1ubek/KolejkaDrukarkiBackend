import io
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.pricing import calculate_estimated_price
from app.core.security import create_access_token, get_password_hash
from app.db.session import Base, get_db, seed_first_admin
from app.main import app
from app.models.print_job import PaymentStatus, PrintJob, PrintStatus
from app.models.user import User, UserRole


@pytest.fixture
def print_test_setup(tmp_path, monkeypatch):
    """Sets up an isolated in-memory DB and temp upload directory."""
    # Override upload dir to a temporary test directory
    test_upload_dir = str(tmp_path / "uploads")
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", test_upload_dir)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_db = TestingSessionLocal()

    # Create admin
    admin = User(
        email="admin@test.com",
        username="admin_user",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    # Create regular user 1
    user1 = User(
        email="user1@test.com",
        username="user1",
        hashed_password=get_password_hash("UserPass123!"),
        role=UserRole.USER.value,
        is_active=True,
    )
    # Create regular user 2
    user2 = User(
        email="user2@test.com",
        username="user2",
        hashed_password=get_password_hash("UserPass123!"),
        role=UserRole.USER.value,
        is_active=True,
    )
    seed_db.add_all([admin, user1, user2])
    seed_db.commit()
    seed_db.refresh(admin)
    seed_db.refresh(user1)
    seed_db.refresh(user2)

    admin_id = admin.id
    user1_id = user1.id
    user2_id = user2.id
    seed_db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    admin_token = create_access_token(subject=admin_id)
    user1_token = create_access_token(subject=user1_id)
    user2_token = create_access_token(subject=user2_id)

    client = TestClient(app)

    yield {
        "client": client,
        "admin_id": admin_id,
        "user1_id": user1_id,
        "user2_id": user2_id,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "user1_headers": {"Authorization": f"Bearer {user1_token}"},
        "user2_headers": {"Authorization": f"Bearer {user2_token}"},
        "upload_dir": test_upload_dir,
        "session_maker": TestingSessionLocal,
    }

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_pricing_calculation():
    # Base: 500, Weight: 50g * 15 = 750, Time: 2h * 300 = 600 -> Total: 1850
    price = calculate_estimated_price(estimated_weight_g=50.0, estimated_time_hours=2.0)
    assert price == 1850


def test_pricing_estimate_endpoint(print_test_setup):
    client = print_test_setup["client"]
    res = client.get("/api/v1/prints/estimate?estimated_weight_g=50&estimated_time_hours=2")
    assert res.status_code == 200
    data = res.json()
    assert data["estimated_price"] == 1850
    assert data["currency"] == "PLN"


def test_create_print_order(print_test_setup):
    client = print_test_setup["client"]
    headers = print_test_setup["user1_headers"]

    file_content = b"solid test_model\nfacet normal 0 0 0\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid"
    files = {"file": ("bracket.stl", io.BytesIO(file_content), "application/octet-stream")}
    data = {
        "title": "Camera Mount Bracket",
        "notes": "Print in black PLA with 20% infill",
        "material": "PLA",
        "estimated_weight_g": "40.0",
        "estimated_time_hours": "1.5",
    }

    res = client.post("/api/v1/prints", headers=headers, data=data, files=files)
    assert res.status_code == 201
    job = res.json()
    assert job["title"] == "Camera Mount Bracket"
    assert job["original_filename"] == "bracket.stl"
    assert job["status"] == "pending_review"
    assert job["payment_status"] == "pending"
    # Base: 500 + 40*15 (600) + 1.5*300 (450) = 1550
    assert job["estimated_price"] == 1550
    assert job["final_price"] is None


def test_reject_unsupported_file_extension(print_test_setup):
    client = print_test_setup["client"]
    headers = print_test_setup["user1_headers"]

    files = {"file": ("dangerous.exe", io.BytesIO(b"fake binary"), "application/octet-stream")}
    data = {
        "title": "Bad File",
        "estimated_weight_g": "10.0",
        "estimated_time_hours": "1.0",
    }

    res = client.post("/api/v1/prints", headers=headers, data=data, files=files)
    assert res.status_code == 400
    assert "not allowed" in res.json()["detail"]


def test_list_my_prints_and_permissions(print_test_setup):
    client = print_test_setup["client"]
    user1_headers = print_test_setup["user1_headers"]
    user2_headers = print_test_setup["user2_headers"]
    admin_headers = print_test_setup["admin_headers"]

    # User 1 creates an order
    files = {"file": ("part.stl", io.BytesIO(b"solid part\nendsolid"), "application/octet-stream")}
    data = {"title": "User 1 Part", "estimated_weight_g": "20.0", "estimated_time_hours": "1.0"}
    create_res = client.post("/api/v1/prints", headers=user1_headers, data=data, files=files)
    assert create_res.status_code == 201
    job_id = create_res.json()["id"]

    # User 1 sees it in /my
    my_res = client.get("/api/v1/prints/my", headers=user1_headers)
    assert my_res.status_code == 200
    assert my_res.json()["total"] == 1
    assert my_res.json()["items"][0]["id"] == job_id

    # User 2 cannot see it in /my
    user2_my_res = client.get("/api/v1/prints/my", headers=user2_headers)
    assert user2_my_res.status_code == 200
    assert user2_my_res.json()["total"] == 0

    # User 2 cannot access user 1's job details
    get_res = client.get(f"/api/v1/prints/{job_id}", headers=user2_headers)
    assert get_res.status_code == 403

    # Admin can access user 1's job details
    admin_get = client.get(f"/api/v1/prints/{job_id}", headers=admin_headers)
    assert admin_get.status_code == 200
    assert admin_get.json()["id"] == job_id


def test_download_file(print_test_setup):
    client = print_test_setup["client"]
    user1_headers = print_test_setup["user1_headers"]
    user2_headers = print_test_setup["user2_headers"]
    admin_headers = print_test_setup["admin_headers"]

    raw_data = b"stl 3d model binary content"
    files = {"file": ("model.stl", io.BytesIO(raw_data), "application/octet-stream")}
    data = {"title": "Download Test", "estimated_weight_g": "10.0", "estimated_time_hours": "1.0"}
    create_res = client.post("/api/v1/prints", headers=user1_headers, data=data, files=files)
    job_id = create_res.json()["id"]

    # Owner can download
    owner_dl = client.get(f"/api/v1/prints/{job_id}/file", headers=user1_headers)
    assert owner_dl.status_code == 200
    assert owner_dl.content == raw_data

    # Other user cannot download
    other_dl = client.get(f"/api/v1/prints/{job_id}/file", headers=user2_headers)
    assert other_dl.status_code == 403

    # Admin can download
    admin_dl = client.get(f"/api/v1/prints/{job_id}/file", headers=admin_headers)
    assert admin_dl.status_code == 200
    assert admin_dl.content == raw_data


def test_cancel_print_job(print_test_setup):
    client = print_test_setup["client"]
    headers = print_test_setup["user1_headers"]

    files = {"file": ("item.stl", io.BytesIO(b"data"), "application/octet-stream")}
    data = {"title": "To Cancel", "estimated_weight_g": "10.0", "estimated_time_hours": "1.0"}
    create_res = client.post("/api/v1/prints", headers=headers, data=data, files=files)
    job_id = create_res.json()["id"]

    # Cancel while pending_review
    cancel_res = client.delete(f"/api/v1/prints/{job_id}", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


def test_admin_queue_and_price_correction(print_test_setup):
    client = print_test_setup["client"]
    user1_headers = print_test_setup["user1_headers"]
    admin_headers = print_test_setup["admin_headers"]

    # User creates job
    files = {"file": ("gear.stl", io.BytesIO(b"data"), "application/octet-stream")}
    data = {"title": "Robot Gear", "estimated_weight_g": "25.0", "estimated_time_hours": "1.0"}
    create_res = client.post("/api/v1/prints", headers=user1_headers, data=data, files=files)
    job_id = create_res.json()["id"]

    # Admin lists queue
    queue_res = client.get("/api/v1/admin/prints/queue", headers=admin_headers)
    assert queue_res.status_code == 200
    assert queue_res.json()["total"] == 1

    # Regular user cannot access queue
    forbidden_res = client.get("/api/v1/admin/prints/queue", headers=user1_headers)
    assert forbidden_res.status_code == 403

    # Admin corrects final price and approves status
    patch_res = client.patch(
        f"/api/v1/admin/prints/{job_id}",
        headers=admin_headers,
        json={
            "final_price": 2000,
            "status": "ready_to_print",
            "notes": "Added supports manually",
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["final_price"] == 2000
    assert updated["status"] == "ready_to_print"
    assert updated["notes"] == "Added supports manually"

    # Admin deletes job
    del_res = client.delete(f"/api/v1/admin/prints/{job_id}", headers=admin_headers)
    assert del_res.status_code == 204

    # Confirms deleted
    assert client.get(f"/api/v1/prints/{job_id}", headers=admin_headers).status_code == 404


def test_seed_first_admin(print_test_setup):
    session_maker = print_test_setup["session_maker"]
    # Check that calling seed_first_admin when an admin already exists does nothing
    with session_maker() as db:
        admin_count_before = db.query(User).filter(User.role == UserRole.ADMIN.value).count()
        seed_first_admin(db)
        admin_count_after = db.query(User).filter(User.role == UserRole.ADMIN.value).count()
        assert admin_count_before == admin_count_after


def test_report_print_error_marks_job_failed_and_lists_errors(print_test_setup):
    client = print_test_setup["client"]
    user_headers = print_test_setup["user1_headers"]
    other_user_headers = print_test_setup["user2_headers"]

    files = {"file": ("part.stl", io.BytesIO(b"data"), "application/octet-stream")}
    data = {"title": "Failed Part", "estimated_weight_g": "20", "estimated_time_hours": "1"}
    job_response = client.post("/api/v1/prints", headers=user_headers, data=data, files=files)
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    error_response = client.post(
        "/api/v1/print-errors",
        headers=user_headers,
        json={
            "job_id": job_id,
            "error_type": "FILAMENT_RUNOUT",
            "description": "Filament ran out during printing",
        },
    )
    assert error_response.status_code == 201
    error = error_response.json()
    assert error["job_id"] == job_id
    assert error["reported_by_user_id"] == print_test_setup["user1_id"]
    assert error["error_type"] == "FILAMENT_RUNOUT"
    assert error["created_at"]

    job_after_error = client.get(f"/api/v1/prints/{job_id}", headers=user_headers)
    assert job_after_error.status_code == 200
    assert job_after_error.json()["status"] == "FAILED"

    own_errors = client.get("/api/v1/print-errors", headers=user_headers)
    assert own_errors.status_code == 200
    assert [item["id"] for item in own_errors.json()] == [error["id"]]
    assert client.get("/api/v1/print-errors", headers=other_user_headers).json() == []


def test_print_error_validation_permissions_and_job_filter(print_test_setup):
    client = print_test_setup["client"]
    user_headers = print_test_setup["user1_headers"]
    other_user_headers = print_test_setup["user2_headers"]
    admin_headers = print_test_setup["admin_headers"]

    files = {"file": ("part.stl", io.BytesIO(b"data"), "application/octet-stream")}
    data = {"title": "Private Part", "estimated_weight_g": "20", "estimated_time_hours": "1"}
    job_response = client.post("/api/v1/prints", headers=user_headers, data=data, files=files)
    job_id = job_response.json()["id"]

    payload = {
        "job_id": job_id,
        "error_type": "OTHER",
        "description": "Unexpected print failure",
    }
    assert client.post("/api/v1/print-errors", json=payload).status_code == 401
    assert client.post("/api/v1/print-errors", headers=other_user_headers, json=payload).status_code == 403
    assert client.post(
        "/api/v1/print-errors",
        headers=user_headers,
        json={**payload, "job_id": 99999},
    ).status_code == 404
    assert client.post(
        "/api/v1/print-errors",
        headers=user_headers,
        json={**payload, "error_type": "INVALID"},
    ).status_code == 422

    assert client.post("/api/v1/print-errors", headers=admin_headers, json=payload).status_code == 201
    filtered_errors = client.get(
        f"/api/v1/print-errors?job_id={job_id}",
        headers=admin_headers,
    )
    assert filtered_errors.status_code == 200
    assert len(filtered_errors.json()) == 1
    assert filtered_errors.json()[0]["job_id"] == job_id
