#!/usr/bin/env sh
set -e

DB_HOST="$1"; shift
CMD=("$@")

echo "⏳ Waiting for Postgres at ${DB_HOST}..."
until pg_isready -h "${DB_HOST}" -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  sleep 2
done

echo "✅ Postgres is up — running migrations"
alembic upgrade head

echo "🚀 Starting application: ${CMD[*]}"
exec "${CMD[@]}"