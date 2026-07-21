#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doctor — the STATIC-tier runner. Reference CLI for Contract-Driven Scaffolding.

    python -m src.doctor scan   <project>              # one project, human report
    python -m src.doctor scan   <project> --json       # one project, machine report
    python -m src.doctor matrix <dir-of-projects>      # fleet matrix + promotion backlog

The JSON shape is the point: `{file, line, contract}` per violation is what another
tool — or an AI fixing its own output — parses to act. The human report is a courtesy.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contracts import REGISTRY, Status, matrix, run  # noqa: E402

_C = {"g": "\033[92m", "r": "\033[91m", "d": "\033[90m", "b": "\033[1m", "x": "\033[0m"}
_ICON = {Status.PASS: "✅", Status.FAIL: "❌", Status.NA: "⚪"}


def _report_json(report):
    return {
        "project": report.project,
        "green": report.green,
        "summary": {"pass": report.passed, "fail": len(report.failed), "checked": report.checked},
        "results": [
            {"contract": c.id, "section": c.section, "severity": c.severity.value,
             "status": r.status.value, "detail": r.detail,
             "hits": [{"file": h.file, "line": h.line, "text": h.text} for h in r.hits]}
            for c, r in report.results
        ],
    }


def cmd_scan(path, as_json=False):
    report = run(path)
    if as_json:
        print(json.dumps(_report_json(report), ensure_ascii=False, indent=2))
        return report
    verdict = f"{_C['g']}GREEN{_C['x']}" if report.green else f"{_C['r']}{len(report.failed)} FAIL{_C['x']}"
    print(f"\n{_C['b']}━━ doctor: {report.project} ━━{_C['x']}  {verdict}"
          f"  {_C['d']}(pass {report.passed} / checked {report.checked}){_C['x']}")
    for c, r in report.results:
        col = _C["g"] if r.status is Status.PASS else (_C["r"] if r.status is Status.FAIL else _C["d"])
        print(f"  {_ICON[r.status]} {col}[{c.id}]{_C['x']} {r.detail}")
        for h in r.hits[:6]:
            print(f"       {_C['d']}{h.file}:{h.line}{_C['x']}  {h.text}")
    return report


def cmd_matrix(root):
    dirs = [os.path.join(root, d) for d in sorted(os.listdir(root))
            if os.path.isdir(os.path.join(root, d))]
    reports, backlog = matrix(dirs)
    ids = [c.id for c in REGISTRY]
    print(f"\n{_C['b']}━━ doctor MATRIX ({len(reports)} projects) ━━{_C['x']}")
    print(f"  {'PROJECT':<16} " + "  ".join(f"{i[:9]:>9}" for i in ids))
    for rep in reports:
        st = {c.id: r.status for c, r in rep.results}
        cells = []
        for i in ids:
            s = st.get(i, Status.NA)
            cells.append((_C["r"] + f"{'✗':>9}" if s is Status.FAIL else
                          (_C["g"] + f"{'✓':>9}" if s is Status.PASS else _C["d"] + f"{'·':>9}")) + _C["x"])
        tag = (_C["r"] + f"{len(rep.failed)} fail" if rep.failed else _C["g"] + "green") + _C["x"]
        print(f"  {rep.project:<16} " + "  ".join(cells) + f"   {tag}")
    print(f"\n{_C['b']}  Promotion backlog — fix these at the source, widest blast radius first:{_C['x']}")
    if not backlog:
        print(f"    {_C['g']}nothing violated across the fleet. ship it.{_C['x']}")
    for c, violators in backlog:
        print(f"    {_C['r']}{c.id:<22}{_C['x']} {len(violators):>2} projects: {', '.join(violators)}")
    return reports, backlog


def main(argv):
    if len(argv) >= 3 and argv[1] == "scan":
        cmd_scan(argv[2], as_json="--json" in argv)
    elif len(argv) >= 3 and argv[1] == "matrix":
        cmd_matrix(argv[2])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
