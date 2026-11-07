#!/usr/bin/env bash
# ==============================================================================
# DIGITAL EQUB ETHIOPIA — PRODUCTION BUILD SCRIPT (RENDER / CLOUD DEPLOYMENT)
# ==============================================================================
set -o errexit

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Collecting static assets..."
python backend/manage.py collectstatic --noinput

echo "Applying database migrations..."
python backend/manage.py migrate --noinput

echo "[✓] Build script completed successfully."
