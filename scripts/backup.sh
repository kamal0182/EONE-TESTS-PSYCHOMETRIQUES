#!/usr/bin/env bash
# Sauvegarde PostgreSQL d'EONE-Test (compressée), avec rotation.
#
#   ./scripts/backup.sh                      # sauvegarde dans ./backups, garde 14 jours
#   BACKUP_DIR=/srv/backups KEEP_DAYS=30 ./scripts/backup.sh
#
# Cron (tous les jours à 2 h) :
#   0 2 * * * cd /opt/eone-test && ./scripts/backup.sh >> backups/backup.log 2>&1
#
# Restauration :
#   gunzip -c backups/eone_test_XXXX.sql.gz | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
set -euo pipefail

cd "$(dirname "$0")/.."
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p "$BACKUP_DIR"

FILE="$BACKUP_DIR/eone_test_$(date +%Y%m%d_%H%M%S).sql.gz"
TMP="$FILE.part"

if docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip > "$TMP"; then
  mv "$TMP" "$FILE"
  echo "$(date '+%F %T') Sauvegarde OK : $FILE ($(du -h "$FILE" | cut -f1))"
else
  rm -f "$TMP"
  echo "$(date '+%F %T') ÉCHEC de la sauvegarde" >&2
  exit 1
fi

find "$BACKUP_DIR" -name 'eone_test_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
