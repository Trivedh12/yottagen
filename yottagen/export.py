"""Deterministic export engine for YottaGen.

Exports:
- <out>/inputs/*.csv
- <out>/inputs/*.json
- <out>/ground_truth/ground_truth.csv
- <out>/ground_truth/ground_truth.json
- <out>/ground_truth/expected_decisions.csv
- <out>/ground_truth/expected_decisions.json
- <out>/sql/schema.sql (CREATE TABLE, PK, FK, INDEX)
- <out>/sql/seed.sql (INSERT INTO in dependency order)
- <out>/manifest.json (seed, version, scale, row counts, SHA-256 checksums)
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from yottagen import __version__
from yottagen.config import REFERENCE_DATE_STR
from yottagen.schema import SCHEMA_TABLES, TABLES_BY_NAME, generate_sql_ddl

# Tables in topological dependency order for SQL insertion
TOPOLOGICAL_TABLE_ORDER: List[str] = [
    "cost_center",
    "employee",
    "employee_cost_center_assignment",
    "holiday_calendar",
    "leave_policy",
    "leave_balance_ledger",
    "leave_balance",
    "leave_request",
    "leave_request_event",
    "expense_policy",
    "approval_rule",
    "approval_rule_category",
    "approval_rule_country",
    "expense_claim",
    "expense_line",
    "expense_claim_event",
    "approval_step",
    "decision_log",
    "reimbursement",
]


def compute_file_sha256(filepath: str) -> str:
    """Compute deterministic SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def format_sql_value(val: Any) -> str:
    """Format a Python value safely for standard SQL insertion."""
    if val is None or val == "":
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bool):
        return "1" if val else "0"
    # String escaping
    s = str(val).replace("'", "''")
    return f"'{s}'"


def export_dataset(
    output_dir: str,
    tables: Dict[str, List[Dict[str, Any]]],
    ground_truth_records: List[Any],
    expected_decisions: List[Dict[str, Any]],
    seed: int,
    scale_name: str,
    command_str: str = "python -m yottagen generate",
) -> Dict[str, Any]:
    """Export complete tabular dataset, ground truth, SQL scripts, and manifest."""
    inputs_dir = os.path.join(output_dir, "inputs")
    gt_dir = os.path.join(output_dir, "ground_truth")
    sql_dir = os.path.join(output_dir, "sql")

    os.makedirs(inputs_dir, exist_ok=True)
    os.makedirs(gt_dir, exist_ok=True)
    os.makedirs(sql_dir, exist_ok=True)

    row_counts: Dict[str, int] = {}

    # 1. Export inputs/*.csv and inputs/*.json
    for tdef in SCHEMA_TABLES:
        table_name = tdef.name
        rows = tables.get(table_name, [])
        row_counts[table_name] = len(rows)
        field_names = [f.name for f in tdef.fields]

        # CSV Export with fixed column order and newline="\n"
        csv_path = os.path.join(inputs_dir, f"{table_name}.csv")
        with open(csv_path, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(field_names)
            for r in rows:
                row_vals = [r.get(fn, "") for fn in field_names]
                writer.writerow(row_vals)

        # JSON Export with sorted keys and indent=2
        json_path = os.path.join(inputs_dir, f"{table_name}.json")
        with open(json_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(rows, f, indent=2)
            f.write("\n")

    # 2. Export ground_truth/ground_truth.csv and .json
    gt_dicts = [
        asdict(g) if hasattr(g, "__dataclass_fields__") else g for g in ground_truth_records
    ]
    row_counts["ground_truth"] = len(gt_dicts)

    gt_csv_path = os.path.join(gt_dir, "ground_truth.csv")
    if gt_dicts:
        gt_fields = list(gt_dicts[0].keys())
        with open(gt_csv_path, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(gt_fields)
            for g in gt_dicts:
                writer.writerow([g.get(fn, "") for fn in gt_fields])

    gt_json_path = os.path.join(gt_dir, "ground_truth.json")
    with open(gt_json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(gt_dicts, f, indent=2)
        f.write("\n")

    # 3. Export ground_truth/expected_decisions.csv and .json
    row_counts["expected_decisions"] = len(expected_decisions)
    exp_csv_path = os.path.join(gt_dir, "expected_decisions.csv")
    if expected_decisions:
        exp_fields = list(expected_decisions[0].keys())
        with open(exp_csv_path, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(exp_fields)
            for d in expected_decisions:
                writer.writerow([d.get(fn, "") for fn in exp_fields])

    exp_json_path = os.path.join(gt_dir, "expected_decisions.json")
    with open(exp_json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(expected_decisions, f, indent=2)
        f.write("\n")

    # 4. Export sql/schema.sql and sql/seed.sql
    schema_sql_path = os.path.join(sql_dir, "schema.sql")
    with open(schema_sql_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(generate_sql_ddl())
        f.write("\n")

    seed_sql_path = os.path.join(sql_dir, "seed.sql")
    with open(seed_sql_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- ============================================================================\n")
        f.write(f"-- YottaGen Database Seed SQL (Scale: {scale_name}, Seed: {seed})\n")
        f.write("-- ============================================================================\n")
        f.write("PRAGMA foreign_keys = OFF;\n")
        f.write("BEGIN TRANSACTION;\n\n")

        for table_name in TOPOLOGICAL_TABLE_ORDER:
            rows = tables.get(table_name, [])
            if not rows:
                continue
            tdef = TABLES_BY_NAME[table_name]
            field_names = [f.name for f in tdef.fields]
            f.write(f"-- Seed: {table_name} ({len(rows)} records)\n")

            for r in rows:
                vals_str = ", ".join(format_sql_value(r.get(fn)) for fn in field_names)
                cols_str = ", ".join(field_names)
                f.write(f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str});\n")
            f.write("\n")

        f.write("COMMIT;\n")
        f.write("PRAGMA foreign_keys = ON;\n")

    # 5. Build and export manifest.json
    manifest_path = os.path.join(output_dir, "manifest.json")
    checksums: Dict[str, str] = {}

    for root, _, files in os.walk(output_dir):
        for file in sorted(files):
            if file == "manifest.json":
                continue
            full_p = os.path.join(root, file)
            rel_p = os.path.relpath(full_p, output_dir).replace("\\", "/")
            checksums[rel_p] = compute_file_sha256(full_p)

    manifest_data = {
        "generator": "yottagen",
        "version": __version__,
        "seed": seed,
        "scale": scale_name,
        "reference_date": REFERENCE_DATE_STR,
        "command": command_str,
        "row_counts": row_counts,
        "checksums_sha256": checksums,
    }

    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest_data, f, indent=2)
        f.write("\n")

    return manifest_data
