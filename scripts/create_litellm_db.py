#!/usr/bin/env python3
"""Create the LiteLLM Postgres database once.

Run from the host after Postgres is up, the same way as init_versioning_db.py.
Uses DB_HOST, DB_PORT, DB_USER, and DB_PASSWORD. Exits without changes when the
database already exists. Connects to the maintenance database (postgres), not
testcase_db.
"""

import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def _database_name() -> str:
    name = os.environ.get("LITELLM_DB_NAME", "litellm").strip() or "litellm"
    if not name.replace("_", "").isalnum():
        print(f"invalid database name: {name}", file=sys.stderr)
        sys.exit(1)
    return name


def main() -> None:
    db_name = _database_name()
    host = os.environ.get("DB_HOST", "localhost").strip() or "localhost"
    port = os.environ.get("DB_PORT", "5432").strip() or "5432"
    user = os.environ.get("DB_USER", "postgres").strip() or "postgres"
    password = os.environ.get("DB_PASSWORD", "password")

    connection = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname="postgres",
    )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cursor.fetchone():
            print(f"database {db_name} already exists")
            return
        cursor.execute(f'CREATE DATABASE "{db_name}"')
        print(f"created database {db_name}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
