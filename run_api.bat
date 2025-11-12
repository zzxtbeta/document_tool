@echo off
REM Knowledge Graph Extraction API Launcher
REM Windows batch script to start the FastAPI server

echo ========================================
echo Knowledge Graph Extraction API
echo ========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure your API keys.
    echo.
    pause
    exit /b 1
)

REM Check if DASHSCOPE_API_KEY is set
findstr /C:"DASHSCOPE_API_KEY" .env >nul
if errorlevel 1 (
    echo ERROR: DASHSCOPE_API_KEY not configured in .env
    pause
    exit /b 1
)

echo Starting API server...
echo.
echo Access documentation at: http://localhost:8000/docs
echo.

REM Start uvicorn
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

pause
