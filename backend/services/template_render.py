"""Template renderer — variables + spintax + Liquid-style fallbacks.

Order of operations is important. We expand spintax FIRST (per-recipient
randomization), then variables (so a chosen spintax token can itself contain
`{first_name}` and substitute correctly), then fallbacks.

Variable syntax:
    Hi {first_name},          → "Hi Amine,"
    Hi {{first_name | there}} → "Hi Amine," / "Hi there," when missing

Spintax syntax (matches Smartlead/Instantly):
    {Hi|Hey|Hello}            → one of those, picked uniformly per render
    {Quick|Fast|Speedy} idea  → "Fast idea" for one recipient,
                                "Quick idea" for the next.

Why spintax matters: sending byte-identical bodies to N recipients is the
single biggest pattern Gmail's bulk-suppression watches for. Even small
randomization (5-7 spintax slots in a 100-word email) creates millions of
unique permutations and makes the campaign look like normal one-off mail.
"""

from __future__ import annotations

import random
import re
from typing import Any


# {a|b|c} where a/b/c contain anything except `{`, `|`, `}`. We don't support
# nesting because nested spintax is a footgun (combinatorial explosion) and
# Smartlead/Instantly don't support it either.
_SPINTAX_RE = re.compile(r"\{([^{}|]+(?:\|[^{}|]+)+)\}")

# {{var | fallback}} — Liquid-style with default value when var is missing.
_FALLBACK_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\|\s*([^}]+?)\s*\}\}")

# {var} — plain Python str.format-style. Not a spintax conflict because
# spintax always has at least one `|`.
_VARIABLE_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def expand_spintax(text: str, *, rng: random.Random | None = None) -> str:
    """Pick one option from each `{a|b|c}` block. Idempotent on text with no
    spintax. Uses the supplied RNG so callers can pin per-recipient choices."""
    rng = rng or random
    while True:
        m = _SPINTAX_RE.search(text)
        if not m:
            return text
        options = m.group(1).split("|")
        choice = rng.choice(options)
        text = text[: m.start()] + choice + text[m.end():]


def substitute(text: str, variables: dict[str, Any]) -> str:
    """Replace `{var}` and `{{var | fallback}}` with values from `variables`.
    Missing keys leave the placeholder intact for `{var}`, fall through to
    the literal fallback for `{{var|fallback}}`."""

    def _fallback_repl(m: re.Match) -> str:
        key, default = m.group(1), m.group(2)
        v = variables.get(key)
        if v is None or v == "":
            return default
        return str(v)

    text = _FALLBACK_RE.sub(_fallback_repl, text)

    def _var_repl(m: re.Match) -> str:
        key = m.group(1)
        if key in variables:
            return str(variables[key])
        return m.group(0)

    return _VARIABLE_RE.sub(_var_repl, text)


def render(
    text: str,
    variables: dict[str, Any],
    *,
    seed: str | None = None,
) -> str:
    """One-shot render. Order matters:
      1. Fallbacks `{{var | default}}` — consumed first so the inner pipe
         isn't mis-parsed as spintax.
      2. Spintax `{a|b|c}` — randomized per render (or pinned by `seed`).
      3. Plain variables `{var}` — last so values can themselves contain
         spintax that won't get re-expanded.

    `seed` (if provided) makes spintax deterministic per recipient — the
    same lead always gets the same variant, so a follow-up rendering the
    same template doesn't suddenly switch greeting.
    """
    rng = random.Random(seed) if seed else random

    def _fallback_repl(m: re.Match) -> str:
        key, default = m.group(1), m.group(2)
        v = variables.get(key)
        if v is None or v == "":
            return default
        return str(v)

    out = _FALLBACK_RE.sub(_fallback_repl, text)
    out = expand_spintax(out, rng=rng)

    def _var_repl(m: re.Match) -> str:
        key = m.group(1)
        if key in variables:
            return str(variables[key])
        return m.group(0)

    return _VARIABLE_RE.sub(_var_repl, out)
