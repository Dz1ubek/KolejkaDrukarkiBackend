from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class PrintStatus(str, Enum):
    PENDING_REVIEW = "pending_review"  # Awaiting admin review / pricing confirmation
    READY_TO_PRINT = "ready_to_print"  # Approved / paid, waiting in queue
    PRINTING = "printing"              # Currently on the 3D printer
    COMPLETED = "completed"            # Finished, ready for pickup
    CANCELLED = "cancelled"            # Cancelled by user
    REJECTED = "rejected"              # Rejected by admin (e.g. unprintable geometry)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    material: Mapped[str] = mapped_column(String(50), default="PLA", nullable=False)

    # File storage metadata
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Print estimates (provided by user / slicer)
    estimated_weight_g: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    estimated_time_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Pricing (in grosze/cents, e.g. 1500 = 15.00 PLN)
    estimated_price: Mapped[int] = mapped_column(Integer, nullable=False)
    final_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="PLN", nullable=False)

    # Queue & Payment Statuses
    status: Mapped[str] = mapped_column(
        String(50),
        default=PrintStatus.PENDING_REVIEW.value,
        index=True,
        nullable=False,
    )
    payment_status: Mapped[str] = mapped_column(
        String(50),
        default=PaymentStatus.PENDING.value,
        index=True,
        nullable=False,
    )

    # Stripe readiness
    stripe_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped["User"] = relationship("User", backref="print_jobs")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PrintJob id={self.id} title={self.title} status={self.status} estimated_price={self.estimated_price}>"
