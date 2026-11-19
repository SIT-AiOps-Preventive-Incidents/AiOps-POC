"""schema.sql runs at every start-up; one missing ');' stops the whole API. Each statement must close its brackets
and hold one command (a missing ';' or ')' glues the next statement onto it)."""
from __future__ import annotations

import os
import re

SQL = os.path.join(os.path.dirname(__file__), "..", "app", "schema.sql")
VERBS = ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "DO", "COMMENT")


def statements() -> list[str]:
    text = re.sub(r"--[^\n]*", "", open(SQL).read())
    text = re.sub(r"\$\$.*?\$\$", "$$", text, flags=re.S)        # function bodies hold their own semicolons
    return [s.strip() for s in text.split(";") if s.strip()]


def test_every_statement_closes_its_brackets():
    bad = [s[:80] for s in statements() if s.count("(") != s.count(")")]
    assert bad == []


def test_every_statement_is_one_command():
    glued = [s[:80] for s in statements() if len(re.findall(r"(?m)^\s*(CREATE|ALTER) (TABLE|INDEX|UNIQUE)", s)) > 1]
    assert glued == []
    assert all(s.split()[0].upper() in VERBS for s in statements())
