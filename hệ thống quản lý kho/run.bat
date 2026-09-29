@echo off
chcp 65001 > nul
title Hệ Thống Quản Lý Kho Thông Minh Tích Hợp AI - WMS AI (Đề Tài 07)
echo ===============================================================================
echo     HỆ THỐNG QUẢN LÝ KHO THÔNG MINH TÍCH HỢP AI (ĐỀ TÀI 07)
echo               KHỞI CHẠY HỆ THỐNG 1-CLICK (WINDOWS)
echo ===============================================================================
echo.

:: 1. Khởi động Backend API Server (FastAPI)
echo [1/2] Đang khởi động Backend FastAPI Server tại cổng 8000...
start "WMS Backend (FastAPI)" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --reload --port 8000"

:: 2. Khởi động Frontend Web Application (React Vite)
echo [2/2] Đang khởi động Frontend Web Application tại cổng 5173...
start "WMS Frontend (React Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ===============================================================================
echo Hệ thống đã được kích hoạt thành công!
echo.
echo - Frontend Web Application:   http://localhost:5173
echo - Backend API Swagger UI:     http://localhost:8000/docs
echo - Backend ReDoc:              http://localhost:8000/redoc
echo.
echo Tài khoản mẫu để kiểm thử và chấm thi:
echo  1. Quản trị viên (Admin):    Tài khoản: admin    | Mật khẩu: admin123
echo  2. Thủ kho (Warehouse):      Tài khoản: thukho   | Mật khẩu: thukho123
echo  3. Kế toán (Accountant):     Tài khoản: ketoan   | Mật khẩu: ketoan123
echo.
echo (Trên giao diện Web có sẵn thanh "Chuyển vai trò Demo" để chuyển đổi 1-click)
echo ===============================================================================
pause
