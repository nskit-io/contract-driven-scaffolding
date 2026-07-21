# -*- coding: utf-8 -*-
"""Contract-Driven Scaffolding — a tiny, dependency-free contract linter."""
from .core import (
    Contract, Hit, Project, Report, Result, Severity, Status,
    REGISTRY, blank_comments, contract, matrix, na, run, verdict,
)
from . import library  # noqa: F401  (registers the starter contracts)

__all__ = [
    "Contract", "Hit", "Project", "Report", "Result", "Severity", "Status",
    "REGISTRY", "blank_comments", "contract", "matrix", "na", "run", "verdict",
]
