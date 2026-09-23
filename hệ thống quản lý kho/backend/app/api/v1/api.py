"""Gom và đăng ký toàn bộ sub-routers cho API v1."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    ai,
    auth,
    categories,
    export_notes,
    import_notes,
    products,
    reports,
    stock_ledger,
    suppliers,
)

api_router = APIRouter()

# Đăng ký các sub-routers
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(suppliers.router)
api_router.include_router(import_notes.router)
api_router.include_router(export_notes.router)
api_router.include_router(stock_ledger.router)
api_router.include_router(reports.router)
api_router.include_router(ai.router)

