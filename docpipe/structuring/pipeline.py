from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .builders import build_images_sum_final, build_tables_str_final
from .chunking import chunk_text_blocks
from .io_utils import append_empty_page, write_json
from .parsing import parse_mmd, parse_page_no


def _init_output_buckets() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "texts_final": [],
        "tables_str_final": [],
        "tables_unstr_final": [],
        "images_formula_final": [],
        "images_sum_final": [],
        "images_trans_final": [],
    }


def run(root_dir: Path, pdf_folder_name: str, out_root: Path) -> None:
    pdf_dir = root_dir / pdf_folder_name
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF folder not found: {pdf_dir}")

    out_dir = out_root / pdf_folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    empty_log = out_dir / "empty_pages.txt"

    buckets = _init_output_buckets()
    page_dirs = sorted([path for path in pdf_dir.iterdir() if path.is_dir() and path.name.startswith("page_")])

    for page_dir in page_dirs:
        page_no = parse_page_no(page_dir.name)
        mmd_path = page_dir / "result.mmd"
        if not mmd_path.exists():
            append_empty_page(empty_log, page_dir.name)
            continue

        raw = mmd_path.read_text(encoding="utf-8", errors="ignore")
        if not raw.strip():
            append_empty_page(empty_log, page_dir.name)
            continue

        text_blocks, figures, tables = parse_mmd(
            mmd_path=mmd_path,
            pdf_folder_name=pdf_folder_name,
            doc_id=pdf_folder_name,
            page_no=page_no,
        )

        buckets["texts_final"].extend(
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
        buckets["images_sum_final"].extend(build_images_sum_final(figures))
        buckets["tables_str_final"].extend(build_tables_str_final(tables))

    write_json(out_dir / "texts_final.json", buckets["texts_final"])
    write_json(out_dir / "tables_str_final.json", buckets["tables_str_final"])
    write_json(out_dir / "tables_unstr_final.json", buckets["tables_unstr_final"])
    write_json(out_dir / "images_formula_final.json", buckets["images_formula_final"])
    write_json(out_dir / "images_sum_final.json", buckets["images_sum_final"])
    write_json(out_dir / "images_trans_final.json", buckets["images_trans_final"])

