from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from .structuring.io_utils import write_json


# ── Stopwords ─────────────────────────────────────────────────────────────────
_STOPWORDS = frozenset(
    """
    a about above across after again against all also always am an and any are
    as at
    be because been before being below between both but by
    can could
    did do does doing don down during
    each
    few for from further
    get given
    had has have having he her here hers herself him himself his how however
    i if in into is it its itself
    just
    may me more most my myself
    no nor not now
    of off on once only or other our ours ourselves out over own
    per
    s same shall she should so some such
    t than that the their theirs them themselves then there these they
    this those through to too
    under until up us use used using
    very
    was we were what when where which while who whom why will with would
    you your yours yourself yourselves
    """.split()
)

_STRIP_RE = re.compile(
    r"```.*?```"             # fenced code blocks
    r"|<[^>]+>"              # HTML tags
    r"|!\[[^\]]*\]\([^)]*\)" # markdown images
    r"|\[[^\]]*\]\([^)]*\)", # markdown links
    re.DOTALL,
)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
_PHRASE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{1,}")


def _strip_metadata_prefix(text: str) -> str:
    """Strip the '[doc: ...] [path: ...] [page: ...]' prefix line injected by chunking."""
    newline = text.find("\n")
    if newline > 0 and text[:newline].lstrip().startswith("[doc:"):
        return text[newline + 1 :]
    return text


def _clean(text: str) -> str:
    text = _strip_metadata_prefix(text)
    return _STRIP_RE.sub(" ", text)


def _words(text: str) -> List[str]:
    return [
        tok.lower()
        for tok in _TOKEN_RE.findall(_clean(text))
        if tok.lower() not in _STOPWORDS
    ]


def _ngrams(text: str, n: int) -> List[str]:
    tokens = [tok.lower() for tok in _PHRASE_TOKEN_RE.findall(_clean(text))]
    out = []
    for i in range(len(tokens) - n + 1):
        gram = tokens[i : i + n]
        if all(w not in _STOPWORDS and len(w) >= 2 for w in gram):
            out.append(" ".join(gram))
    return out


def _chunk_keywords(
    word_counts: Counter,
    phrase_counts: Counter,
    idf: Dict[str, float],
    top_n: int,
) -> List[Dict[str, Any]]:
    """TF-IDF scored keywords for a single chunk; phrases get a 1.5× semantic boost."""
    total_w = sum(word_counts.values()) or 1
    total_p = sum(phrase_counts.values()) or 1

    scores: Dict[str, float] = {}
    for w, cnt in word_counts.items():
        scores[w] = (cnt / total_w) * idf.get(w, 1.0)
    for p, cnt in phrase_counts.items():
        scores[p] = (cnt / total_p) * idf.get(p, 1.0) * 1.5

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{"keyword": kw, "score": round(sc, 6)} for kw, sc in ranked if sc > 0]


def run_stage4_keywords(
    root_dir: Path,  # noqa: ARG001 – kept for CLI backward-compatibility
    pdf_folder_name: str,
    out_root: Path,
    top_n: int = 30,
    min_count: int = 2,
    top_n_phrases: int | None = None,
) -> None:
    """
    Read texts_final.json, add a 'keywords' field to every chunk using TF-IDF,
    write the updated texts_final.json back in place, then write keywords.json
    with the top globally-significant words and phrases.
    """
    if top_n_phrases is None:
        top_n_phrases = top_n

    texts_path = out_root / pdf_folder_name / "texts_final.json"
    if not texts_path.exists():
        raise FileNotFoundError(f"texts_final.json not found: {texts_path}")

    chunks: List[Dict[str, Any]] = json.loads(texts_path.read_text(encoding="utf-8"))
    if not chunks:
        print(f"[{pdf_folder_name}] texts_final.json is empty — nothing to do.")
        return

    # ── 1. Extract per-chunk term counts ──────────────────────────────────────
    chunk_wc: List[Counter] = []
    chunk_pc: List[Counter] = []
    for chunk in chunks:
        text = chunk.get("text") or ""
        chunk_wc.append(Counter(_words(text)))
        chunk_pc.append(Counter(_ngrams(text, 2) + _ngrams(text, 3)))

    # ── 2. Compute IDF (across chunks) ───────────────────────────────────────
    n = len(chunks)
    df: Counter = Counter()
    for wc in chunk_wc:
        df.update(wc.keys())
    for pc in chunk_pc:
        df.update(pc.keys())

    idf: Dict[str, float] = {
        term: math.log(n / (1 + cnt)) + 1.0
        for term, cnt in df.items()
    }

    # ── 3. Annotate each chunk with top-N TF-IDF keywords ────────────────────
    global_wc: Counter = Counter()
    global_pc: Counter = Counter()
    for i, chunk in enumerate(chunks):
        chunk["keywords"] = _chunk_keywords(chunk_wc[i], chunk_pc[i], idf, top_n)
        global_wc.update(chunk_wc[i])
        global_pc.update(chunk_pc[i])

    # ── 4. Write updated texts_final.json ────────────────────────────────────
    write_json(texts_path, chunks)

    # ── 5. Build global keywords.json ────────────────────────────────────────
    # Score = count × IDF  →  frequent AND semantically distinctive terms rank high.
    # Phrases get the same 1.5× boost as in chunk scoring.
    def _global_score(term: str, count: int, boost: float = 1.0) -> float:
        return count * idf.get(term, 1.0) * boost

    top_words = sorted(
        [
            {"keyword": w, "count": cnt, "score": round(_global_score(w, cnt), 4), "type": "word"}
            for w, cnt in global_wc.items()
            if cnt >= min_count
        ],
        key=lambda x: x["score"],
        reverse=True,
    )[:top_n]

    top_phrases = sorted(
        [
            {"keyword": p, "count": cnt, "score": round(_global_score(p, cnt, 1.5), 4), "type": "phrase"}
            for p, cnt in global_pc.items()
            if cnt >= min_count
        ],
        key=lambda x: x["score"],
        reverse=True,
    )[:top_n_phrases]

    results = sorted(top_words + top_phrases, key=lambda x: x["score"], reverse=True)

    out_dir = out_root / pdf_folder_name
    write_json(out_dir / "keywords.json", results)

    print(
        f"[{pdf_folder_name}] "
        f"texts_final.json updated ({len(chunks)} chunks with per-chunk keywords) | "
        f"keywords.json: {len(top_words)} words + {len(top_phrases)} phrases "
        f"-> {out_dir}"
    )
