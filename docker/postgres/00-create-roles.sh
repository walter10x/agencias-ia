#!/bin/sh
# ============================================================
# Crea el rol "authenticator" que usa PostgREST, con password
# tomada de la variable de entorno POSTGREST_AUTHENTICATOR_PASSWORD
# (NUNCA hardcodeada en SQL versionado).
#
# Este script corre automáticamente al iniciar el contenedor postgres
# (docker-entrypoint-initdb.d ejecuta todo *.sh y *.sql en orden
# alfabético). El prefijo "00-" garantiza que corra ANTES que init.sql,
# que asume que el rol ya existe (hace "GRANT web_anon TO authenticator").
#
# Requiere que el servicio "postgres" reciba la variable de entorno
# POSTGREST_AUTHENTICATOR_PASSWORD (inyectada en Dokploy / .env local).
# Si falta, se aborta el arranque para no crear un rol con password vacía
# o previsible.
# ============================================================
set -eu

if [ -z "${POSTGREST_AUTHENTICATOR_PASSWORD:-}" ]; then
  echo "ERROR: POSTGREST_AUTHENTICATOR_PASSWORD no está definida." >&2
  echo "Define esta variable de entorno (en Dokploy o en tu .env local)" >&2
  echo "antes de iniciar el contenedor postgres. Generar un valor con:" >&2
  echo "  openssl rand -hex 24" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE authenticator WITH LOGIN NOINHERIT PASSWORD '${POSTGREST_AUTHENTICATOR_PASSWORD}';
EOSQL
