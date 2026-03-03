from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .parsing import is_numbered_title, split_by_numbered_subheadings
from .types import FigureItem, TableItem


FIG_REF_RE = re.compile(r"\b(?:fig\.|figure)\s*([0-9]+(?:\.[0-9]+)?)\b", re.IGNORECASE)
TABLE_REF_RE = re.compile(r"\btable\s*([0-9]+(?:\.[0-9]+)?)\b", re.IGNORECASE)


def build_prefix(filename: str, section_path: Optional[str], page: Optional[int]) -> str:
    file_prefix = f"[doc: {filename}]"
    section_prefix = f" [path: {section_path}]" if section_path else ""
    page_prefix = f" [page: {page}]" if page is not None else ""
    return file_prefix + section_prefix + page_prefix + "\n"


def _split_by_max_chars(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    grouped: List[str] = []
    buf = ""
    for paragraph in paragraphs:
        if not buf:
            buf = paragraph
            continue
        if len(buf) + 2 + len(paragraph) <= max_chars:
            buf += "\n\n" + paragraph
            continue
        grouped.append(buf)
        buf = paragraph
    if buf:
        grouped.append(buf)

    final_parts = []
    for part in grouped:
        if len(part) <= max_chars:
            final_parts.append(part)
            continue
        for idx in range(0, len(part), max_chars):
            final_parts.append(part[idx : idx + max_chars])
    return final_parts


def chunk_text_blocks(
    doc_id: str,
    pdf_folder_name: str,
    text_blocks: List[Dict[str, Any]],
    figures: List[FigureItem],
    tables: List[TableItem],
    page_no: Optional[int],
    max_chars: int = 2500,
    base_id_prefix: str = "",
) -> List[Dict[str, Any]]:
    fig_path_map: Dict[str, Optional[str]] = {figure.img_no: figure.image_link for figure in figures}
    table_path_map: Dict[str, str] = {
        table.table_no: f"{doc_id}::table::{table.table_no}::p{page_no}" for table in tables
    }

    result: List[Dict[str, Any]] = []
    chunk_idx = 0

    for block in text_blocks:
        section_path = block.get("section_path")
        title = block.get("title") or ""
        content = (block.get("content") or "").strip()
        if not content:
            continue

        parts = split_by_numbered_subheadings(content) if is_numbered_title(title) else [content]
        for part in parts:
            for subpart in _split_by_max_chars(part.strip(), max_chars):
                if not subpart:
                    continue

                fig_refs = [match.group(1) for match in FIG_REF_RE.finditer(subpart)]
                table_refs = [match.group(1) for match in TABLE_REF_RE.finditer(subpart)]

                multi_list: List[str] = []
                multi_path: List[str] = []

                for number in fig_refs:
                    key = f"fig_{number}"
                    if key not in multi_list:
                        multi_list.append(key)
                        multi_path.append(fig_path_map.get(number) or "")

                for number in table_refs:
                    key = f"table_{number}"
                    if key not in multi_list:
                        multi_list.append(key)
                        multi_path.append(table_path_map.get(number, ""))

                prefix = build_prefix(pdf_folder_name, section_path, page_no)
                result.append(
                    {
                        "id": f"{base_id_prefix}{doc_id}#c{chunk_idx}",
                        "filename": pdf_folder_name,
                        "section_path": section_path,
                        "page": page_no,
                        "text": prefix + subpart.strip(),
                        "multi_data_list": multi_list,
                        "multi_data_path": multi_path,
                    }
                )
                chunk_idx += 1

    return result

