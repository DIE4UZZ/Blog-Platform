#!/bin/bash
# Blog-Platform 一键停止脚本 (macOS)

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "   Blog-Platform 停止服务"
echo "=========================================="

# 停止后端
echo ""
echo "[1/2] 停止后端服务..."
if [ -f "$PROJECT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_DIR/.backend.pid")
    kill "$BACKEND_PID" 2>/dev/null && echo "  ✅ 后端已停止 (PID: $BACKEND_PID)" || echo "  ⚠️  后端进程不存在"
    rm -f "$PROJECT_DIR/.backend.pid"
else
    lsof -ti :8000 | xargs kill -9 2>/dev/null && echo "  ✅ 后端已停止" || echo "  ⚠️  后端未在运行"
fi

# 停止前端
echo ""
echo "[2/2] 停止前端服务..."
if [ -f "$PROJECT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_DIR/.frontend.pid")
    kill "$FRONTEND_PID" 2>/dev/null && echo "  ✅ 前端已停止 (PID: $FRONTEND_PID)" || echo "  ⚠️  前端进程不存在"
    rm -f "$PROJECT_DIR/.frontend.pid"
else
    lsof -ti :5173 | xargs kill -9 2>/dev/null && echo "  ✅ 前端已停止" || echo "  ⚠️  前端未在运行"
fi

echo ""
echo "=========================================="
echo "   ✅ 所有服务已停止"
echo "=========================================="
echo ""
echo "  MySQL 服务仍在运行，如需停止请执行:"
echo "  brew services stop mysql"
echo "=========================================="
