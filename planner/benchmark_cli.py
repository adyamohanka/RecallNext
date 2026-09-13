"""Write deterministic sequential benchmark artifacts."""
from __future__ import annotations

import json
from pathlib import Path

from .sequential_benchmark import run_sequential_benchmark


def main() -> None:
    result = run_sequential_benchmark()
    output = Path("docs/evaluation-results")
    output.mkdir(parents=True, exist_ok=True)
    (output / "sequential-benchmark.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = ["# Sequential benchmark", "", "Synthetic deterministic benchmark. Committed artifacts omit machine-dependent wall-clock timings; they are not warehouse or database measurements.", "", f"- Truth cases: {result['truth_case_count']}", f"- Budgets: {', '.join(map(str, result['budgets']))} minutes", f"- Seeds: {', '.join(map(str, result['seeds']))}", f"- Runs: {len(result['runs'])}", "", "| Strategy | Runs | Mean resolved cases | Mean simulated minutes | False excluded cases |", "|---|---:|---:|---:|---:|"]
    for strategy in result["strategies"]:
        runs = [item for item in result["runs"] if item["strategy"] == strategy]
        lines.append(f"| {strategy} | {len(runs)} | {sum(item['resolved_cases'] for item in runs) / len(runs):.2f} | {sum(item['simulated_minutes'] for item in runs) / len(runs):.2f} | {sum(item['false_excluded_cases'] for item in runs)} |")
    (output / "sequential-benchmark.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
