"""Tests for byte-identical reproducibility and seed sensitivity."""

import os
import pytest
from yottagen.repro import run_reproducibility_check


def test_reproducibility_check_starter():
    ok, report_content = run_reproducibility_check(
        seed=20261022,
        diff_seed=99999999,
        scale_name="starter",
        report_output_path="docs/reproducibility_report.md",
    )
    assert ok is True
    assert "**Overall Bit-for-Bit Determinism Result**: **PASS**" in report_content
    assert os.path.exists("docs/reproducibility_report.md")
