from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdfium2
import pypdfium2.raw as pdfium_r

# ---------------------------------------------------------------------------
# PDF object type constants
# ---------------------------------------------------------------------------
_OBJ_TEXT  = pdfium_r.FPDF_PAGEOBJ_TEXT    # 1
_OBJ_PATH  = pdfium_r.FPDF_PAGEOBJ_PATH    # 2
_OBJ_IMAGE = pdfium_r.FPDF_PAGEOBJ_IMAGE   # 3

# ---------------------------------------------------------------------------
# Table-detection heuristics
# ---------------------------------------------------------------------------
# A path whose narrower dimension is <= this threshold is treated as a "line"
_LINE_THICK_PT = 3.0
# Minimum length for a line to be considered a table border
_LINE_MIN_LEN_PT = 20.0
# Two lines are "in the same cluster" if their bboxes overlap (or nearly)
_CLUSTER_GAP_PT = 8.0
# A cluster must have at least this many H-lines AND V-lines to count as table
_TABLE_MIN_H = 2
_TABLE_MIN_V = 2

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _r(v: float, n: int = 2) -> float:
    return round(v, n)


def _bbox(obj) -> Tuple[float, float, float, float]:
    return obj.get_bounds()


def _bbox_dict(x0, y0, x1, y1, prec: int = 2) -> Dict[str, float]:
    return {
        "x0": _r(x0, prec),
        "y0": _r(y0, prec),
        "x1": _r(x1, prec),
        "y1": _r(y1, prec),
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
    """Replace lone surrogates / replacement characters from PDF metadata."""
    return val.encode("utf-8", errors="replace").decode("utf-8")


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def _extract_metadata(doc: pypdfium2.PdfDocument) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for pdf_key, json_key in _META_KEY_MAP.items():
        val = doc.get_metadata_value(pdf_key) or ""
        if pdf_key in ("CreationDate", "ModDate") and val.startswith("D:"):
            val = _parse_pdf_date(val)
        meta[json_key] = _clean_str(val)
    return meta


# ---------------------------------------------------------------------------
# Text blocks  (layout-aware via textpage.get_rect)
# ---------------------------------------------------------------------------

def _extract_text_blocks(textpage) -> List[Dict[str, Any]]:
    """
    Extract text layout blocks returned by pdfium's text layout engine.

    Each block is a contiguous run of text that pdfium considers spatially
    coherent (same line / paragraph).  Coordinates are in PDF points,
    origin = bottom-left of the page.
    """
    blocks: List[Dict[str, Any]] = []
    n = textpage.count_rects()
    for i in range(n):
        x0, y0, x1, y1 = textpage.get_rect(i)
        text = textpage.get_text_bounded(x0, y0, x1, y1).strip()
        if not text:
            continue
        blocks.append({
            "block_no": i,
            "text": text,
            "bbox": _bbox_dict(x0, y0, x1, y1),
        })
    return blocks


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def _extract_images(page) -> List[Dict[str, Any]]:
    """
    Extract all image objects from the page with position and metadata.

    Fields:
    - bbox       : rendered bounding box in PDF points (bottom-left origin)
    - width_px / height_px : native pixel dimensions of the image data
    - rendered_width_pt / rendered_height_pt : size as drawn on the page
    - dpi_h / dpi_v : horizontal/vertical resolution stored in image metadata
    - colorspace : pdfium colorspace constant (1=gray,2=RGB,3=CMYK,…)
    - bits_per_pixel
    - filters    : list of compression filters (e.g. ["DCTDecode"])
    """
    results: List[Dict[str, Any]] = []
    idx = 0
    for obj in page.get_objects():
        if obj.type != _OBJ_IMAGE:
            continue

        x0, y0, x1, y1 = _bbox(obj)
        px_w, px_h = obj.get_px_size()
        mat = obj.get_matrix()

        try:
            meta = obj.get_metadata()
            dpi_h = _r(meta.horizontal_dpi, 1)
            dpi_v = _r(meta.vertical_dpi, 1)
            colorspace = int(meta.colorspace)
            bits_per_px = int(meta.bits_per_pixel)
        except Exception:
            dpi_h = dpi_v = colorspace = bits_per_px = None

        try:
            filters = list(obj.get_filters())
        except Exception:
            filters = []

        results.append({
            "image_no": idx,
            "bbox": _bbox_dict(x0, y0, x1, y1),
            "width_px": px_w,
            "height_px": px_h,
            "rendered_width_pt": _r(abs(mat.a)),
            "rendered_height_pt": _r(abs(mat.d)),
            "dpi_h": dpi_h,
            "dpi_v": dpi_v,
            "colorspace": colorspace,
            "bits_per_pixel": bits_per_px,
            "filters": filters,
        })
        idx += 1
    return results


# ---------------------------------------------------------------------------
# Table detection (heuristic via path line geometry)
# ---------------------------------------------------------------------------

def _classify_lines(
    page,
) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Collect thin path objects and classify them as horizontal or vertical lines.

    Returns (h_lines, v_lines) where each element is (x0, y0, x1, y1).
    """
    h_lines: List[Tuple] = []
    v_lines: List[Tuple] = []

    for obj in page.get_objects():
        if obj.type != _OBJ_PATH:
            continue
        x0, y0, x1, y1 = _bbox(obj)
        w = x1 - x0
        h = y1 - y0
        if w <= 0 or h <= 0:
            continue

        is_h = (h <= _LINE_THICK_PT) and (w >= _LINE_MIN_LEN_PT)
        is_v = (w <= _LINE_THICK_PT) and (h >= _LINE_MIN_LEN_PT)

        if is_h:
            h_lines.append((x0, y0, x1, y1))
        elif is_v:
            v_lines.append((x0, y0, x1, y1))

    return h_lines, v_lines


def _bbox_overlaps(a: Tuple, b: Tuple, gap: float) -> bool:
    """True if two bboxes overlap (with a tolerance gap)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return (
        ax0 - gap < bx1 and ax1 + gap > bx0
        and ay0 - gap < by1 and ay1 + gap > by0
    )


def _union_bbox(lines: List[Tuple]) -> Tuple[float, float, float, float]:
    x0 = min(l[0] for l in lines)
    y0 = min(l[1] for l in lines)
    x1 = max(l[2] for l in lines)
    y1 = max(l[3] for l in lines)
    return x0, y0, x1, y1


def _detect_tables(h_lines: List[Tuple], v_lines: List[Tuple]) -> List[Dict[str, Any]]:
    """
    Cluster H-lines and V-lines into groups whose bboxes overlap.
    A cluster with >= _TABLE_MIN_H horizontal AND >= _TABLE_MIN_V vertical
    lines is flagged as a table candidate.
    """
    if not h_lines or not v_lines:
        return []

    all_lines = [("h", l) for l in h_lines] + [("v", l) for l in v_lines]

    # Union-Find style grouping
    n = len(all_lines)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            if _bbox_overlaps(all_lines[i][1], all_lines[j][1], _CLUSTER_GAP_PT):
                union(i, j)

    # Collect clusters
    from collections import defaultdict
    clusters: Dict[int, List] = defaultdict(list)
    for i, (kind, line) in enumerate(all_lines):
        clusters[find(i)].append((kind, line))

    tables: List[Dict[str, Any]] = []
    for group in clusters.values():
        hs = [l for k, l in group if k == "h"]
        vs = [l for k, l in group if k == "v"]
        if len(hs) >= _TABLE_MIN_H and len(vs) >= _TABLE_MIN_V:
            all_seg = hs + vs
            ux0, uy0, ux1, uy1 = _union_bbox(all_seg)
            tables.append({
                "bbox": _bbox_dict(ux0, uy0, ux1, uy1),
                "h_line_count": len(hs),
                "v_line_count": len(vs),
            })

    return tables


# ---------------------------------------------------------------------------
# Per-page extraction
# ---------------------------------------------------------------------------

def _extract_page(page: pypdfium2.PdfPage, page_no: int) -> Dict[str, Any]:
    width, height = page.get_size()

    # ── object counts ──────────────────────────────────────────────────────
    text_obj_count = image_count = path_count = 0
    for obj in page.get_objects():
        t = obj.type
        if t == _OBJ_TEXT:
            text_obj_count += 1
        elif t == _OBJ_IMAGE:
            image_count += 1
        elif t == _OBJ_PATH:
            path_count += 1

    # ── full text + layout blocks ──────────────────────────────────────────
    textpage = page.get_textpage()
    full_text = textpage.get_text_range().strip()
    char_count = textpage.count_chars()
    text_blocks = _extract_text_blocks(textpage)

    # ── images ────────────────────────────────────────────────────────────
    images = _extract_images(page)

    # ── table candidates ──────────────────────────────────────────────────
    h_lines, v_lines = _classify_lines(page)
    table_candidates = _detect_tables(h_lines, v_lines)

    return {
        "page_no": page_no,
        "width_pt": _r(width),
        "height_pt": _r(height),
        # coordinate system note: PDF origin is bottom-left of the page;
        # y increases upward.  All bbox values follow this convention.
        "coordinate_system": "pdf_bottom_left",
        "char_count": char_count,
        "has_text": char_count > 0,
        "image_count": image_count,
        "path_count": path_count,
        "text_obj_count": text_obj_count,
        "text": full_text,
        "text_blocks": text_blocks,
        "images": images,
        "table_candidates": table_candidates,
    }


# ---------------------------------------------------------------------------
# Document-level extraction
# ---------------------------------------------------------------------------

def extract_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract all readable information from a born-digital PDF using pypdfium2.

    Per-page output includes:
    - full text + text_blocks (layout blocks with bbox)
    - images (bbox, pixel size, DPI, colorspace, compression filters)
    - table_candidates (heuristic from line path geometry)
    """
    doc = pypdfium2.PdfDocument(str(pdf_path))
    try:
        metadata = _extract_metadata(doc)
        pages: List[Dict[str, Any]] = []
        for i in range(len(doc)):
            pages.append(_extract_page(doc[i], page_no=i + 1))
    finally:
        doc.close()

    total_chars  = sum(p["char_count"]  for p in pages)
    total_images = sum(p["image_count"] for p in pages)
    total_tables = sum(len(p["table_candidates"]) for p in pages)

    return {
        "filename": pdf_path.name,
        "page_count": len(pages),
        "total_char_count": total_chars,
        "total_image_count": total_images,
        "total_table_candidates": total_tables,
        "metadata": metadata,
        "pages": pages,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def run_pdf_extract(
    pdf_dir: Optional[Path],
    pdf_file: Optional[Path],
    out_root: Path,
) -> None:
    """
    Extract text/layout/images/tables from PDF(s) and write
    out_root/<stem>/pdf_extracted.json for each file.

    Provide either pdf_dir (all .pdf files) or pdf_file (single file).
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
            f" {result['total_image_count']} images,"
            f" {result['total_table_candidates']} table candidates)"
            f" -> {out_path}"
        )
