from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Print Bed Cable Guide"],
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        examples=["Guide for heatbed cable chain"],
    )
    is_completed: bool = Field(default=False)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_completed: Optional[bool] = None


class ItemResponse(ItemBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
