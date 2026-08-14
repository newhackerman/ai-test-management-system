from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _load_result_files(results_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in results_dir.glob("*-result.json"):
        try:
            results.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid Allure result JSON: {path}: {exc}") from exc
    return results


def _final_attempts(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        history_id = result.get("historyId") or result.get("uuid") or result.get("name")
        grouped[str(history_id)].append(result)
    return [max(attempts, key=lambda item: item.get("stop") or 0) for attempts in grouped.values()]


def _status_message(result: dict[str, Any]) -> str:
    details = result.get("statusDetails") or {}
    message = details.get("message") or "NO_MESSAGE"
    return str(message).splitlines()[0][:220]


def analyze(results_dir: Path) -> dict[str, Any]:
    results = _load_result_files(results_dir)
    final_results = _final_attempts(results)

    attempts_by_history: dict[str, int] = Counter(
        str(result.get("historyId") or result.get("uuid") or result.get("name")) for result in results
    )
    retried = [count for count in attempts_by_history.values() if count > 1]

    skipped_reasons = Counter(
        _status_message(result) for result in final_results if result.get("status") == "skipped"
    )

    failed_by_suite = Counter()
    failure_messages = Counter()
    for result in final_results:
        if result.get("status") not in {"failed", "broken"}:
            continue
        full_name = str(result.get("fullName") or "")
        failed_by_suite[full_name.split("#")[0]] += 1
        failure_messages[_status_message(result)] += 1

    return {
        "results_dir": str(results_dir),
        "raw_result_files": len(results),
        "final_test_cases": len(final_results),
        "final_status": dict(Counter(result.get("status") for result in final_results)),
        "raw_status": dict(Counter(result.get("status") for result in results)),
        "retried_tests": len(retried),
        "extra_attempts": len(results) - len(final_results),
        "max_attempts": max(attempts_by_history.values(), default=0),
        "skipped_reasons": dict(skipped_reasons.most_common()),
        "failed_by_suite_top20": dict(failed_by_suite.most_common(20)),
        "failure_messages_top20": dict(failure_messages.most_common(20)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze pytest Allure result files.")
    parser.add_argument("results_dir", type=Path, help="Directory containing Allure *-result.json files.")
    args = parser.parse_args()

    results_dir = args.results_dir.resolve()
    if not results_dir.exists():
        raise SystemExit(f"Allure results directory does not exist: {results_dir}")
    summary = analyze(results_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
