import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_demo_data  # noqa: E402
from src.risk_flags import detect_risk_flags  # noqa: E402


def main() -> None:
    data = load_demo_data(PROJECT_ROOT / "data")
    expected_flags_path = PROJECT_ROOT / "eval" / "expected_flags.json"
    results_path = PROJECT_ROOT / "eval" / "evaluation_results.csv"

    expected = set(json.loads(expected_flags_path.read_text(encoding="utf-8")))
    generated = {
        flag["id"]
        for flag in detect_risk_flags(
            data.constituents,
            data.factor_scores,
            data.backtest_metrics,
        )
    }

    missing = sorted(expected - generated)
    unexpected = sorted(generated - expected)
    passed = not missing and not unexpected

    with results_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "run_id",
                "expected_flags",
                "generated_flags",
                "missing_flags",
                "unexpected_flags",
                "passed",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "run_id": "starter_demo",
                "expected_flags": "|".join(sorted(expected)),
                "generated_flags": "|".join(sorted(generated)),
                "missing_flags": "|".join(missing),
                "unexpected_flags": "|".join(unexpected),
                "passed": str(passed).lower(),
            }
        )

    print(f"Evaluation passed: {passed}")
    print(f"Generated flags: {', '.join(sorted(generated))}")


if __name__ == "__main__":
    main()
