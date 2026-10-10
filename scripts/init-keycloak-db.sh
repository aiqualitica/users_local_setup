#!/bin/bash
set -e

# Create Keycloak database in the same PostgreSQL instance
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE keycloak;
    GRANT ALL PRIVILEGES ON DATABASE keycloak TO $POSTGRES_USER;
EOSQL

echo "✅ Keycloak database created successfully"
