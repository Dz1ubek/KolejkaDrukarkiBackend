import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.security import create_access_token, get_password_hash
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
def test_setup():
    """Sets up an isolated in-memory database and TestClient with overridden get_db."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_db = TestingSessionLocal()

    # Create admin user
    admin_user = User(
        email="admin@test.com",
        username="admin_user",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    # Create regular user
    regular_user = User(
        email="regular@test.com",
        username="regular_user",
        hashed_password=get_password_hash("UserPass123!"),
        role=UserRole.USER.value,
        is_active=True,
    )
    # Create extra user for pagination/search testing
    extra_user = User(
        email="inactive@test.com",
        username="inactive_bob",
        hashed_password=get_password_hash("UserPass123!"),
        role=UserRole.USER.value,
        is_active=False,
    )
    seed_db.add_all([admin_user, regular_user, extra_user])
    seed_db.commit()
    seed_db.refresh(admin_user)
    seed_db.refresh(regular_user)
    seed_db.refresh(extra_user)

    admin_id = admin_user.id
    regular_id = regular_user.id
    extra_id = extra_user.id
    seed_db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    admin_token = create_access_token(subject=admin_id)
    regular_token = create_access_token(subject=regular_id)

    client = TestClient(app)

    yield {
        "client": client,
        "admin_id": admin_id,
        "regular_id": regular_id,
        "extra_id": extra_id,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "regular_headers": {"Authorization": f"Bearer {regular_token}"},
    }

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_list_users(test_setup):
    client = test_setup["client"]
    headers = test_setup["admin_headers"]

    # List all users
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Test search filter
    search_res = client.get("/api/v1/admin/users?search=bob", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["items"][0]["username"] == "inactive_bob"

    # Test role filter
    role_res = client.get("/api/v1/admin/users?role=admin", headers=headers)
    assert role_res.status_code == 200
    assert role_res.json()["total"] == 1
    assert role_res.json()["items"][0]["role"] == "admin"

    # Test is_active filter
    active_res = client.get("/api/v1/admin/users?is_active=false", headers=headers)
    assert active_res.status_code == 200
    assert active_res.json()["total"] == 1
    assert active_res.json()["items"][0]["username"] == "inactive_bob"

    # Test pagination limit
    limit_res = client.get("/api/v1/admin/users?limit=1&skip=0", headers=headers)
    assert limit_res.status_code == 200
    assert len(limit_res.json()["items"]) == 1
    assert limit_res.json()["total"] == 3


def test_get_user_by_id(test_setup):
    client = test_setup["client"]
    headers = test_setup["admin_headers"]
    regular_id = test_setup["regular_id"]

    response = client.get(f"/api/v1/admin/users/{regular_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == regular_id
    assert data["username"] == "regular_user"

    # Not found
    not_found = client.get("/api/v1/admin/users/9999", headers=headers)
    assert not_found.status_code == 404


def test_update_user_role(test_setup):
    client = test_setup["client"]
    headers = test_setup["admin_headers"]
    regular_id = test_setup["regular_id"]
    admin_id = test_setup["admin_id"]

    # Promote regular user to admin
    promote_res = client.patch(
        f"/api/v1/admin/users/{regular_id}/role",
        headers=headers,
        json={"role": "admin"},
    )
    assert promote_res.status_code == 200
    assert promote_res.json()["role"] == "admin"

    # Admin cannot alter own role
    self_role_res = client.patch(
        f"/api/v1/admin/users/{admin_id}/role",
        headers=headers,
        json={"role": "user"},
    )
    assert self_role_res.status_code == 400


def test_update_user_status(test_setup):
    client = test_setup["client"]
    headers = test_setup["admin_headers"]
    regular_id = test_setup["regular_id"]
    admin_id = test_setup["admin_id"]

    # Deactivate regular user
    deactivate_res = client.patch(
        f"/api/v1/admin/users/{regular_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_res.status_code == 200
    assert deactivate_res.json()["is_active"] is False

    # Admin cannot deactivate self
    self_status_res = client.patch(
        f"/api/v1/admin/users/{admin_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert self_status_res.status_code == 400


def test_delete_user(test_setup):
    client = test_setup["client"]
    headers = test_setup["admin_headers"]
    regular_id = test_setup["regular_id"]
    admin_id = test_setup["admin_id"]

    # Delete regular user
    del_res = client.delete(f"/api/v1/admin/users/{regular_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_res = client.get(f"/api/v1/admin/users/{regular_id}", headers=headers)
    assert get_res.status_code == 404

    # Admin cannot delete self
    self_del_res = client.delete(f"/api/v1/admin/users/{admin_id}", headers=headers)
    assert self_del_res.status_code == 400


def test_admin_endpoints_forbidden_for_regular_users(test_setup):
    client = test_setup["client"]
    regular_headers = test_setup["regular_headers"]

    # Attempt to list users
    res = client.get("/api/v1/admin/users", headers=regular_headers)
    assert res.status_code == 403

    # Attempt to update role
    res = client.patch(
        "/api/v1/admin/users/1/role",
        headers=regular_headers,
        json={"role": "admin"},
    )
    assert res.status_code == 403


def test_admin_endpoints_unauthorized_without_token(test_setup):
    client = test_setup["client"]

    res = client.get("/api/v1/admin/users")
    assert res.status_code == 401
