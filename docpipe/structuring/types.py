from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FigureItem:
    doc_id: str
    filename: str
    section_path: Optional[str]
    img_no: str
    caption: str
    image_link: Optional[str]
    page: Optional[int] = None


@dataclass
class TableItem:
    doc_id: str
    filename: str
    section_path: Optional[str]
    table_no: str
    caption: str
    table_md: str
    page: Optional[int] = None

