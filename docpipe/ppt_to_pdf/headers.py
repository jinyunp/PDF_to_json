"""
table-headers: Extract first-content-row of every table in PDFs → CSV

Flow per PDF:
  1. Look for existing pdf_extracted.json under <json_root>/<pdf.stem>/
  2. If not found, run extract_pdf() on the fly to create it
  3. For each page → each table_candidate, find the first row that has
     at least one non-empty cell text (= "header row")
  4. Write one CSV row per table
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import List, Optional

from .extract import extract_pdf


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _first_content_row(cells: list) -> Optional[tuple[int, list]]:
    """Return (row_index, sorted_cells) for the first row that has any text.
    Returns None if no cell in the table has text."""
    rows: dict[int, list] = {}
    for c in cells:
        rows.setdefault(c["row"], []).append(c)
    for ri in sorted(rows):
        row_cells = sorted(rows[ri], key=lambda c: c["col"])
        if any(c["text"].strip() for c in row_cells):
            return ri, row_cells
    return None


def _load_or_extract(pdf_path: Path, json_root: Path) -> dict:
    """Load existing pdf_extracted.json or run extraction and load the result."""
    json_path = json_root / pdf_path.stem / "pdf_extracted.json"
    if not json_path.exists():
        print(f"  [extract] {pdf_path.name} → {json_path.parent}/")
        extract_pdf(pdf_path, json_path.parent)
    import json
    return json.loads(json_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_table_headers(
    pdf_dir: Path,
    json_root: Path,
    out_path: Path,
) -> None:
    pdf_files = sorted(pdf_dir.glob("**/*.pdf"))
    if not pdf_files:
        print(f"[table-headers] No PDF files found under: {pdf_dir}")
        return

    all_rows: List[dict] = []
    max_cols = 0

    for pdf_path in pdf_files:
        print(f"[table-headers] {pdf_path.name}")
        try:
            data = _load_or_extract(pdf_path, json_root)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            continue

        for page in data.get("pages", []):
            page_no = page["page_no"]
            for ti, tbl in enumerate(page.get("table_candidates", [])):
                result = _first_content_row(tbl.get("cells", []))
                if result is None:
                    continue
                row_idx, row_cells = result
                texts = [c["text"].strip() for c in row_cells]
                max_cols = max(max_cols, len(texts))
                all_rows.append({
                    "pdf_file":  pdf_path.stem,
                    "page_no":   page_no,
                    "table_idx": ti,
                    "header_row_index": row_idx,
                    "_texts":    texts,
                })

    if not all_rows:
        print("[table-headers] No tables found.")
        return

    # Build final column names
    col_names = [f"col_{i}" for i in range(max_cols)]
    fieldnames = ["pdf_file", "page_no", "table_idx", "header_row_index"] + col_names

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            texts = row.pop("_texts")
            for i, t in enumerate(texts):
                row[f"col_{i}"] = t
            writer.writerow(row)

    print(f"[table-headers] {len(all_rows)} table header(s) saved → {out_path}")
