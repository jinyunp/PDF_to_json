from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pypdfium2
import pypdfium2.raw as pdfium_r

# PDF object type constants
_OBJ_TEXT = pdfium_r.FPDF_PAGEOBJ_TEXT    # 1
_OBJ_PATH = pdfium_r.FPDF_PAGEOBJ_PATH    # 2
_OBJ_IMAGE = pdfium_r.FPDF_PAGEOBJ_IMAGE  # 3

# Maps PDF metadata key → JSON output key
_META_KEY_MAP = {
    "Title":        "title",
    "Author":       "author",
    "Subject":      "subject",
    "Keywords":     "keywords",
    "Creator":      "creator",
    "Producer":     "producer",
    "CreationDate": "creation_date",
    "ModDate":      "mod_date",
}


def _parse_pdf_date(raw: str) -> str:
    """Convert PDF date string 'D:YYYYMMDDHHmmSSOHH'00'' to ISO-8601."""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(.*)", raw)
    if not m:
        return raw
    y, mo, d, h, mi, s, tz_raw = m.groups()
    tz = tz_raw.replace("'", ":").rstrip(":")
    if not tz or tz in ("Z", "+00:00"):
        tz = "Z"
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}{tz}"


def _clean_str(val: str) -> str:
    """Replace lone surrogate / replacement characters from PDF metadata."""
    return val.encode("utf-8", errors="replace").decode("utf-8")


def _extract_metadata(doc: pypdfium2.PdfDocument) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for pdf_key, json_key in _META_KEY_MAP.items():
        val = doc.get_metadata_value(pdf_key) or ""
        if pdf_key in ("CreationDate", "ModDate") and val.startswith("D:"):
            val = _parse_pdf_date(val)
        meta[json_key] = _clean_str(val)
    return meta


def _extract_page(page: pypdfium2.PdfPage, page_no: int) -> Dict[str, Any]:
    width, height = page.get_size()

    # Count object types
    text_obj_count = 0
    image_count = 0
    path_count = 0
    for obj in page.get_objects():
        t = obj.type
        if t == _OBJ_TEXT:
            text_obj_count += 1
        elif t == _OBJ_IMAGE:
            image_count += 1
        elif t == _OBJ_PATH:
            path_count += 1

    textpage = page.get_textpage()
    text = textpage.get_text_range().strip()
    char_count = textpage.count_chars()

    return {
        "page_no": page_no,
        "width_pt": round(width, 2),
        "height_pt": round(height, 2),
        "char_count": char_count,
        "has_text": char_count > 0,
        "image_count": image_count,
        "path_count": path_count,
        "text_obj_count": text_obj_count,
        "text": text,
    }


def extract_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract all readable information from a born-digital PDF using pypdfium2.

    Returns a dict with:
    - filename, page_count, metadata
    - pages: list of per-page dicts (text, dimensions, object counts)
    """
    doc = pypdfium2.PdfDocument(str(pdf_path))
    try:
        metadata = _extract_metadata(doc)
        pages: List[Dict[str, Any]] = []
        for i in range(len(doc)):
            page = doc[i]
            pages.append(_extract_page(page, page_no=i + 1))

    finally:
        doc.close()

    total_chars = sum(p["char_count"] for p in pages)
    total_images = sum(p["image_count"] for p in pages)

    return {
        "filename": pdf_path.name,
        "page_count": len(pages),
        "total_char_count": total_chars,
        "total_image_count": total_images,
        "metadata": metadata,
        "pages": pages,
    }


def run_pdf_extract(
    pdf_dir: Optional[Path],
    pdf_file: Optional[Path],
    out_root: Path,
) -> None:
    """
    Extract text and metadata from PDF(s) and write JSON to out_root/<stem>/pdf_extracted.json.

    Provide either pdf_dir (process all .pdf files) or pdf_file (single file).
    """
    if pdf_file:
        targets = [pdf_file]
    elif pdf_dir:
        targets = sorted(pdf_dir.glob("*.pdf"))
        if not targets:
            print(f"[pdf-extract] No .pdf files found in {pdf_dir}")
            return
    else:
        raise ValueError("Provide --pdf_dir or --pdf_file.")

    for pdf_path in targets:
        print(f"  [extracting] {pdf_path.name} ...", end="", flush=True)
        try:
            result = extract_pdf(pdf_path)
        except Exception as exc:  # noqa: BLE001
            print(f" FAILED: {exc}")
            continue

        out_dir = out_root / pdf_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "pdf_extracted.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f" done  ({result['page_count']} pages,"
            f" {result['total_char_count']} chars,"
            f" {result['total_image_count']} images)"
            f" -> {out_path}"
        )
