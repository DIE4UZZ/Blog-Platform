#!/bin/bash
# Blog-Platform 一键启动脚本 (macOS)
# 使用方法: chmod +x start.sh && ./start.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "   Blog-Platform 一键启动"
echo "=========================================="

# 1. 检查并启动 MySQL
echo ""
echo "[1/4] 检查 MySQL 服务..."
if brew services list | grep mysql | grep -q started; then
    echo "  ✅ MySQL 已在运行"
else
    echo "  ⏳ 正在启动 MySQL..."
    brew services start mysql
    sleep 2
    echo "  ✅ MySQL 已启动"
fi

# 2. 确保数据库存在
echo ""
echo "[2/4] 检查数据库..."
mysql -u root -e "CREATE DATABASE IF NOT EXISTS blog_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
echo "  ✅ 数据库 blog_platform 已就绪"

# 3. 启动后端
echo ""
echo "[3/4] 启动后端服务 (端口 8000)..."
source "$PROJECT_DIR/venv/bin/activate"

# 先杀掉已有的后端进程
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

cd "$PROJECT_DIR"
nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  ✅ 后端已启动 (PID: $BACKEND_PID)"
echo "  📋 日志文件: $PROJECT_DIR/backend.log"

# 4. 启动前端
echo ""
echo "[4/4] 启动前端服务 (端口 5173)..."

# 先杀掉已有的前端进程
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
sleep 1

cd "$PROJECT_DIR/frontend"
nohup npm run dev > "$PROJECT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  ✅ 前端已启动 (PID: $FRONTEND_PID)"
echo "  📋 日志文件: $PROJECT_DIR/frontend.log"

# 等待服务就绪
echo ""
echo "⏳ 等待服务就绪..."
sleep 3

echo ""
echo "=========================================="
echo "   🎉 所有服务已启动！"
echo "=========================================="
echo ""
echo "  🌐 前端页面: http://localhost:5173"
echo "  🔧 后端 API: http://localhost:8000"
echo "  📖 API 文档: http://localhost:8000/docs"
echo ""
echo "  停止服务请运行: ./stop.sh"
echo "=========================================="

# 保存PID到文件，方便停止
echo "$BACKEND_PID" > "$PROJECT_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$PROJECT_DIR/.frontend.pid"

# 打开浏览器
open http://localhost:5173
