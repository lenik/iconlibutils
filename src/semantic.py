#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""English semantic helpers for icon search (inflection + offline WordNet).

Uses python3-inflect for singular/plural and Debian wordnet-base files under
/usr/share/wordnet (no network). Pattern/NLTK are avoided because they can
block forever offline (e.g. during debuild).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_TOKEN_SPLIT = re.compile(r"[-_\s]+")
SCORE_THRESHOLD = 50.0

WORDNET_DIR = Path("/usr/share/wordnet")

_HAS_INFLECT = False
try:
    import inflect as _inflect_mod

    _inflect_engine = _inflect_mod.engine()
    _HAS_INFLECT = True

    def singularize(word: str) -> str:
        s = _inflect_engine.singular_noun(word)
        return s if s else word

    def pluralize(word: str) -> str:
        return _inflect_engine.plural(word)

except Exception:  # noqa: BLE001

    def singularize(word: str) -> str:
        if word.endswith("ies") and len(word) > 3:
            return word[:-3] + "y"
        if word.endswith("ses") and len(word) > 3:
            return word[:-2]
        if word.endswith("s") and not word.endswith("ss") and len(word) > 1:
            return word[:-1]
        return word

    def pluralize(word: str) -> str:
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


class _WordNetNoun:
    """Minimal offline noun WordNet over Debian wordnet-base files."""

    def __init__(self, root: Path = WORDNET_DIR) -> None:
        self.root = root
        self._index: dict[str, list[str]] | None = None
        self._data: dict[str, tuple[list[str], list[str]]] | None = None

    def available(self) -> bool:
        return (self.root / "index.noun").is_file() and (self.root / "data.noun").is_file()

    def _load_index(self) -> dict[str, list[str]]:
        if self._index is not None:
            return self._index
        idx: dict[str, list[str]] = {}
        path = self.root / "index.noun"
        if not path.is_file():
            self._index = idx
            return idx
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line or line.startswith(" "):
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                lemma = parts[0]
                try:
                    synset_cnt = int(parts[2])
                    p_cnt = int(parts[3])
                except ValueError:
                    continue
                # offsets start after: lemma pos synset_cnt p_cnt [ptrs...] sense_cnt tagsense_cnt
                off = 4 + p_cnt + 2
                offsets = parts[off : off + synset_cnt]
                idx[lemma] = offsets
        self._index = idx
        return idx

    def _load_data(self) -> dict[str, tuple[list[str], list[str]]]:
        if self._data is not None:
            return self._data
        data: dict[str, tuple[list[str], list[str]]] = {}
        path = self.root / "data.noun"
        if not path.is_file():
            self._data = data
            return data
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line or line.startswith(" "):
                    continue
                # offset lex filenum pos w_cnt word lexid ...
                try:
                    meta, _gloss = line.split("|", 1)
                except ValueError:
                    meta = line
                parts = meta.split()
                if len(parts) < 5:
                    continue
                offset = parts[0]
                try:
                    w_cnt = int(parts[3], 16)
                except ValueError:
                    continue
                lemmas: list[str] = []
                i = 4
                for _ in range(w_cnt):
                    if i >= len(parts):
                        break
                    lemmas.append(parts[i])
                    i += 2  # skip lex_id
                try:
                    p_cnt = int(parts[i])
                except (ValueError, IndexError):
                    p_cnt = 0
                    i = len(parts)
                else:
                    i += 1
                hyponyms: list[str] = []
                for _ in range(p_cnt):
                    if i + 3 >= len(parts):
                        break
                    pointer_symbol = parts[i]
                    synset_offset = parts[i + 1]
                    # parts[i+2]=pos, parts[i+3]=source/target
                    if pointer_symbol == "~":  # hyponym
                        hyponyms.append(synset_offset)
                    i += 4
                data[offset] = (lemmas, hyponyms)
        self._data = data
        return data

    def expand(self, word: str, *, max_hyponym_depth: int = 2) -> set[str]:
        out: set[str] = set()
        idx = self._load_index()
        data = self._load_data()
        key = word.lower().replace("-", "_")
        offsets = idx.get(key) or idx.get(word.lower())
        if not offsets:
            return out
        # Primary synset only (first offset) — avoids guy/CAT senses of "cat".
        primary = offsets[0]
        frontier = [primary]
        seen: set[str] = set()
        for depth in range(max_hyponym_depth + 1):
            nxt: list[str] = []
            for off in frontier:
                if off in seen:
                    continue
                seen.add(off)
                entry = data.get(off)
                if not entry:
                    continue
                lemmas, hypos = entry
                for lemma in lemmas:
                    term = _normalize_lemma(lemma)
                    if _usable_term(term):
                        out.add(term)
                if depth < max_hyponym_depth:
                    nxt.extend(hypos[:24] if depth == 0 else hypos[:16])
            frontier = nxt
        return out


_WN = _WordNetNoun()


@lru_cache(maxsize=2048)
def expand_query_terms(query: str) -> frozenset[str]:
    """Inflections + primary-sense synonyms/hyponyms for query tokens."""
    terms: set[str] = set()
    primary_lemmas: set[str] = set()
    tokens = tokenize(query) or [query.lower()]

    for tok in tokens:
        terms |= set(inflection_forms(tok))
        if _WN.available():
            expanded = _WN.expand(tok)
            if expanded:
                # First-wave lemmas ≈ primary synset terms already in expand;
                # keep all for matching, but only inflect query + short primary set.
                terms |= expanded
                # Approximate primary lemmas: those equal to tok forms or containing tok
                for t in expanded:
                    if t in inflection_forms(tok) or tok in tokenize(t):
                        primary_lemmas.add(t)
                # Also treat first few alphabetically-stable short terms as primary-ish
                primary_lemmas |= {t for t in list(expanded)[:8] if "-" not in t}

    extra: set[str] = set()
    seed = {str(x) for x in tokens} | {str(x) for x in primary_lemmas}
    for t in seed:
        parts = set(tokenize(t))
        parts.add(t)
        for part in parts:
            extra |= set(inflection_forms(part))
    q_forms = set(inflection_forms(query.lower()))
    terms |= {t for t in extra if _usable_term(t) or t in q_forms}
    return frozenset(terms)


def score_icon_name(name: str, query: str, query_terms: frozenset[str] | None = None) -> float:
    """Score how well an icon name matches an English query (higher is better)."""
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
            if len(name_tokens) == 1 or nt == name_tokens[0]:
                best = max(best, 75.0)

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
