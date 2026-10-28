@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

title Kho Công Nghệ WMS AI - 1-Click Startup

echo ===============================================================================
echo     HỆ THỐNG QUẢN LÝ KHO THÔNG MINH TÍCH HỢP AI (ĐỀ TÀI 07)
echo               KHỞI CHẠY HỆ THỐNG 1-CLICK (WINDOWS)
echo ===============================================================================
echo.

:: 1. KIỂM TRA MÔI TRƯỜNG PYTHON & NODE.JS
echo [BƯỚC 1/4] Kiểm tra môi trường hệ thống...

where python >nul 2>nul
if !errorlevel! neq 0 (
    echo [LỖI] Không tìm thấy Python trên máy tính.
    echo Vui lòng cài đặt Python 3.10 trở lên và tích chọn "Add Python to PATH".
    echo Tải về tại: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set PYTHON_VER=%%a
echo  + Python đã cài đặt: !PYTHON_VER!

where node >nul 2>nul
if !errorlevel! neq 0 (
    echo [LỖI] Không tìm thấy Node.js trên máy tính.
    echo Vui lòng cài đặt Node.js 18 trở lên.
    echo Tải về tại: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=1 delims= " %%a in ('node --version 2^>^&1') do set NODE_VER=%%a
echo  + Node.js đã cài đặt: !NODE_VER!
echo.

:: 2. THIẾT LẬP BACKEND (VENV, DEPENDENCIES, DATABASE)
echo [BƯỚC 2/4] Thiết lập môi trường Backend...
cd /d "%~dp0backend"

if not exist "%~dp0backend\.venv\Scripts\activate.bat" (
    echo  + Đang tạo môi trường ảo Python venv tại backend\.venv...
    python -m venv --system-site-packages "%~dp0backend\.venv"
    if !errorlevel! neq 0 (
        python -m venv "%~dp0backend\.venv"
    )
)

call "%~dp0backend\.venv\Scripts\activate.bat"
python -c "import fastapi, uvicorn, openpyxl, sqlalchemy" >nul 2>nul
if !errorlevel! neq 0 (
    echo  + Đang cài đặt thư viện Backend từ requirements.txt...
    python -m pip install -r "%~dp0backend\requirements.txt"
) else (
    echo  + Thư viện Backend đã sẵn sàng.
)

:: Kiểm tra database
if not exist "%~dp0backend\warehouse.db" (
    echo  + Chưa có database. Đang nạp dữ liệu mẫu 5 tháng (seed_data.py)...
    python "%~dp0backend\seed_data.py"
) else (
    echo  + Database warehouse.db đã tồn tại (bảo toàn dữ liệu hiện có).
)
echo.

:: 3. THIẾT LẬP FRONTEND (NODE_MODULES)
echo [BƯỚC 3/4] Thiết lập môi trường Frontend...
cd /d "%~dp0frontend"

if not exist "%~dp0frontend\node_modules" (
    echo  + Đang cài đặt thư viện Frontend qua npm install (chỉ cần chạy lần đầu)...
    call npm install
) else (
    echo  + Thư viện Frontend (node_modules) đã sẵn sàng.
)
echo.

:: 4. KHỞI ĐỘNG CÁC DỊCH VỤ
echo [BƯỚC 4/4] Khởi động các dịch vụ và mở trình duyệt...

:: Khởi động FastAPI server
echo  + Khởi động Backend FastAPI tại http://127.0.0.1:8000 ...
start "WMS Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && call "%~dp0backend\.venv\Scripts\activate.bat" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Khởi động Vite frontend server
echo  + Khởi động Frontend Vite tại http://localhost:5173 ...
start "WMS Frontend (React Vite)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: Đợi 3 giây để Backend khởi động xong
timeout /t 3 /nobreak >nul

:: Tự động mở trình duyệt web
start http://localhost:5173

echo.
echo ===============================================================================
echo                HỆ THỐNG ĐÃ ĐƯỢC KHỞI ĐỘNG THÀNH CÔNG!
echo ===============================================================================
echo - Giao diện Web:          http://localhost:5173
echo - Backend API Docs:       http://localhost:8000/docs
echo - Backend ReDoc:          http://localhost:8000/redoc
echo.
echo Tài khoản đăng nhập mẫu:
echo  1. Quản trị viên (Admin):    admin    / admin123
echo  2. Thủ kho (Warehouse):      thukho   / thukho123
echo  3. Kế toán (Accountant):     ketoan   / ketoan123
echo.
echo (Cửa sổ terminal Backend và Frontend đang chạy độc lập ở chế độ nền.)
echo ===============================================================================
pause
