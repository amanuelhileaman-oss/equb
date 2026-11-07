#!/usr/bin/env bash
# ==============================================================================
# DIGITAL EQUB ETHIOPIA — PRODUCTION BUILD SCRIPT (RENDER / CLOUD DEPLOYMENT)
# ==============================================================================
set -o errexit

echo "Installing Python dependencies and Gunicorn..."
pip install --upgrade pip
pip install -r requirements.txt gunicorn

echo "Collecting static assets..."
python backend/manage.py collectstatic --noinput

echo "Applying database migrations..."
python backend/manage.py migrate --noinput

echo "Seeding system roles, default plans, and platform admin..."
python backend/manage.py seed_initial_data

echo "[✓] Build script completed successfully."
