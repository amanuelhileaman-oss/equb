#!/usr/bin/env bash
# ==============================================================================
# DIGITAL EQUB ETHIOPIA — ALL-IN-ONE APPLICATION LAUNCHER
# Starts PostgreSQL, Django Backend (port 8000), and Vite Frontend (port 5173)
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo "   STARTING DIGITAL EQUB ETHIOPIA APPLICATION     "
echo "=================================================="

# Function to kill child processes on Ctrl+C
cleanup() {
    echo ""
    echo "Stopping all Digital Equb services..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Local PostgreSQL Daemon (port 5433)
if [ -f "$PROJECT_DIR/scripts/start_postgres.sh" ]; then
    bash "$PROJECT_DIR/scripts/start_postgres.sh"
fi

# 2. Start Django Backend Server on port 8000
echo "Starting Django API Server on http://127.0.0.1:8000/ ..."
source "$PROJECT_DIR/.venv/bin/activate"
python "$PROJECT_DIR/backend/manage.py" runserver 127.0.0.1:8000 &
BACKEND_PID=$!

# Wait 2 seconds for Django to initialize
sleep 2

# Check if backend started successfully
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Error: Django backend failed to start. Check terminal output above."
    exit 1
fi
echo "[✓] Django backend is running (PID: $BACKEND_PID)"

# 3. Start Vite Frontend Server on port 5173
echo "Starting Vite Frontend on http://localhost:5173/ ..."
cd "$PROJECT_DIR/frontend"

# Use nvm node if available
export PATH="/home/amanuel/.nvm/versions/node/v22.23.3/bin:$PATH"

npm run dev

