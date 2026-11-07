#!/usr/bin/env bash
# Digital Equb Ethiopia - Start Django Backend Server
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1. Ensure PostgreSQL is active
"$BASE_DIR/scripts/start_postgres.sh"

# 2. Activate virtual environment
source "$BASE_DIR/.venv/bin/activate"

# 3. Start Django Server on port 8000
echo "Starting Django development server at http://127.0.0.1:8000/..."
python "$BASE_DIR/backend/manage.py" runserver 127.0.0.1:8000

