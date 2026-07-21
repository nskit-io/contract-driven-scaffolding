# -*- coding: utf-8 -*-
"""
Contract-Driven Scaffolding — the engine.

A *contract* is a machine-executed answer to one question:
    "Can the framework prove this, instead of trusting the builder to get it right?"

Every contract is a 4-tuple — (target, when-checked, predicate, violation-signal) —
where the predicate runs on a machine (never a human review) and the signal is
machine-readable (a file:line another tool, or an AI, can act on).

This module is the STATIC tier: it decides from source alone. It is deliberately
dependency-free and ~200 lines so you can read it in one sitting and port it.

The one hard-won lesson encoded here: **naive grep lies.** A forbidden token that
only appears in a comment is not a violation; a token split across two lines of an
object literal is; a template's `[[${...}]]` is not the same as a JavaScript
`[[ array ]]`. The `Project` helpers below make the honest version the easy version.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Sequence, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Vocabulary

class Severity(str, Enum):
    HIGH = "high"
    MED = "med"
    LOW = "low"
    INFO = "info"


class Status(str, Enum):
    PASS = "pass"   # the predicate held
    FAIL = "fail"   # the predicate was violated — here is where
    NA = "na"       # the contract does not apply to this project


@dataclass
class Hit:
    file: str       # project-relative path
    line: int       # 1-indexed; 0 = "whole file / no single line"
    text: str       # the offending source, trimmed


@dataclass
class Result:
    contract_id: str
    status: Status
    detail: str
    hits: List[Hit] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# The war story: comment-aware source, so grep stops lying.

_COMMENTABLE = {".js", ".ts", ".java", ".css", ".c", ".cpp", ".go", ".rs", ".kt", ".swift"}
_HTML = {".html", ".htm", ".vue"}


def _blank(match: "re.Match") -> str:
    # Replace matched text with spaces, but keep newlines — line numbers must survive.
    return re.sub(r"[^\n]", " ", match.group(0))


def blank_comments(text: str, ext: str) -> str:
    """Return `text` with comment *content* blanked to spaces (newlines preserved).

    Why one alternation, scanned strictly left-to-right, instead of stripping line
    comments and block comments in two passes:

        //  drop this endpoint later: /api/**  ← a line comment
        const url = "/api/v1/live";            ← real code, must NOT be swallowed

    If you blank block comments (`/* … */`) first, the `/*` *substring* inside the
    line comment opens a phantom block that eats everything down to the next `*/`,
    silently deleting real code from the scan — a false negative you never see.
    A single left-to-right alternation lets whichever opens first win, which is
    exactly how the language lexer sees it.
    """
    if ext in _HTML:
        text = re.sub(r"<!--.*?-->", _blank, text, flags=re.S)
    if ext in _COMMENTABLE or ext in _HTML:
        # `//…`  (but not `://`, `"//`, `'//` — those are URLs / strings)  OR  `/* … */`
        # whichever *starts first* wins.
        text = re.sub(r"(?<![:\"'/])//[^\n]*|/\*.*?\*/", _blank, text, flags=re.S)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Project — the scan context handed to every contract.

_SKIP_DIRS = ("/node_modules/", "/build/", "/target/", "/dist/", "/.git/", "/vendor/")


class Project:
    """A rooted view of one project's source, with honest scan helpers."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.name = os.path.basename(self.root.rstrip("/"))

    # -- filesystem --------------------------------------------------------
    def files(self, exts: Sequence[str]) -> List[str]:
        out: List[str] = []
        for dp, dns, fns in os.walk(self.root):
            if any(s in (dp + "/") for s in _SKIP_DIRS):
                dns[:] = []
                continue
            for fn in fns:
                if fn.endswith(tuple(exts)):
                    out.append(os.path.join(dp, fn))
        return sorted(out)

    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.root)

    def exists(self, *rel_paths: str) -> bool:
        return any(os.path.exists(os.path.join(self.root, p)) for p in rel_paths)

    def read(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def read_json(self, rel_path: str) -> Optional[dict]:
        full = os.path.join(self.root, rel_path)
        if not os.path.exists(full):
            return None
        try:
            return json.loads(self.read(full))
        except Exception:
            return None

    # -- honest grep -------------------------------------------------------
    def grep(self, pattern: str, exts: Sequence[str], skip_comments: bool = True) -> List[Hit]:
        """Regex search returning Hits. Comment content is blanked by default —
        a match inside a comment is not a match."""
        rx = re.compile(pattern)
        hits: List[Hit] = []
        for p in self.files(exts):
            ext = os.path.splitext(p)[1]
            raw = self.read(p)
            scanned = blank_comments(raw, ext) if skip_comments else raw
            raw_lines = raw.split("\n")
            for i, line in enumerate(scanned.split("\n")):
                if rx.search(line):
                    src = raw_lines[i] if i < len(raw_lines) else line
                    hits.append(Hit(self.rel(p), i + 1, src.strip()[:160]))
        return hits

    def grep_window(self, pattern: str, exts: Sequence[str], radius: int,
                    accept: Callable[[str], bool], skip_comments: bool = True) -> List[Hit]:
        """Like grep, but a hit only counts if `accept(window_text)` is True, where
        the window is ±`radius` lines around the match. Use this when the thing that
        makes a line OK-or-not lives on a *neighbouring* line — e.g. a flag and the
        call it guards sitting on different lines of the same object literal. A
        single-line grep cannot see that context and will lie in both directions.
        """
        rx = re.compile(pattern)
        out: List[Hit] = []
        for p in self.files(exts):
            ext = os.path.splitext(p)[1]
            raw = self.read(p)
            scanned = blank_comments(raw, ext) if skip_comments else raw
            lines = scanned.split("\n")
            raw_lines = raw.split("\n")
            for i, line in enumerate(lines):
                if not rx.search(line):
                    continue
                lo, hi = max(0, i - radius), min(len(lines), i + radius + 1)
                if accept(" ".join(lines[lo:hi])):
                    src = raw_lines[i] if i < len(raw_lines) else line
                    out.append(Hit(self.rel(p), i + 1, src.strip()[:160]))
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Contract — metadata + a predicate that returns a Result.

@dataclass
class Contract:
    id: str
    section: str                       # where the originating incident is documented
    severity: Severity
    describe: str
    check: Callable[[Project], Result]

    def run(self, project: Project) -> Result:
        r = self.check(project)
        r.contract_id = self.id
        return r


REGISTRY: List[Contract] = []


def contract(id: str, section: str, severity: Severity, describe: str):
    """Decorator: register a predicate `(Project) -> Result` as a Contract."""
    def deco(fn: Callable[[Project], Result]) -> Contract:
        c = Contract(id=id, section=section, severity=severity, describe=describe, check=fn)
        REGISTRY.append(c)
        return c
    return deco


# convenience for predicates: turn a hit-list into a Result
def verdict(hits: List[Hit], ok_detail: str, bad_detail: str,
            applicable: bool = True) -> Result:
    if not applicable:
        return Result("", Status.NA, ok_detail, [])
    if hits:
        return Result("", Status.FAIL, bad_detail.format(n=len(hits)), hits)
    return Result("", Status.PASS, ok_detail, [])


def na(detail: str) -> Result:
    return Result("", Status.NA, detail, [])


# ─────────────────────────────────────────────────────────────────────────────
# run + matrix

@dataclass
class Report:
    project: str
    results: List[Tuple[Contract, Result]]

    @property
    def passed(self) -> int:
        return sum(1 for _, r in self.results if r.status is Status.PASS)

    @property
    def failed(self) -> List[Tuple[Contract, Result]]:
        return [(c, r) for c, r in self.results if r.status is Status.FAIL]

    @property
    def checked(self) -> int:
        return sum(1 for _, r in self.results if r.status is not Status.NA)

    @property
    def green(self) -> bool:
        return len(self.failed) == 0


def run(project_root: str, contracts: Sequence[Contract] = None) -> Report:
    contracts = list(contracts if contracts is not None else REGISTRY)
    p = Project(project_root)
    return Report(p.name, [(c, c.run(p)) for c in contracts])


def matrix(project_roots: Sequence[str], contracts: Sequence[Contract] = None):
    """Scan many projects. Returns (reports, backlog) where `backlog` is the list of
    (contract, [violating project names]) sorted by how many projects violate it.

    This is the point of the whole exercise: the contract violated by the *most*
    projects is the abstraction most worth fixing at the source — a promotion
    backlog, ranked by blast radius, that falls straight out of the same checks
    that gate each project.
    """
    contracts = list(contracts if contracts is not None else REGISTRY)
    reports = [run(root, contracts) for root in project_roots]
    backlog = []
    for c in contracts:
        violators = [rep.project for rep in reports
                     for cc, r in rep.results
                     if cc is c and r.status is Status.FAIL]
        if violators:
            backlog.append((c, violators))
    backlog.sort(key=lambda cv: -len(cv[1]))
    return reports, backlog
