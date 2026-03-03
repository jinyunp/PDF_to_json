from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .types import FigureItem, TableItem


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)\s*$")
NUMBERED_PREFIX_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*(?:[)\].:-]\s*)?(.*)$")
FIG_CAPTION_RE = re.compile(
    r"^\s*(?:fig(?:ure)?\.?)\s*([0-9]+(?:\.[0-9]+)?)\s*[:.\-]?\s*(.*)$",
    re.IGNORECASE,
)
TABLE_CAPTION_RE = re.compile(r"^\s*table\s*([0-9]+(?:\.[0-9]+)?)\s*[:.\-]?\s*(.*)$", re.IGNORECASE)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_TABLE_START_RE = re.compile(r"^\s*<table\b", re.IGNORECASE)
HTML_TABLE_END_RE = re.compile(r"</table>\s*$", re.IGNORECASE)


def normalize_section_path(headings_stack: List[Tuple[int, str]]) -> str:
    return " > ".join([title for _, title in headings_stack])


def parse_page_no(page_dir_name: str) -> Optional[int]:
    match = re.search(r"page_(\d{4})", page_dir_name)
    if not match:
        return None
    return int(match.group(1))


def split_by_numbered_subheadings(content: str) -> List[str]:
    lines = content.splitlines()
    indices = []
    for idx, line in enumerate(lines):
        if HEADING_RE.match(line.strip()):
            continue
        matched = NUMBERED_PREFIX_RE.match(line.strip())
        if matched and re.fullmatch(r"\d+(?:\.\d+)*", (matched.group(1) or "").strip()):
            indices.append(idx)

    if len(indices) <= 1:
        return [content.strip()]

    chunks = []
    for start, end in zip(indices, indices[1:] + [len(lines)]):
        part = "\n".join(lines[start:end]).strip()
        if part:
            chunks.append(part)
    return chunks if chunks else [content.strip()]


def is_numbered_title(title: str) -> bool:
    matched = NUMBERED_PREFIX_RE.match(title.strip())
    if not matched:
        return False
    number = (matched.group(1) or "").strip()
    return bool(re.fullmatch(r"\d+(?:\.\d+)*", number))


def extract_html_table(lines: List[str], start_idx: int, scan_limit: int = 200) -> Tuple[str, int]:
    idx = start_idx
    end = min(len(lines), start_idx + scan_limit)

    while idx < end and not HTML_TABLE_START_RE.search(lines[idx]):
        idx += 1
    if idx >= end:
        return "", start_idx

    buffer = [lines[idx].rstrip("\n")]
    idx += 1

    while idx < end:
        buffer.append(lines[idx].rstrip("\n"))
        if HTML_TABLE_END_RE.search(lines[idx]):
            idx += 1
            break
        idx += 1

    return "\n".join(buffer).strip(), idx


def parse_mmd(
    mmd_path: Path,
    pdf_folder_name: str,
    doc_id: str,
    page_no: Optional[int],
) -> Tuple[List[Dict[str, Any]], List[FigureItem], List[TableItem]]:
    raw = mmd_path.read_text(encoding="utf-8", errors="ignore")
    if not raw.strip():
        return [], [], []

    lines = raw.splitlines(True)
    headings_stack: List[Tuple[int, str]] = []
    text_blocks: List[Dict[str, Any]] = []
    figures: List[FigureItem] = []
    tables: List[TableItem] = []

    current_lines: List[str] = []
    current_title: Optional[str] = None
    current_section_path: Optional[str] = None

    def flush_text_block() -> None:
        nonlocal current_lines
        content = "".join(current_lines).strip()
        if content:
            text_blocks.append(
                {
                    "title": current_title,
                    "section_path": current_section_path,
                    "content": content,
                }
            )
        current_lines = []

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        heading = HEADING_RE.match(line.strip("\n"))
        if heading:
            flush_text_block()
            level = len(heading.group(1))
            title = heading.group(2).strip()

            while headings_stack and headings_stack[-1][0] >= level:
                headings_stack.pop()
            headings_stack.append((level, title))
            current_title = title
            current_section_path = normalize_section_path(headings_stack)
            idx += 1
            continue

        figure_caption = FIG_CAPTION_RE.match(line.strip())
        if figure_caption:
            img_no = figure_caption.group(1).strip()
            caption_rest = (figure_caption.group(2) or "").strip()
            prefix_match = re.match(r"^\s*(fig(?:ure)?\.?)", line.strip(), re.IGNORECASE)
            prefix_text = prefix_match.group(1).strip().rstrip(".").capitalize()

            caption_full = f"{prefix_text} {img_no}"
            if caption_rest:
                caption_full += f": {caption_rest}"

            image_link = None
            for offset in range(1, 5):
                if idx + offset >= len(lines):
                    break
                found_img = MD_IMAGE_RE.search(lines[idx + offset])
                if found_img:
                    image_link = found_img.group(1).strip()
                    break

            figures.append(
                FigureItem(
                    doc_id=doc_id,
                    filename=pdf_folder_name,
                    section_path=current_section_path,
                    img_no=str(img_no),
                    caption=caption_full,
                    image_link=image_link,
                    page=page_no,
                )
            )
            idx += 1
            continue

        table_caption = TABLE_CAPTION_RE.match(line.strip())
        if table_caption:
            table_no = table_caption.group(1).strip()
            title_line = ""
            cursor = idx + 1
            while cursor < len(lines) and not lines[cursor].strip():
                cursor += 1
            if cursor < len(lines) and not HTML_TABLE_START_RE.search(lines[cursor]):
                title_line = lines[cursor].strip()
                cursor += 1

            html_table, next_idx = extract_html_table(lines, cursor, scan_limit=300)
            caption_full = f"Table {table_no}"
            if title_line:
                caption_full += f": {title_line}"

            tables.append(
                TableItem(
                    doc_id=doc_id,
                    filename=pdf_folder_name,
                    section_path=current_section_path,
                    table_no=str(table_no),
                    caption=caption_full,
                    table_md=html_table,
                    page=page_no,
                )
            )
            idx = next_idx if next_idx > idx else idx + 1
            continue

        current_lines.append(line)
        idx += 1

    flush_text_block()
    return text_blocks, figures, tables

