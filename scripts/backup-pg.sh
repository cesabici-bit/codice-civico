#!/usr/bin/env bash
# ==============================================================================
# Codice Civico — PostgreSQL Backup
#
# Usage (from host, via cron):
#   /opt/codice-civico/scripts/backup-pg.sh
#
# Cron entry (daily at 05:00 UTC):
#   0 5 * * * /opt/codice-civico/scripts/backup-pg.sh >> /var/log/cc-backup.log 2>&1
# ==============================================================================
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/codice-civico}"
BACKUP_DIR="${REPO_DIR}/backups"
COMPOSE_FILE="${REPO_DIR}/docker-compose.prod.yml"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/codicecivico_${TIMESTAMP}.sql.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup..."

# Dump via docker compose exec
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-codicecivico}" "${POSTGRES_DB:-codicecivico}" \
    | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup done: $BACKUP_FILE ($BACKUP_SIZE)"

# Remove backups older than retention period
DELETED=$(find "$BACKUP_DIR" -name "codicecivico_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned $DELETED old backups (>${RETENTION_DAYS} days)"
fi
