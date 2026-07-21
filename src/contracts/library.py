# -*- coding: utf-8 -*-
"""
A starter library of contracts.

These are deliberately small and generic so the *technique* is visible, but each
one is a distilled version of a real contract from NSKit's `doctor` — the field
incident it came from is named in `section`. Copy them, delete them, write your
own. The value is not this list; it is that each bug you get burned by becomes one
of these and then can never silently come back.
"""
from __future__ import annotations

from .core import Project, Result, Severity, Status, contract, na, verdict


# ── 1. Comment-aware forbidden token ─────────────────────────────────────────
# Technique: comment blanking. A debug/kill switch left in a *comment* is fine;
# one left in live code ships a landmine. Naive grep cannot tell them apart.
# NSKit origin: L2 (Font Awesome must be fully removed, not "mostly").
@contract(id="NO-DEBUG-MARKER", section="incident-log#debug-markers",
          severity=Severity.MED,
          describe="No `DEBUG_ONLY` marker survives into shipped source (comments are fine)")
def no_debug_marker(p: Project) -> Result:
    hits = p.grep(r"\bDEBUG_ONLY\b", exts=(".js", ".ts", ".java", ".py"))
    return verdict(hits, "no live DEBUG_ONLY markers",
                   "DEBUG_ONLY in shipped source ({n})")


# ── 2. Context-sensitive token (template vs code collision) ──────────────────
# Technique: distinguish two meanings of the same characters. In a Thymeleaf
# `th:inline="javascript"` block, `[[${x}]]` is a legitimate server expression,
# but a JavaScript array-of-arrays `[[ 'a', 1 ], …]` is read by the template
# engine as an expression and silently corrupts the served script.
# NSKit origin: T16 (§16) — a whole admin page's JS went undefined in production
# while the source passed `node --check`.
@contract(id="INLINE-ARRAY-COLLISION", section="incident-log#template-inline",
          severity=Severity.HIGH,
          describe="No JS `[[` array literal inside a template inline block (`[[${…}]]` is allowed)")
def inline_array_collision(p: Project) -> Result:
    # Only look at files that actually use an inline block.
    inline_files = {h.file for h in p.grep(r'th:inline\s*=\s*["\']javascript',
                                           exts=(".html",), skip_comments=False)}
    if not inline_files:
        return na("no template inline blocks")
    # `[[` NOT immediately followed by `${` = JS array-of-arrays = the bug.
    hits = [h for h in p.grep(r"\[\[(?!\$\{)", exts=(".html",)) if h.file in inline_files]
    return verdict(hits, "template inline blocks are collision-free",
                   "JS `[[` array literal collides with template inline ({n})")


# ── 3. Cross-line context (the window technique) ─────────────────────────────
# Technique: a line is OK-or-not because of a *neighbouring* line. Every API call
# must send an auth token, EXCEPT the token-issuing calls themselves. In a real
# object literal the `useAuth: false` and the `command:` that excuses it sit on
# different lines — a single-line grep flags the exception or misses the abuse.
# NSKit origin: K3 (cm§1) — `useAuth:false` audit.
_TOKEN_ISSUING = ("auth-verify", "auth-refresh", "ensureGuestToken")


@contract(id="USEAUTH-DISCIPLINE", section="incident-log#useauth",
          severity=Severity.LOW,
          describe="`useAuth:false` only on token-issuing calls (checked across ±6 lines)")
def useauth_discipline(p: Project) -> Result:
    hits = p.grep_window(
        r"useAuth\s*:\s*false", exts=(".js", ".ts"), radius=6,
        accept=lambda window: not any(tok in window for tok in _TOKEN_ISSUING),
    )
    return verdict(hits, "useAuth discipline holds",
                   "useAuth:false outside token-issuing calls ({n})")


# ── 4. Cross-file parity ─────────────────────────────────────────────────────
# Technique: two files must stay in lockstep. Every locale file must carry the
# same key set, or a translated screen falls back to a raw token in production.
# NSKit origin: I1 (i18n) — lang-json parity.
@contract(id="LOCALE-PARITY", section="incident-log#i18n",
          severity=Severity.LOW,
          describe="All locale files under assets/lang/ share one key set")
def locale_parity(p: Project) -> Result:
    import os
    lang_dir = os.path.join(p.root, "assets", "lang")
    if not os.path.isdir(lang_dir):
        return na("no assets/lang/ (single-locale)")
    keysets = {}
    for fn in sorted(os.listdir(lang_dir)):
        if fn.endswith(".json"):
            data = p.read_json(os.path.join("assets", "lang", fn))
            if isinstance(data, dict):
                keysets[fn] = set(data.keys())
    if len(keysets) < 2:
        return na("fewer than two locales")
    union = set().union(*keysets.values())
    from .core import Hit
    hits = []
    for fn, keys in keysets.items():
        missing = union - keys
        if missing:
            hits.append(Hit(os.path.join("assets", "lang", fn), len(missing),
                            fn + " missing " + str(len(missing)) + " keys: "
                            + ", ".join(sorted(missing)[:6])))
    return verdict(hits, "locale key parity holds ({} locales)".format(len(keysets)),
                   "locale files out of parity ({n})")


# ── 5. Conditional presence (feature implies its guard) ──────────────────────
# Technique: if a project uses feature X, it must also carry the override that
# stops X from breaking. Absence is only a violation *when the feature is used*.
# NSKit origin: L3 (§11) — any project using PAGE must ship the flex override, or
# the sub-page silently loses its scroll.
@contract(id="FEATURE-GUARD", section="incident-log#page-scroll",
          severity=Severity.MED,
          describe="Any project using PAGE.show ships the `.sub-page-container.show` flex override")
def feature_guard(p: Project) -> Result:
    uses = p.grep(r"PAGE\.show\(|PAGE\.define\(", exts=(".js", ".html"))
    if not uses:
        return na("PAGE not used")
    override = p.grep(r"sub-page-container\.show", exts=(".css", ".html"))
    if override:
        return Result("", Status.PASS, "flex override present", [])
    from .core import Hit
    return Result("", Status.FAIL, "PAGE used without the scroll-fixing override",
                  [Hit(uses[0].file, uses[0].line, "PAGE.show(...) — override missing")])
