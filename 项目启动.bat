@echo off
:: 核心：强制设置控制台为UTF-8编码 + 脚本保存为ANSI格式（关键）
chcp 65001 >nul 2>&1
:: 设置控制台字体（可选，增强兼容性）
reg add "HKCU\Console" /v "CodePage" /t REG_DWORD /d 65001 /f >nul 2>&1
reg add "HKCU\Console" /v "FaceName" /t REG_SZ /d "Consolas" /f >nul 2>&1
reg add "HKCU\Console" /v "FontFamily" /t REG_DWORD /d 54 /f >nul 2>&1
reg add "HKCU\Console" /v "FontSize" /t REG_DWORD /d 10485760 /f >nul 2>&1
title 博客平台启动脚本

:: ==================== 启动后端服务 ====================
echo [1/3] 正在启动后端服务（FastAPI+Uvicorn）...
start "后端服务" cmd /k "cd /d F:\Blog-Platform && python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"

:: 延迟5秒，确保后端服务初始化完成
timeout /t 5 /nobreak >nul

:: ==================== 启动前端服务 ====================
echo [2/3] 正在启动前端服务（npm dev）...
start "前端服务" cmd /k "cd /d F:\Blog-Platform\frontend && npm run dev"

:: 延迟8秒，确保前端服务启动并监听端口
timeout /t 8 /nobreak >nul

:: ==================== 自动打开网页（修复核心：用start "" 包裹网址） ====================
echo [3/3] 正在打开登录页面 http://localhost:5173/login...
start "" "http://localhost:5173/login"

echo ==================================================
echo  操作完成！
echo - 后端服务窗口：已启动（端口8000）
echo - 前端服务窗口：已启动（端口5173）
echo - 浏览器已打开：http://localhost:5173/login
echo ==================================================
pause >nul