# -*- coding: utf-8 -*-
"""
The war stories, as tests. Each asserts that a contract is *honest* — that it does
not fire on the look-alike that a naive grep would flag, and does fire on the real
thing. Run: `python -m pytest test/` or `python test/test_contracts.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contracts import Status, blank_comments, run  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "examples", "fixtures")


def _status(report, cid):
    return {c.id: r.status for c, r in report.results}[cid]


# ── the comment-blanking lexer rule ──────────────────────────────────────────
def test_line_comment_does_not_swallow_following_code():
    # If block comments were stripped first, the `/*`-free line below is safe, but
    # a `//… /*…` line would open a phantom block. This asserts real code survives.
    src = '// drop later: /api/**\nconst keep = "REAL_CODE";\n'
    out = blank_comments(src, ".js")
    assert "REAL_CODE" in out            # second line NOT swallowed
    assert "drop later" not in out       # comment content blanked
    assert out.count("\n") == src.count("\n")  # line numbers preserved


def test_url_double_slash_is_not_a_comment():
    src = 'const u = "https://api.example.com/v1";\n'
    assert "api.example.com" in blank_comments(src, ".js")


# ── contract honesty on the fixtures ─────────────────────────────────────────
def test_green_app_is_green():
    rep = run(os.path.join(FIX, "green_app"))
    assert rep.green, [(_c.id, _r.detail) for _c, _r in rep.failed]


def test_debug_marker_ignores_comment_but_catches_code():
    assert _status(run(os.path.join(FIX, "green_app")), "NO-DEBUG-MARKER") is Status.PASS
    assert _status(run(os.path.join(FIX, "red_app")), "NO-DEBUG-MARKER") is Status.FAIL


def test_inline_array_allows_server_expr_but_catches_js_array():
    # green: `[[${currentUser}]]` is a legit server expression → PASS
    assert _status(run(os.path.join(FIX, "green_app")), "INLINE-ARRAY-COLLISION") is Status.PASS
    # red: `[['name',1],…]` is a JS array-of-arrays → FAIL
    assert _status(run(os.path.join(FIX, "red_app")), "INLINE-ARRAY-COLLISION") is Status.FAIL


def test_useauth_window_excuses_token_issuing_only():
    assert _status(run(os.path.join(FIX, "green_app")), "USEAUTH-DISCIPLINE") is Status.PASS
    assert _status(run(os.path.join(FIX, "red_app")), "USEAUTH-DISCIPLINE") is Status.FAIL


def test_locale_parity():
    assert _status(run(os.path.join(FIX, "green_app")), "LOCALE-PARITY") is Status.PASS
    assert _status(run(os.path.join(FIX, "red_app")), "LOCALE-PARITY") is Status.FAIL


def test_feature_guard_conditional():
    assert _status(run(os.path.join(FIX, "green_app")), "FEATURE-GUARD") is Status.PASS
    assert _status(run(os.path.join(FIX, "red_app")), "FEATURE-GUARD") is Status.FAIL


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
