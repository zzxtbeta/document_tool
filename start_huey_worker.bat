@echo off
REM Huey Worker 启动脚本 (Windows)
REM 用于启动 PDF 提取任务的后台 worker 进程
REM 使用方式: 从项目根目录运行 .\scripts\start_huey_worker.bat

setlocal enabledelayedexpansion

REM 配置
set WORKERS=%HUEY_WORKERS%
if "!WORKERS!"=="" set WORKERS=5

set WORKER_TYPE=%HUEY_WORKER_TYPE%
if "!WORKER_TYPE!"=="" set WORKER_TYPE=thread

set LOG_LEVEL=%HUEY_LOG_LEVEL%
if "!LOG_LEVEL!"=="" set LOG_LEVEL=INFO

echo ==========================================
echo Starting Huey Worker for PDF Extraction
echo ==========================================
echo Workers: !WORKERS!
echo Worker Type: !WORKER_TYPE!
echo Log Level: !LOG_LEVEL!
echo.

REM 启动 Huey worker
REM -w: worker 数量
REM -k: worker 类型 (thread/process)
REM -v: verbose 日志
huey_consumer pipelines.queue_tasks.huey ^
    -w !WORKERS! ^
    -k !WORKER_TYPE! ^
    -v

echo.
echo Huey Worker stopped
pause
