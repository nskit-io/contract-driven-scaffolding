#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worked example. Run:

    python examples/demo.py

Scans two fixture projects — one green, one that trips five contracts — then runs
the fleet matrix so you can see the promotion backlog fall out of the same checks.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from src.doctor import cmd_matrix, cmd_scan  # noqa: E402

FIX = os.path.join(HERE, "fixtures")

if __name__ == "__main__":
    cmd_scan(os.path.join(FIX, "green_app"))
    cmd_scan(os.path.join(FIX, "red_app"))
    cmd_matrix(FIX)
