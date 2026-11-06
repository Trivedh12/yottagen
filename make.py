"""Cross-platform Makefile runner for systems without GNU Make."""

import subprocess
import sys

TARGETS = {
    "setup": [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
    "generate": [
        [sys.executable, "-m", "yottagen", "generate", "--seed", "20261022", "--scale", "starter", "--out", "data/starter"],
        [sys.executable, "-m", "yottagen", "generate", "--seed", "20261022", "--scale", "full", "--out", "data/full"],
    ],
    "validate": [sys.executable, "-m", "yottagen", "validate", "--data", "data/full", "--docs-dir", "docs"],
    "audit": [sys.executable, "-m", "yottagen", "audit", "--data", "data/full", "--out", "data/full/audit_findings.csv"],
    "evaluate": [sys.executable, "-m", "yottagen", "evaluate", "--data", "data/full", "--docs-dir", "docs"],
    "test": [sys.executable, "-m", "pytest", "-v"],
    "repro": [sys.executable, "-m", "yottagen", "repro-check", "--seed", "20261022", "--scale", "starter", "--out", "docs/reproducibility_report.md"],
}


def run_target(target: str) -> int:
    if target == "all":
        for step in ["generate", "validate", "audit", "evaluate", "test", "repro"]:
            print(f"\n>>> Running target: {step}")
            ret = run_target(step)
            if ret != 0:
                return ret
        print("\nAll Makefile targets completed successfully.")
        return 0

    commands = TARGETS.get(target)
    if not commands:
        print(f"Unknown target: '{target}'. Available: {list(TARGETS.keys()) + ['all']}")
        return 1

    if isinstance(commands[0], list):
        for cmd in commands:
            print(" ".join(cmd))
            ret = subprocess.call(cmd)
            if ret != 0:
                return ret
        return 0
    else:
        print(" ".join(commands))
        return subprocess.call(commands)


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "all"
    sys.exit(run_target(t))
