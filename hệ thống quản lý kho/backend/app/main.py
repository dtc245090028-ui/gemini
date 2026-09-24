"""Điểm khởi chạy ứng dụng FastAPI, đăng ký Middleware, Handlers và Router."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.seed import seed_default_users
import app.models  # Nạp toàn bộ models để Base.metadata nhận diện bảng
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời ứng dụng: Tự động khởi tạo cấu trúc bảng CSDL và nạp dữ liệu ban đầu."""
    # Tự động tạo các bảng CSDL nếu chưa tồn tại
    Base.metadata.create_all(bind=engine)

    # Tự động nạp dữ liệu tài khoản mặc định (Idempotent seed an toàn)
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()

    yield
    # Dọn dẹp tài nguyên khi tắt app nếu cần


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API cho Hệ thống Quản lý Kho Thông minh tích hợp AI (Đề tài 07)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Cấu hình CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers chuẩn hóa định dạng lỗi trả về tiếng Việt
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "detail": "Dữ liệu gửi lên không đúng định dạng hợp lệ.",
            "errors": exc.errors(),
            "error_code": "VALIDATION_ERROR",
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "detail": "Dữ liệu vi phạm ràng buộc toàn vẹn cơ sở dữ liệu (trùng lặp mã duy nhất hoặc vi phạm ràng buộc kiểm tra dữ liệu).",
            "error_code": "INTEGRITY_ERROR",
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "detail": "Đã xảy ra lỗi tương tác cơ sở dữ liệu.",
            "error_code": "DATABASE_ERROR",
        },
    )


# Đăng ký API Router v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Cấu hình Static Files phục vụ ảnh sản phẩm và tài nguyên tĩnh
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "products").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["Hệ thống"])
def root():
    """Endpoint gốc thông báo thông tin hệ thống."""
    return {
        "success": True,
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["Hệ thống"])
def health_check():
    """Health check endpoint kiểm tra trạng thái hoạt động."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
