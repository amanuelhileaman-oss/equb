#!/usr/bin/env bash
# Digital Equb Ethiopia - Start Local PostgreSQL Service
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_DIR="$BASE_DIR/.postgres_db"
SOCKETS_DIR="$BASE_DIR/.postgres_sockets"
PORT=5433

mkdir -p "$SOCKETS_DIR"

if /usr/lib/postgresql/18/bin/pg_isready -h "$SOCKETS_DIR" -p "$PORT" > /dev/null 2>&1; then
    echo "PostgreSQL is already running and accepting connections on socket $SOCKETS_DIR port $PORT."
    exit 0
fi

# Clean up stale locks if process is not running
rm -f "$DB_DIR/postmaster.pid" "$SOCKETS_DIR/.s.PGSQL.$PORT"*

echo "Starting PostgreSQL daemon on port $PORT..."
/usr/lib/postgresql/18/bin/postgres -D "$DB_DIR" -p "$PORT" -k "$SOCKETS_DIR" > /tmp/postgres_equb.log 2>&1 &
PID=$!

sleep 1
if /usr/lib/postgresql/18/bin/pg_isready -h "$SOCKETS_DIR" -p "$PORT" > /dev/null 2>&1; then
    echo "PostgreSQL successfully started (PID: $PID) on port $PORT."
else
    echo "Failed to start PostgreSQL. Check /tmp/postgres_equb.log for details."
    exit 1
fi
