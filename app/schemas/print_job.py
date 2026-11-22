from datetime import datetime
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from app.models.print_job import PaymentStatus, PrintStatus


class PrintJobBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150, examples=["Spool Holder Bracket"])
    notes: Optional[str] = Field(None, max_length=1000, examples=["Print with 4 perimeters and 25% infill"])
    material: str = Field(default="PLA", max_length=50, examples=["PLA"])


class PrintJobResponse(PrintJobBase):
    id: int
    original_filename: str
    file_size_bytes: int
    estimated_weight_g: float
    estimated_time_hours: float
    estimated_price: int
    final_price: Optional[int] = None
    currency: str
    status: Union[PrintStatus, Literal["FAILED"]]
    payment_status: PaymentStatus
    stripe_session_id: Optional[str] = None
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrintJobAdminUpdate(BaseModel):
    final_price: Optional[int] = Field(None, ge=0, description="Corrected/approved price in grosze/cents")
    status: Optional[PrintStatus] = None
    payment_status: Optional[PaymentStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)


class PrintJobPaginationResponse(BaseModel):
    total: int
    items: List[PrintJobResponse]
    limit: int
    skip: int


class PrintPriceEstimateResponse(BaseModel):
    estimated_weight_g: float
    estimated_time_hours: float
    estimated_price: int
    currency: str = "PLN"
