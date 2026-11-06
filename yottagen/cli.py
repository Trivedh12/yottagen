"""Command Line Interface for YottaGen.

Subcommands:
- generate: Generate complete synthetic datasets (CSV, JSON, SQL, manifest)
- validate: Run structural and arithmetic invariant validation
- audit: Run independent rule detection engine and export audit findings
- evaluate: Evaluate audit findings against ground truth and produce operational KPIs
- repro-check: Execute bit-for-bit reproducibility tests across seeds
- all: Execute complete end-to-end generation, validation, audit, and evaluation pipeline
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional

from yottagen import __version__
from yottagen.audit import export_audit_findings_csv, run_audit
from yottagen.calendar import CalendarEngine, build_holiday_calendar
from yottagen.config import DEFAULT_SEED, SCALE_CONFIGS, ScaleConfig
from yottagen.evaluate import (
    evaluate_audit_results,
    generate_evaluation_report_json,
    generate_evaluation_report_md,
)
from yottagen.expense import generate_expense_module
from yottagen.export import export_dataset
from yottagen.injector import inject_anomalies
from yottagen.leave import generate_leave_module
from yottagen.master import generate_master_data
from yottagen.repro import run_reproducibility_check
from yottagen.schema import export_documentation
from yottagen.validate import (
    generate_validation_summary_json,
    generate_validation_summary_md,
    validate_dataset,
)
import random


def load_tables_from_dir(inputs_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load all JSON tables from an inputs directory."""
    tables: Dict[str, List[Dict[str, Any]]] = {}
    if not os.path.exists(inputs_dir):
        return tables
    for f in sorted(os.listdir(inputs_dir)):
        if f.endswith(".json"):
            tname = f[:-5]
            with open(os.path.join(inputs_dir, f), "r", encoding="utf-8") as fp:
                tables[tname] = json.load(fp)
    return tables


def load_ground_truth(gt_dir: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load ground truth and expected decisions from ground_truth directory."""
    gt_records = []
    exp_decisions = []
    gt_json = os.path.join(gt_dir, "ground_truth.json")
    if os.path.exists(gt_json):
        with open(gt_json, "r", encoding="utf-8") as f:
            gt_records = json.load(f)

    exp_json = os.path.join(gt_dir, "expected_decisions.json")
    if os.path.exists(exp_json):
        with open(exp_json, "r", encoding="utf-8") as f:
            exp_decisions = json.load(f)

    return gt_records, exp_decisions


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate complete synthetic dataset."""
    seed = args.seed
    scale_name = args.scale
    out_dir = args.out

    if scale_name in SCALE_CONFIGS:
        scale_cfg = SCALE_CONFIGS[scale_name]
    else:
        scale_cfg = ScaleConfig(
            name="custom",
            num_employees=args.employees or 40,
            num_leave_policies=6,
            num_leave_requests=args.leave_requests or 80,
            num_expense_claims=args.expense_claims or 100,
            target_anomalies_per_type=args.anomalies_per_type or 2,
        )

    print(f"Generating YottaGen dataset (Scale: {scale_cfg.name}, Seed: {seed})...")
    rng = random.Random(seed)

    holidays = build_holiday_calendar(2015, 2027)
    cal_engine = CalendarEngine(holidays)

    master = generate_master_data(scale_cfg, rng)
    leave = generate_leave_module(
        scale_cfg, master.employees, master.leave_policies, master.approval_rules, cal_engine, rng
    )
    expense = generate_expense_module(
        scale_cfg, master.employees, master.expense_policies, master.approval_rules, rng
    )
    inj = inject_anomalies(scale_cfg, master, leave, expense, rng)

    tables = {
        "cost_center": inj.master_bundle.cost_centers,
        "employee": inj.master_bundle.employees,
        "employee_cost_center_assignment": inj.master_bundle.employee_cost_center_assignments,
        "holiday_calendar": [
            {
                "holiday_id": h.holiday_id,
                "country": h.country,
                "holiday_date": h.holiday_date,
                "holiday_name": h.holiday_name,
                "is_half_day": h.is_half_day,
            }
            for h in holidays
        ],
        "leave_policy": inj.master_bundle.leave_policies,
        "expense_policy": inj.master_bundle.expense_policies,
        "approval_rule": inj.master_bundle.approval_rules,
        "approval_rule_category": inj.master_bundle.approval_rule_categories,
        "approval_rule_country": inj.master_bundle.approval_rule_countries,
        "leave_balance_ledger": inj.leave_bundle.ledger_entries,
        "leave_balance": inj.leave_bundle.balances,
        "leave_request": inj.leave_bundle.requests,
        "leave_request_event": inj.leave_bundle.events,
        "expense_claim": inj.expense_bundle.claims,
        "expense_line": inj.expense_bundle.lines,
        "expense_claim_event": inj.expense_bundle.events,
        "approval_step": inj.expense_bundle.approval_steps,
        "decision_log": inj.leave_bundle.decision_logs + inj.expense_bundle.decision_logs,
        "reimbursement": inj.expense_bundle.reimbursements,
    }

    manifest = export_dataset(
        output_dir=out_dir,
        tables=tables,
        ground_truth_records=inj.ground_truth_records,
        expected_decisions=inj.expected_decisions,
        seed=seed,
        scale_name=scale_cfg.name,
        command_str=f"python -m yottagen generate --seed {seed} --scale {scale_cfg.name} --out {out_dir}",
    )

    print(f"Dataset successfully exported to {out_dir}")
    print(f"Total Tables: {len(tables)} | Injected Anomalies: {len(inj.ground_truth_records)}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate invariant integrity on an exported dataset directory."""
    data_dir = args.data
    inputs_dir = os.path.join(data_dir, "inputs")
    gt_dir = os.path.join(data_dir, "ground_truth")

    tables = load_tables_from_dir(inputs_dir)
    gt_records, _ = load_ground_truth(gt_dir)

    summary = validate_dataset(tables, gt_records)

    md_content = generate_validation_summary_md(summary)
    json_content = generate_validation_summary_json(summary)

    docs_dir = getattr(args, "docs_dir", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "validation_summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md_content)
    with open(os.path.join(docs_dir, "validation_summary.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json_content)

    print(f"Validation completed. Verdict: {summary.overall_status} ({summary.passed_checks}/{summary.total_checks} passed)")
    return 0 if summary.overall_status == "PASS" else 1


def cmd_audit(args: argparse.Namespace) -> int:
    """Run independent audit engine against input tables."""
    data_dir = args.data
    inputs_dir = os.path.join(data_dir, "inputs")
    out_file = args.out or os.path.join(data_dir, "audit_findings.csv")

    tables = load_tables_from_dir(inputs_dir)
    findings = run_audit(tables)

    csv_out = export_audit_findings_csv(findings)
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(csv_out)

    print(f"Audit completed: {len(findings)} findings detected. Exported to {out_file}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Evaluate audit findings against ground truth and produce metrics."""
    data_dir = args.data
    inputs_dir = os.path.join(data_dir, "inputs")
    gt_dir = os.path.join(data_dir, "ground_truth")

    tables = load_tables_from_dir(inputs_dir)
    gt_records, exp_decisions = load_ground_truth(gt_dir)

    findings = run_audit(tables)
    decisions = tables.get("decision_log", [])
    steps = tables.get("approval_step", [])

    report = evaluate_audit_results(
        findings, gt_records, exp_decisions, decisions, steps, tables
    )

    md_report = generate_evaluation_report_md(report)
    json_report = generate_evaluation_report_json(report)

    docs_dir = getattr(args, "docs_dir", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "evaluation_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md_report)
    with open(os.path.join(docs_dir, "evaluation_report.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json_report)

    print(f"Evaluation completed. Macro F1: {report.macro_f1:.4f} | Micro F1: {report.micro_f1:.4f} | Decision Acc: {report.decision_accuracy:.4f}")
    return 0


def cmd_repro_check(args: argparse.Namespace) -> int:
    """Run byte-identical reproducibility checks."""
    seed = args.seed
    scale_name = args.scale
    report_path = args.out or "docs/reproducibility_report.md"

    print(f"Executing reproducibility checks across seeds (Primary: {seed}, Scale: {scale_name})...")
    ok, _ = run_reproducibility_check(
        seed=seed,
        scale_name=scale_name,
        report_output_path=report_path,
    )

    if ok:
        print(f"Reproducibility verification PASSED. Full report saved to {report_path}")
        return 0
    else:
        print(f"Reproducibility verification FAILED.")
        return 1


def cmd_all(args: argparse.Namespace) -> int:
    """Run end-to-end: schema docs, starter, full, validate, audit, evaluate, repro-check."""
    print("=== Step 1/6: Export Data Dictionary Documentation ===")
    export_documentation("docs")

    print("\n=== Step 2/6: Generate Starter Scale Dataset ===")
    args_starter = argparse.Namespace(
        seed=DEFAULT_SEED,
        scale="starter",
        out="data/starter",
        employees=None,
        leave_requests=None,
        expense_claims=None,
        anomalies_per_type=None,
    )
    cmd_generate(args_starter)

    print("\n=== Step 3/6: Generate Full Scale Dataset ===")
    args_full = argparse.Namespace(
        seed=DEFAULT_SEED,
        scale="full",
        out="data/full",
        employees=None,
        leave_requests=None,
        expense_claims=None,
        anomalies_per_type=None,
    )
    cmd_generate(args_full)

    print("\n=== Step 4/6: Validate Full Dataset ===")
    args_val = argparse.Namespace(data="data/full", docs_dir="docs")
    v_code = cmd_validate(args_val)
    if v_code != 0:
        return v_code

    print("\n=== Step 5/6: Audit & Evaluate Full Dataset ===")
    args_aud = argparse.Namespace(data="data/full", out="data/full/audit_findings.csv")
    cmd_audit(args_aud)

    args_eval = argparse.Namespace(data="data/full", docs_dir="docs")
    cmd_evaluate(args_eval)

    print("\n=== Step 6/6: Verify Bit-for-Bit Reproducibility ===")
    args_repro = argparse.Namespace(
        seed=DEFAULT_SEED,
        scale="starter",
        out="docs/reproducibility_report.md",
    )
    r_code = cmd_repro_check(args_repro)

    print("\nAll pipeline tasks completed successfully.")
    return r_code


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="yottagen",
        description="YottaGen: Deterministic Synthetic Corporate Governance Data Generator & Audit Engine",
    )
    parser.add_argument("--version", action="version", version=f"yottagen {__version__}")

    subparsers = parser.add_subparsers(dest="subcommand", help="Operational Subcommands")

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic dataset")
    gen_parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Pseudorandom seed (default: {DEFAULT_SEED})")
    gen_parser.add_argument("--scale", type=str, default="full", choices=["starter", "full", "custom"], help="Dataset scale profile")
    gen_parser.add_argument("--out", type=str, default="data/full", help="Output directory")
    gen_parser.add_argument("--employees", type=int, help="Custom employee count")
    gen_parser.add_argument("--leave-requests", type=int, help="Custom leave request count")
    gen_parser.add_argument("--expense-claims", type=int, help="Custom expense claim count")
    gen_parser.add_argument("--anomalies-per-type", type=int, help="Custom anomalies per type")

    # validate
    val_parser = subparsers.add_parser("validate", help="Validate relational and arithmetic invariants")
    val_parser.add_argument("--data", type=str, default="data/full", help="Path to dataset directory")
    val_parser.add_argument("--docs-dir", type=str, default="docs", help="Path to write validation_summary.md/.json")

    # audit
    aud_parser = subparsers.add_parser("audit", help="Run independent audit engine against input tables")
    aud_parser.add_argument("--data", type=str, default="data/full", help="Path to dataset directory")
    aud_parser.add_argument("--out", type=str, default="data/full/audit_findings.csv", help="Path for audit_findings.csv")

    # evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate audit findings against ground truth")
    eval_parser.add_argument("--data", type=str, default="data/full", help="Path to dataset directory")
    eval_parser.add_argument("--docs-dir", type=str, default="docs", help="Path to write evaluation_report.md/.json")

    # repro-check
    repro_parser = subparsers.add_parser("repro-check", help="Verify byte-identical reproducibility")
    repro_parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Reference seed")
    repro_parser.add_argument("--scale", type=str, default="starter", choices=["starter", "full"], help="Scale profile")
    repro_parser.add_argument("--out", type=str, default="docs/reproducibility_report.md", help="Report output path")

    # all
    subparsers.add_parser("all", help="Execute complete generation, validation, evaluation, and repro pipeline")

    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 1

    handlers = {
        "generate": cmd_generate,
        "validate": cmd_validate,
        "audit": cmd_audit,
        "evaluate": cmd_evaluate,
        "repro-check": cmd_repro_check,
        "all": cmd_all,
    }

    handler = handlers.get(args.subcommand)
    if not handler:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
