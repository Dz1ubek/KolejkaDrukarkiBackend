import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.api.deps import get_current_active_admin, get_current_user
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.db.session import Base
from app.models.user import User, UserRole


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_password_hashing():
    raw_password = "SecretPassword123!"
    hashed = get_password_hash(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_cycle():
    user_id = "42"
    token = create_access_token(subject=user_id, extra_claims={"role": "admin"})
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == user_id
    assert decoded["role"] == "admin"


def test_user_creation_in_db(db_session):
    raw_password = "SecurePassword123!"
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash(raw_password),
        role=UserRole.USER.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert verify_password(raw_password, user.hashed_password) is True


def test_auth_dependencies(db_session):
    # Create regular user
    user = User(
        email="regular@example.com",
        username="regular",
        hashed_password=get_password_hash("pass"),
        role=UserRole.USER.value,
        is_active=True,
    )
    # Create admin user
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db_session.add_all([user, admin])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(admin)

    # Test get_current_user with valid token
    token = create_access_token(subject=user.id)
    retrieved_user = get_current_user(db=db_session, token=token)
    assert retrieved_user.id == user.id

    # Test regular user trying to access admin dependency
    with pytest.raises(HTTPException) as exc_info:
        get_current_active_admin(current_user=user)
    assert exc_info.value.status_code == 403

    # Test admin accessing admin dependency
    authorized_admin = get_current_active_admin(current_user=admin)
    assert authorized_admin.id == admin.id
