"""Gom và đăng ký toàn bộ sub-routers cho API v1."""

from fastapi import APIRouter

api_router = APIRouter()

# Các sub-routers (auth, products, import_notes, export_notes, reports, ai)
# sẽ được đăng ký tại đây trong Giai đoạn 2, 3 và 4.
