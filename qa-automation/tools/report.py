#!/usr/bin/env python3
"""Generate a Markdown test report from pytest's JSON report.

Usage:
    python -m pytest --json-report --json-report-file=reports/latest.json
    python tools/report.py [reports/latest.json] [output.md]

The report contains: totals, pass rate, per-module counts, the full failure
list with assertion messages, and a severity/priority table skeleton that
the QA engineer fills in after triage (failures are NOT auto-severitised:
severity needs a human/product judgement).

Generated vs curated report — read this before pointing the output at
the curated file:
  - Default output is reports/generated.md: the fresh numbers for THIS
    run only. It never touches the curated reports/TEST_REPORT.md.
  - The curated TEST_REPORT.md keeps the round history, the defect list
    and the hand-written sections. Merge the numbers from generated.md
    into it by hand; never let this tool write over it wholesale, or
    the history is lost.
  - Pass an explicit output path only for a fresh project with no
    curated history yet, or for a scratch file.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def module_of(nodeid: str) -> str:
    # tests/test_projects.py::TestX::test_y -> test_projects
    return nodeid.split("::")[0].split("/")[-1].replace(".py", "")


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reports" / "latest.json"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "reports" / "generated.md"
    data = load(src)
    summary = data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("error", 0)
    skipped = summary.get("skipped", 0)
    duration = data.get("duration", 0)
    rate = (passed / total * 100) if total else 0.0

    tests = data.get("tests", [])
    by_module: dict[str, Counter] = defaultdict(Counter)
    failures = []
    for t in tests:
        mod = module_of(t["nodeid"])
        by_module[mod][t["outcome"]] += 1
        if t["outcome"] in ("failed", "error"):
            call = t.get("call", {}) or {}
            failures.append(
                {
                    "nodeid": t["nodeid"],
                    "outcome": t["outcome"],
                    "duration": round(call.get("duration", 0), 3),
                    "message": (call.get("longrepr") or "")[:1500],
                }
            )

    lines = []
    lines.append("# AI 测试管理系统 — 自动化测试报告")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"执行耗时：{duration:.1f}s")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("| --- | --- |")
    lines.append(f"| 用例总数 | {total} |")
    lines.append(f"| 通过 | {passed} |")
    lines.append(f"| 失败 | {failed} |")
    lines.append(f"| 错误 | {errors} |")
    lines.append(f"| 跳过 | {skipped} |")
    lines.append(f"| 通过率 | {rate:.1f}% |")
    lines.append("")
    lines.append("## 按模块统计")
    lines.append("")
    lines.append("| 模块 | 通过 | 失败 | 错误 | 跳过 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for mod in sorted(by_module):
        c = by_module[mod]
        lines.append(
            f"| {mod} | {c.get('passed', 0)} | {c.get('failed', 0)} | "
            f"{c.get('error', 0)} | {c.get('skipped', 0)} |"
        )
    lines.append("")
    lines.append("## 失败用例")
    lines.append("")
    if not failures:
        lines.append("无失败用例。")
    else:
        for i, f in enumerate(failures, 1):
            lines.append(f"### {i}. `{f['nodeid']}` ({f['outcome']}, {f['duration']}s)")
            lines.append("")
            lines.append("```")
            lines.append(f["message"].strip())
            lines.append("```")
            lines.append("")
    lines.append("## 问题清单（待分级）")
    lines.append("")
    lines.append(
        "下表由测试负责人根据失败用例填写：严重程度 blocker / critical / major / minor；"
        "优先级 P0 / P1 / P2。"
    )
    lines.append("")
    lines.append("| # | 问题 | 严重程度 | 优先级 | 状态 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for i, f in enumerate(failures, 1):
        lines.append(f"| {i} | `{f['nodeid']}` |  |  | 待处理 |")
    if not failures:
        lines.append("| - | 无 | - | - | - |")
    lines.append("")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(lines), encoding="utf-8")
    print(f"report written: {dst} (total={total} passed={passed} failed={failed} errors={errors})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
