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


def _extract_words(text: str) -> List[str]:
    cleaned = _STRIP_RE.sub(" ", text)
    return [
        tok.lower()
        for tok in _TOKEN_RE.findall(cleaned)
        if tok.lower() not in _STOPWORDS
    ]


def run_stage4_keywords(
    root_dir: Path,
    pdf_folder_name: str,
    out_root: Path,
    top_n: int = 50,
    min_count: int = 2,
) -> None:
    pdf_dir = root_dir / pdf_folder_name
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF folder not found: {pdf_dir}")

    page_dirs = sorted(
        [p for p in pdf_dir.iterdir() if p.is_dir() and p.name.startswith("page_")]
    )

    counter: Counter = Counter()
    for page_dir in page_dirs:
        mmd_path = page_dir / "result.mmd"
        if not mmd_path.exists():
            continue
        raw = mmd_path.read_text(encoding="utf-8", errors="ignore")
        if raw.strip():
            counter.update(_extract_words(raw))

    results: List[Dict[str, Any]] = [
        {"keyword": word, "count": count}
        for word, count in counter.most_common(top_n)
        if count >= min_count
    ]

    out_dir = out_root / pdf_folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "keywords.json", results)
    print(f"keywords.json written ({len(results)} keywords) -> {out_dir / 'keywords.json'}")
