from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.request import urlopen


METHODS = {"get", "post", "put", "patch", "delete"}
MUTATION_METHODS = {"post", "put", "patch", "delete"}
PUBLIC_PREFIXES = (
    "/health",
    "/api/v1/health",
    "/api/v1/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/captcha",
)


def _load_openapi(base_url: str) -> dict:
    with urlopen(f"{base_url.rstrip('/')}/api/v1/openapi.json", timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _case_type(method: str, path: str) -> str:
    if path.startswith(PUBLIC_PREFIXES):
        return "public_contract_or_validation"
    if method in MUTATION_METHODS:
        return "anonymous_guard_then_data_factory_happy_path"
    return "anonymous_guard_and_live_get_smoke"


def build_rows(schema: dict) -> list[dict[str, str]]:
    rows = []
    for path, operations in sorted(schema.get("paths", {}).items()):
        for method, operation in sorted(operations.items()):
            if method not in METHODS or not isinstance(operation, dict):
                continue
            rows.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation.get("operationId", ""),
                    "tags": ",".join(operation.get("tags", [])),
                    "has_path_params": str("{" in path and "}" in path).lower(),
                    "has_request_body": str("requestBody" in operation).lower(),
                    "case_type": _case_type(method, path),
                    "automated_checks": "schema_contract;anonymous_guard;server_error_scan",
                    "happy_path_status": "pending_data_factory" if method in MUTATION_METHODS else "covered_or_not_applicable",
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", default="test_cases/api_endpoint_case_catalog.csv")
    parser.add_argument("--summary", default="test_cases/api_endpoint_case_summary.json")
    parser.add_argument("--snapshot", default="test_cases/openapi_snapshot.json")
    args = parser.parse_args()

    schema = _load_openapi(args.base_url)
    rows = build_rows(schema)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    method_counts = Counter(row["method"] for row in rows)
    case_counts = Counter(row["case_type"] for row in rows)
    summary = {
        "base_url": args.base_url,
        "path_count": len(schema.get("paths", {})),
        "operation_count": len(rows),
        "method_counts": dict(sorted(method_counts.items())),
        "case_type_counts": dict(sorted(case_counts.items())),
        "catalog": str(output.resolve()),
    }
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.snapshot).write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
