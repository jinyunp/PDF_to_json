from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docpipe.structuring import (
    build_images_sum_final,
    build_tables_str_final,
    chunk_text_blocks,
    parse_mmd,
    parse_page_no,
)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_unique(log_path: Path, line: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if log_path.exists():
        existing = {x.strip() for x in log_path.read_text(encoding="utf-8").splitlines() if x.strip()}
    if line not in existing:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def run_stage2_structure(root_dir: Path, pdf_folder_name: str, out_root: Path) -> None:
    pdf_dir = root_dir / pdf_folder_name
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF folder not found: {pdf_dir}")

    out_dir = out_root / pdf_folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    empty_log = out_dir / "empty_pages_structuring.txt"

    texts_final = []
    tables_str_final = []
    tables_unstr_final = []
    images_formula_final = []
    images_sum_final = []
    images_trans_final = []

    page_dirs = sorted([p for p in pdf_dir.iterdir() if p.is_dir() and p.name.startswith("page_")])

    for page_dir in page_dirs:
        page_no = parse_page_no(page_dir.name)
        mmd_path = page_dir / "result.mmd"

        if not mmd_path.exists():
            _append_unique(empty_log, page_dir.name)
            continue

        raw = mmd_path.read_text(encoding="utf-8", errors="ignore")
        if not raw.strip():
            _append_unique(empty_log, page_dir.name)
            continue

        text_blocks, figures, tables = parse_mmd(
            mmd_path=mmd_path,
            pdf_folder_name=pdf_folder_name,
            doc_id=pdf_folder_name,
            page_no=page_no,
        )

        texts_final.extend(
            chunk_text_blocks(
                doc_id=pdf_folder_name,
                pdf_folder_name=pdf_folder_name,
                text_blocks=text_blocks,
                figures=figures,
                tables=tables,
                page_no=page_no,
                max_chars=2500,
                base_id_prefix=f"{page_dir.name}::",
            )
        )
        images_sum_final.extend(build_images_sum_final(figures))
        tables_str_final.extend(build_tables_str_final(tables))

    _write_json(out_dir / "texts_final.json", texts_final)
    _write_json(out_dir / "tables_str_final.json", tables_str_final)
    _write_json(out_dir / "images_sum_final.json", images_sum_final)
    _write_json(out_dir / "tables_unstr_final.json", tables_unstr_final)
    _write_json(out_dir / "images_formula_final.json", images_formula_final)
    _write_json(out_dir / "images_trans_final.json", images_trans_final)
