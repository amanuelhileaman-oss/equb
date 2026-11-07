#!/usr/bin/env bash
# ==============================================================================
# DIGITAL EQUB ETHIOPIA — AUTOMATED DATABASE BACKUP SCRIPT
# ==============================================================================
set -euo pipefail

BACKUP_DIR="/home/amanuel/Equb/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/digital_equb_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting Digital Equb database backup..."

# Use postgres pg_dump on user cluster (port 5433)
if command -v /usr/lib/postgresql/18/bin/pg_dump >/dev/null 2>&1; then
    PG_DUMP_BIN="/usr/lib/postgresql/18/bin/pg_dump"
else
    PG_DUMP_BIN="pg_dump"
fi

"${PG_DUMP_BIN}" -h 127.0.0.1 -p 5433 -U equb_admin digital_equb_db | gzip > "${BACKUP_FILE}"

FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup successfully completed: ${BACKUP_FILE} (${FILE_SIZE})"

# Prune backups older than RETENTION_DAYS
find "${BACKUP_DIR}" -type f -name "digital_equb_backup_*.sql.gz" -mtime +"${RETENTION_DAYS}" -exec rm -f {} \;
echo "[$(date)] Retention policy applied: Purged backups older than ${RETENTION_DAYS} days."
