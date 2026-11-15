from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    email: str = Field(..., max_length=255, examples=["user@example.com"])
    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    role: UserRole = Field(default=UserRole.USER, examples=[UserRole.USER])
    is_active: bool = Field(default=True)


class UserCreate(BaseModel):
    email: str = Field(..., max_length=255, examples=["user@example.com"])
    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    password: str = Field(..., min_length=6, max_length=100, examples=["StrongPassword123!"])
    role: Optional[UserRole] = Field(default=UserRole.USER)


class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
