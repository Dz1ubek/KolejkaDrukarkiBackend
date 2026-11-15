import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.user import User  # noqa: F401


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def register(client: TestClient, email: str, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "SecurePassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_registration_login_and_current_user(client):
    forbidden_role = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-attempt@example.com",
            "username": "admin_attempt",
            "password": "SecurePassword123!",
            "role": "admin",
        },
    )
    assert forbidden_role.status_code == 422

    oversized_password = client.post(
        "/api/v1/auth/register",
        json={
            "email": "long-password@example.com",
            "username": "long_password",
            "password": "€" * 25,
        },
    )
    assert oversized_password.status_code == 422

    user = register(client, "User@example.com", "regular_user")
    assert user["email"] == "user@example.com"
    assert user["role"] == "user"
    assert "hashed_password" not in user

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "username": "another_user",
            "password": "SecurePassword123!",
        },
    )
    assert duplicate.status_code == 409

    token = login(client, "USER@EXAMPLE.COM")
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]


def test_current_user_endpoint_requires_authentication(client):
    assert client.get("/api/v1/users/me").status_code == 401
