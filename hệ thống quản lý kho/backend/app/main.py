"""Điểm khởi chạy ứng dụng FastAPI, đăng ký Middleware, Handlers và Router."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

import time
from app.core.config import settings
from app.core.metrics import write_metrics, StageTiming
from app.core.bench_metrics import bench_traffic
from app.core.events import broadcaster
from app.core.database import engine, Base, SessionLocal
from app.core.seed import seed_default_users
import app.models  # Nạp toàn bộ models để Base.metadata nhận diện bảng
from app.api.v1.api import api_router
from app.core.http_cache import ETagMiddleware, SelectiveGZipMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send, Message
from fastapi.encoders import jsonable_encoder


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    broadcaster.set_loop(asyncio.get_running_loop())
    """Quản lý vòng đời ứng dụng: Tự động khởi tạo cấu trúc bảng CSDL và nạp dữ liệu ban đầu."""
    # Tự động tạo các bảng CSDL nếu chưa tồn tại
    Base.metadata.create_all(bind=engine)

    # Tự động migrate an toàn các cột mới nếu CSDL đã tồn tại trước đó
    from sqlalchemy import inspect, text
    with engine.connect() as conn:
        inspector = inspect(conn)
        for table_name in ["import_notes", "export_notes", "stock_ledger"]:
            if inspector.has_table(table_name):
                columns = [c["name"] for c in inspector.get_columns(table_name)]
                if "idempotency_key" not in columns:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN idempotency_key VARCHAR(100)"))
                    conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table_name}_idempotency_key ON {table_name} (idempotency_key)"))
                    conn.commit()
        if inspector.has_table("products"):
            prod_cols = [c["name"] for c in inspector.get_columns("products")]
            if "supplier_id" not in prod_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_supplier_id ON products (supplier_id)"))
                conn.commit()

    # Tự động nạp dữ liệu tài khoản mặc định (Idempotent seed an toàn)
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()

    # Cấu hình AnyIO threadpool limiter nếu có env ANYIO_TOTAL_TOKENS
    anyio_tokens = int(os.environ.get("ANYIO_TOTAL_TOKENS", "40"))
    try:
        import anyio.to_thread
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = anyio_tokens
    except Exception:
        pass

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

class WriteArrivalMiddleware:
    """Pure ASGI Middleware: ghi nhận arrival_time, lưu lượng đến/đi và AnyIO threadpool limiter."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            bench_traffic.record_arrival()
            bench_traffic.sample_limiter()

            st = None
            if scope.get("method") in ("POST", "PUT", "PATCH", "DELETE"):
                t_arrival = time.perf_counter()
                scope.setdefault("state", {})
                scope["state"]["arrival_time"] = t_arrival
                if write_metrics.enabled:
                    st = StageTiming()
                    st.t_arrival = t_arrival
                    scope["state"]["stage_timing"] = st

            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    bench_traffic.record_completion()
                    if st is not None:
                        st.t_response_done = time.perf_counter()
                        write_metrics.record_stages(st)
                await send(message)

            await self.app(scope, receive, send_wrapper)
            return

        await self.app(scope, receive, send)


app.add_middleware(WriteArrivalMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bước E2: Tối ưu đọc với GZip & ETag Middleware
app.add_middleware(SelectiveGZipMiddleware, minimum_size=1000)
app.add_middleware(ETagMiddleware)


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
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "detail": "Dữ liệu gửi lên không đúng định dạng hợp lệ.",
            "errors": jsonable_encoder(exc.errors()),
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


logger = logging.getLogger("app.database")


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        f"[DATABASE ERROR] {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    is_locked = "database is locked" in str(exc).lower() or "busy" in str(exc).lower()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "detail": (
                "Cơ sở dữ liệu đang bận xử lý nhiều giao dịch ghi đồng thời. Vui lòng thử lại sau giây lát."
                if is_locked
                else "Đã xảy ra lỗi tương tác cơ sở dữ liệu."
            ),
            "error_code": "DATABASE_BUSY" if is_locked else "DATABASE_ERROR",
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
