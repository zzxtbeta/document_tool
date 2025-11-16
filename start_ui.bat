@echo off
REM 音频转写 UI 前后端启动脚本

echo =============================================
echo  音频转写 UI - 启动脚本
echo =============================================
echo.

REM 启动后端服务
echo [1/2] 启动后端 API 服务...
start "后端服务 - localhost:8000" cmd /k "python -m uvicorn api:app --reload --port 8000"

REM 等待后端启动
echo 等待后端服务启动... (5秒)
timeout /t 5 /nobreak > nul

REM 启动前端服务
echo.
echo [2/2] 启动前端开发服务器...
start "前端服务 - localhost:5173" cmd /k "cd frontend && npm run dev"

echo.
echo =============================================
echo  启动完成!
echo =============================================
echo.
echo  后端 API:  http://localhost:8000
echo  前端界面:  http://localhost:5173
echo  API 文档:  http://localhost:8000/docs
echo.
echo  按任意键退出此窗口...
pause > nul
