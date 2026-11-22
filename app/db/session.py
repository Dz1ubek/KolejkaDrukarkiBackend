import os
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import settings

# SQLite requires check_same_thread=False for FastAPI concurrency
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and ensures it closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_first_admin(db: Session) -> None:
    """Idempotently seed the first administrator account if no admin accounts exist."""
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole

    admin_exists = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
    if not admin_exists and settings.FIRST_SUPERUSER_EMAIL and settings.FIRST_SUPERUSER_PASSWORD:
        first_admin = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            username=settings.FIRST_SUPERUSER_USERNAME,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        db.add(first_admin)
        db.commit()


def init_db(target_engine=None, db_session: Optional[Session] = None) -> None:
    """Create database tables and seed initial administrator if needed."""
    import app.models  # noqa: F401

    active_engine = target_engine or engine
    Base.metadata.create_all(bind=active_engine)

    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Seed initial superuser if configured
    if db_session:
        seed_first_admin(db_session)
    else:
        with SessionLocal() as session:
            seed_first_admin(session)
