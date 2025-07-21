#!/usr/bin/env bash
set -euo pipefail

# where to store
BACKUP_DIR=/home/azureuser/db-backups
TIMESTAMP=$(date +"%F_%H%M")
FILENAME=fastapi_db_${TIMESTAMP}.sql.gz

# run pg_dump inside your Postgres container and gzip it
docker exec -i adet-backend-db-1 \
  pg_dump -U postgres -d fastapi_db | gzip > "${BACKUP_DIR}/${FILENAME}"

# rotate: delete dumps older than 7 days
find "${BACKUP_DIR}" -type f -name 'fastapi_db_*.sql.gz' -mtime +7 -delete
