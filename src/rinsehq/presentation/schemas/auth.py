from __future__ import annotations

from typing import List, Optional, Union
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime
