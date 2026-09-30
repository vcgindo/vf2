#!/bin/sh
set -eu

create_database() {
  database_name="$1"
  case "$database_name" in
    ''|*[!A-Za-z0-9_]*)
      echo "Invalid PostgreSQL database name" >&2
      exit 1
      ;;
  esac
  if ! psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align \
      --command "SELECT 1 FROM pg_database WHERE datname = '$database_name'" | grep -q 1; then
    psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      --command "CREATE DATABASE \"$database_name\""
  fi
}

create_database "$USER_SERVICE_DB_NAME"
create_database "$MTO_DB_NAME"
create_database "$MTA_TEST_DB_NAME"
