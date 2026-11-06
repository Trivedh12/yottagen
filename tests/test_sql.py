"""Tests for loading SQL schema and seed scripts into SQLite and verifying join integrity."""

import os
import sqlite3
import pytest
from yottagen.schema import SCHEMA_RELATIONSHIPS, TABLES_BY_NAME


def test_sqlite_schema_and_seed_load():
    sql_dir = "data/starter/sql"
    schema_path = os.path.join(sql_dir, "schema.sql")
    seed_path = os.path.join(sql_dir, "seed.sql")

    assert os.path.exists(schema_path), f"schema.sql not found at {schema_path}"
    assert os.path.exists(seed_path), f"seed.sql not found at {seed_path}"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with open(seed_path, "r", encoding="utf-8") as f:
        seed_sql = f.read()

    # Load in-memory SQLite
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Execute DDL
    cursor.executescript(schema_sql)

    # Execute Seed DML
    cursor.executescript(seed_sql)

    # Validate that every table has rows
    for tname in TABLES_BY_NAME.keys():
        cursor.execute(f"SELECT COUNT(*) FROM {tname};")
        cnt = cursor.fetchone()[0]
        assert cnt > 0, f"Table {tname} has 0 rows in SQLite seed!"


def test_sqlite_fk_join_integrity():
    sql_dir = "data/starter/sql"
    schema_path = os.path.join(sql_dir, "schema.sql")
    seed_path = os.path.join(sql_dir, "seed.sql")

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
    with open(seed_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # Test every relationship defined in SCHEMA_RELATIONSHIPS
    for rel in SCHEMA_RELATIONSHIPS:
        p_table = rel.parent_table
        c_table = rel.child_table
        fk_field = rel.fk_field
        p_pk = next(f.name for f in TABLES_BY_NAME[p_table].fields if f.pk)

        # Query total non-null/non-empty foreign keys in child table
        cursor.execute(
            f"SELECT COUNT(*) FROM {c_table} WHERE {fk_field} IS NOT NULL AND {fk_field} != '';"
        )
        expected_count = cursor.fetchone()[0]

        # Query inner join count
        cursor.execute(
            f"SELECT COUNT(*) FROM {c_table} c JOIN {p_table} p ON c.{fk_field} = p.{p_pk} WHERE c.{fk_field} IS NOT NULL AND c.{fk_field} != '';"
        )
        join_count = cursor.fetchone()[0]

        assert (
            join_count == expected_count
        ), f"FK join mismatch for {c_table}.{fk_field} -> {p_table}.{p_pk}: {join_count} != {expected_count}"
