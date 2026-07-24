#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${RESTORE_CONFIRMATION:?Set RESTORE_CONFIRMATION=RESTORE_ISOLATED_ENVIRONMENT}"

if [ "$RESTORE_CONFIRMATION" != "RESTORE_ISOLATED_ENVIRONMENT" ]; then
  printf 'Restore recusado: use somente ambiente isolado.\n' >&2
  exit 2
fi

sha256sum --check "$BACKUP_FILE.sha256"
pg_restore --exit-on-error --no-owner --no-acl --clean --if-exists \
  --dbname="$DATABASE_URL" "$BACKUP_FILE"
printf 'Restore concluído; execute smoke tests antes de promover o ambiente.\n'
