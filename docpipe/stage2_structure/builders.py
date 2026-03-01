from __future__ import annotations

from typing import Any, Dict, List

from .chunking import build_prefix
from .types import FigureItem, TableItem


def build_images_sum_final(figures: List[FigureItem]) -> List[Dict[str, Any]]:
    result = []
    for figure in figures:
        prefix = build_prefix(figure.filename, figure.section_path, figure.page)
        original = figure.caption.strip() if figure.caption.strip() else "No Description"
        result.append(
            {
                "id": f"{figure.doc_id}#fig{figure.img_no}::p{figure.page}",
                "placeholder": None,
                "component_type": "image",
                "original": original,
                "text": prefix + original,
                "keyword": [],
                "image_link": figure.image_link,
                "section_path": figure.section_path,
                "filename": figure.filename,
                "page": figure.page,
                "img_no": figure.img_no,
            }
        )
    return result


def build_tables_str_final(tables: List[TableItem]) -> List[Dict[str, Any]]:
    result = []
    for table in tables:
        prefix = build_prefix(table.filename, table.section_path, table.page)
        combined = table.caption.strip()
        html = (table.table_md or "").strip()
        if html:
            combined = combined + "\n\n" + html
        original = combined if combined else "No Description"

        result.append(
            {
                "id": f"{table.doc_id}#table{table.table_no}::p{table.page}",
                "component_type": "table",
                "original": original,
                "text": prefix + original,
                "image_link": None,
                "section_path": table.section_path,
                "filename": table.filename,
                "page": table.page,
                "placeholder": None,
                "table_no": table.table_no,
            }
        )
    return result

