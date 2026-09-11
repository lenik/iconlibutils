#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""English semantic helpers for icon search (inflection + WordNet).

Uses python3-pattern (Debian: python3-pattern → wordnet-base) when available.
Falls back to inflection-only / exact matching if imports fail.

Plain queries expand via the primary noun synset: same-synset synonyms and
two levels of hyponyms (so ``cat`` also matches ``kitty``), plus singular/
plural forms of the query (and primary synonyms). Compound WordNet lemmas
are kept whole — hyphen pieces are not added (avoids ``mountain-lion``
polluting results with ``mountain``).
"""

from __future__ import annotations

import re
from functools import lru_cache

_TOKEN_SPLIT = re.compile(r"[-_\s]+")

SCORE_THRESHOLD = 50.0

_HAS_PATTERN = False

try:
    from pattern.en import pluralize, singularize
    from pattern.en import wordnet as _wn

    _HAS_PATTERN = True
except Exception:  # noqa: BLE001 — optional runtime dependency
    _wn = None  # type: ignore
    try:
        import inflect as _inflect_mod

        _inflect_engine = _inflect_mod.engine()

        def singularize(word: str) -> str:  # type: ignore[misc]
            s = _inflect_engine.singular_noun(word)
            return s if s else word

        def pluralize(word: str) -> str:  # type: ignore[misc]
            return _inflect_engine.plural(word)

    except Exception:  # noqa: BLE001

        def singularize(word: str) -> str:  # type: ignore[misc]
            if word.endswith("ies") and len(word) > 3:
                return word[:-3] + "y"
            if word.endswith("ses") and len(word) > 3:
                return word[:-2]
            if word.endswith("s") and not word.endswith("ss") and len(word) > 1:
                return word[:-1]
            return word

        def pluralize(word: str) -> str:  # type: ignore[misc]
            if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
                return word[:-1] + "ies"
            if word.endswith(("s", "x", "z", "ch", "sh")):
                return word + "es"
            return word + "s"


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t]


def _normalize_lemma(lemma: str) -> str:
    return lemma.replace("_", "-").lower()


def _usable_term(term: str) -> bool:
    if len(term) < 3 or len(term) > 40:
        return False
    if "." in term or term.startswith("felis-") or term.startswith("panthera-"):
        return False
    if any(ch.isdigit() for ch in term):
        return False
    # Possessives / junk from WordNet lemma cleaning.
    if term.endswith("'s") or term.startswith("'"):
        return False
    return True


@lru_cache(maxsize=4096)
def inflection_forms(word: str) -> frozenset[str]:
    w = word.lower()
    forms = {w}
    try:
        forms.add(singularize(w).lower())
    except Exception:  # noqa: BLE001
        pass
    try:
        forms.add(pluralize(w).lower())
    except Exception:  # noqa: BLE001
        pass
    return frozenset(f for f in forms if f and len(f) >= 2)


def _add_lemma(lemma: str, out: set[str]) -> None:
    term = _normalize_lemma(lemma)
    if _usable_term(term):
        out.add(term)


@lru_cache(maxsize=2048)
def expand_query_terms(query: str) -> frozenset[str]:
    """Inflections + primary-sense synonyms/hyponyms for query tokens."""
    terms: set[str] = set()
    primary_lemmas: set[str] = set()
    tokens = tokenize(query) or [query.lower()]

    for tok in tokens:
        terms |= set(inflection_forms(tok))
        if not _HAS_PATTERN or _wn is None:
            continue
        try:
            syns = list(_wn.synsets(tok, pos=_wn.NOUN)) or list(_wn.synsets(tok))[:1]
        except Exception:  # noqa: BLE001
            continue
        if not syns:
            continue
        # Primary sense only — avoids guy/CAT/caterpillar senses of "cat".
        primary = syns[0]
        for lemma in primary.synonyms:
            _add_lemma(lemma, terms)
            _add_lemma(lemma, primary_lemmas)

        try:
            hyponyms = list(primary.hyponyms())[:24]
        except Exception:  # noqa: BLE001
            hyponyms = []
        for hypo in hyponyms:
            for lemma in hypo.synonyms:
                _add_lemma(lemma, terms)
            try:
                deeper = list(hypo.hyponyms())[:16]
            except Exception:  # noqa: BLE001
                deeper = []
            for h2 in deeper:
                for lemma in h2.synonyms:
                    _add_lemma(lemma, terms)

    # Inflect query + primary synonyms only (not every wildcat breed).
    extra: set[str] = set()
    seed = {str(x) for x in tokens}
    seed |= {str(x) for x in primary_lemmas}
    for t in seed:
        parts = set(tokenize(t))
        parts.add(t)
        for part in parts:
            extra |= set(inflection_forms(part))
    q_forms = set(inflection_forms(query.lower()))
    terms |= {t for t in extra if _usable_term(t) or t in q_forms}

    return frozenset(terms)


def score_icon_name(name: str, query: str, query_terms: frozenset[str] | None = None) -> float:
    """
    Score how well an icon name matches an English query.

    Higher is better:
      100 exact full name
       95 full name in expanded terms
       90 query equals a name token
       85 inflection match on a token
       75 name token in expanded synonym/hyponym set
       60 full expanded term equals name or is a name token sequence
       55 expanded term (len>=4) is a prefix/suffix token inside name
       40 query substring of full name
    """
    q = query.strip().lower()
    if not q:
        return 0.0
    name_l = name.lower()
    if query_terms is None:
        query_terms = expand_query_terms(q)

    if name_l == q:
        return 100.0
    if name_l in query_terms:
        return 95.0

    name_tokens = tokenize(name_l)
    q_tokens = tokenize(q) or [q]
    best = 0.0

    for nt in name_tokens:
        for qt in q_tokens:
            if nt == qt:
                best = max(best, 90.0)
            elif nt in inflection_forms(qt) or qt in inflection_forms(nt):
                best = max(best, 85.0)
        if nt in query_terms:
            # Avoid false hits like chess-queen via WordNet "queen"=female cat:
            # synonym tokens count for single-token names or head (first) token.
            if len(name_tokens) == 1 or nt == name_tokens[0]:
                best = max(best, 75.0)

    # Multi-token icon names like kitty-cat: join and compare to terms.
    joined = "-".join(name_tokens)
    if joined in query_terms:
        best = max(best, 80.0)

    for term in query_terms:
        if len(term) < 4:
            continue
        if term == name_l:
            best = max(best, 70.0)
        elif "-" in term and f"-{term}-" in f"-{name_l}-":
            best = max(best, 70.0)
        elif len(name_tokens) == 1 and name_tokens[0] == term:
            best = max(best, 75.0)

    if any(qt in name_l for qt in q_tokens if len(qt) >= 3):
        best = max(best, 40.0)

    return best


def is_plain_query(pattern: str | None) -> bool:
    """True when semantic expansion should apply (not glob/regex/empty)."""
    if pattern is None or pattern == "":
        return False
    if pattern.startswith("/"):
        return False
    if any(c in pattern for c in "*?["):
        return False
    return True
