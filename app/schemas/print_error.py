from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.print_error import PrintErrorType


class PrintErrorCreate(BaseModel):
    job_id: int = Field(..., gt=0)
    error_type: PrintErrorType
    description: str = Field(..., min_length=1)


class PrintErrorResponse(BaseModel):
    id: int
    job_id: int
    error_type: PrintErrorType
    description: str
    reported_by_user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
