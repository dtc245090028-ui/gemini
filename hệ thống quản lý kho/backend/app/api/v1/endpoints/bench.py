import os
import time
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import anyio.to_thread

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import User
from app.core.write_gate import WriteGateContext
from app.core.bench_metrics import bench_traffic

router = APIRouter(dependencies=[Depends(require_roles(["ADMIN"]))])

@router.get("/empty-async", summary="Benchmark rỗng - Pure Async (0 DB, 0 Threadpool, 0 Auth)")
async def empty_async():
    return {"status": "ok", "mode": "empty_async"}

@router.get("/empty-sync", summary="Benchmark rỗng - Sync Def (0 DB, 0 Auth, có AnyIO Threadpool)")
def empty_sync():
    return {"status": "ok", "mode": "empty_sync"}

@router.get("/auth-async", summary="Benchmark Auth - Async Def (Có Auth JWT, 0 Threadpool)")
async def auth_async(current_user: User = Depends(get_current_user)):
    return {"status": "ok", "mode": "auth_async", "user": current_user.username}

@router.get("/auth-sync", summary="Benchmark Auth - Sync Def (Có Auth JWT, có AnyIO Threadpool)")
def auth_sync(current_user: User = Depends(get_current_user)):
    return {"status": "ok", "mode": "auth_sync", "user": current_user.username}

@router.post("/write-gate", summary="Benchmark Write Gate (Có Write Gate FIFO, không ghi DB)")
def write_gate_bench(request: Request, db: Session = Depends(get_db)):
    arrival_t = getattr(request.state, "arrival_time", None)
    with WriteGateContext(arrival_time=arrival_t, db=db):
        return {"status": "ok", "mode": "write_gate"}

@router.get("/traffic-stats", summary="Thống kê lưu lượng đến/đi theo giây và AnyIO Limiter")
def get_traffic_stats():
    return bench_traffic.get_stats()

@router.post("/reset", summary="Reset bộ đếm lưu lượng và limiter")
def reset_traffic_stats():
    bench_traffic.reset()
    return {"status": "ok"}

@router.post("/set-limiter-tokens", summary="Cấu hình số AnyIO threadpool tokens")
async def set_limiter_tokens(tokens: int):
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = tokens
    return {"status": "ok", "total_tokens": limiter.total_tokens}
