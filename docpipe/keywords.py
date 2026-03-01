from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any

from .stage2_structure.io_utils import write_json


# Common English stopwords to exclude
_STOPWORDS = frozenset(
    """
    a about above after again against all also am an and any are as at
    be because been before being below between both but by
    can could
    did do does doing don down during
    each
    few for from further
    had has have having he her here hers herself him himself his how
    i if in into is it its itself
    just
    me more most my myself
    no nor not now
    of off on once only or other our ours ourselves out over own
    s same she should so some such
    t than that the their theirs them themselves then there these they
    this those through to too
    under until up us
    very
    was we were what when where which while who whom why will with
    you your yours yourself yourselves
    """.split()
)

_STRIP_RE = re.compile(
    r"```.*?```"          # fenced code blocks
    r"|<[^>]+>"           # HTML tags
    r"|!\[[^\]]*\]\([^)]*\)"  # markdown images
    r"|\[[^\]]*\]\([^)]*\)",  # markdown links
    re.DOTALL,
)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
_PHRASE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{1,}")


def _extract_words(text: str) -> List[str]:
    cleaned = _STRIP_RE.sub(" ", text)
    return [
        tok.lower()
        for tok in _TOKEN_RE.findall(cleaned)
        if tok.lower() not in _STOPWORDS
    ]


def _extract_ngrams(text: str, n: int) -> List[str]:
    """Extract n-grams where every constituent word is a non-stopword."""
    cleaned = _STRIP_RE.sub(" ", text)
    tokens = [tok.lower() for tok in _PHRASE_TOKEN_RE.findall(cleaned)]
    phrases = []
    for i in range(len(tokens) - n + 1):
        gram = tokens[i : i + n]
        if all(w not in _STOPWORDS and len(w) >= 2 for w in gram):
            phrases.append(" ".join(gram))
    return phrases


def run_stage4_keywords(
    root_dir: Path,
    pdf_folder_name: str,
    out_root: Path,
    top_n: int = 50,
    min_count: int = 2,
    top_n_phrases: int | None = None,
) -> None:
    if top_n_phrases is None:
        top_n_phrases = top_n

    pdf_dir = root_dir / pdf_folder_name
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF folder not found: {pdf_dir}")

    page_dirs = sorted(
        [p for p in pdf_dir.iterdir() if p.is_dir() and p.name.startswith("page_")]
    )

    word_counter: Counter = Counter()
    phrase_counter: Counter = Counter()
    for page_dir in page_dirs:
        mmd_path = page_dir / "result.mmd"
        if not mmd_path.exists():
            continue
        raw = mmd_path.read_text(encoding="utf-8", errors="ignore")
        if raw.strip():
            word_counter.update(_extract_words(raw))
            phrase_counter.update(_extract_ngrams(raw, 2))
            phrase_counter.update(_extract_ngrams(raw, 3))

    words: List[Dict[str, Any]] = [
        {"keyword": word, "count": count, "type": "word"}
        for word, count in word_counter.most_common(top_n)
        if count >= min_count
    ]
    phrases: List[Dict[str, Any]] = [
        {"keyword": phrase, "count": count, "type": "phrase"}
        for phrase, count in phrase_counter.most_common(top_n_phrases)
        if count >= min_count
    ]
    results = sorted(words + phrases, key=lambda x: x["count"], reverse=True)

    out_dir = out_root / pdf_folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "keywords.json", results)
    print(
        f"keywords.json written ({len(words)} words, {len(phrases)} phrases) "
        f"-> {out_dir / 'keywords.json'}"
    )
