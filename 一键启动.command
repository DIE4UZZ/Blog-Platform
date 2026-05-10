#!/bin/bash
# Blog-Platform 一键启动脚本
# 双击此文件即可启动项目

cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"

clear
echo "=========================================="
echo "   🚀 Blog-Platform 一键启动"
echo "=========================================="
echo ""

# 1. 检查并启动 MySQL
echo "[1/4] 检查 MySQL 服务..."
if brew services list 2>/dev/null | grep mysql | grep -q started; then
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

# 杀掉已有的后端进程
lsof -ti :8000 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

source "$PROJECT_DIR/venv/bin/activate"
cd "$PROJECT_DIR"
nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  ✅ 后端已启动 (PID: $BACKEND_PID)"

# 4. 启动前端
echo ""
echo "[4/4] 启动前端服务 (端口 5173)..."

# 杀掉已有的前端进程
lsof -ti :5173 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

cd "$PROJECT_DIR/frontend"
nohup npm run dev > "$PROJECT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  ✅ 前端已启动 (PID: $FRONTEND_PID)"

# 保存PID
echo "$BACKEND_PID" > "$PROJECT_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$PROJECT_DIR/.frontend.pid"

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
echo "=========================================="
echo ""

# 自动打开浏览器
open http://localhost:5173

echo "按任意键关闭所有服务并退出..."
read -n 1 -s

echo ""
echo "正在关闭服务..."
kill $BACKEND_PID 2>/dev/null
kill $FRONTEND_PID 2>/dev/null
lsof -ti :8000 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti :5173 2>/dev/null | xargs kill -9 2>/dev/null
echo "✅ 所有服务已关闭，再见！"
