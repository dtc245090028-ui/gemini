"""Pydantic Schemas cho Người dùng và Xác thực (Authentication)."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    WAREHOUSE_KEEPER = "WAREHOUSE_KEEPER"
    ACCOUNTANT = "ACCOUNTANT"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    full_name: str = Field(..., min_length=1, max_length=100, description="Họ và tên")
    role: UserRole = Field(default=UserRole.WAREHOUSE_KEEPER, description="Vai trò người dùng")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="Mật khẩu tài khoản")


class UserLogin(BaseModel):
    username: str = Field(..., description="Tên đăng nhập")
    password: str = Field(..., description="Mật khẩu")


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
