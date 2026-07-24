#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_DIR:?BACKUP_DIR is required}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
mkdir -p "$BACKUP_DIR"
backup_file="$BACKUP_DIR/darkttk-$timestamp.dump"
manifest_file="$backup_file.sha256"

pg_dump --format=custom --no-owner --no-acl --file="$backup_file" "$DATABASE_URL"
sha256sum "$backup_file" > "$manifest_file"
pg_restore --list "$backup_file" >/dev/null

printf 'Backup verificado: %s\n' "$backup_file"
