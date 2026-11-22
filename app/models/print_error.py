from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PrintErrorType(str, Enum):
    FILAMENT_RUNOUT = "FILAMENT_RUNOUT"
    BED_ADHESION = "BED_ADHESION"
    NOZZLE_CLOG = "NOZZLE_CLOG"
    OTHER = "OTHER"


class PrintError(Base):
    __tablename__ = "print_errors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("print_jobs.id"),
        nullable=False,
        index=True,
    )
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reported_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job = relationship("PrintJob")
    reported_by_user = relationship("User")
