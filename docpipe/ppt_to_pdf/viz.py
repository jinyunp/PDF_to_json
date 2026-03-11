from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pypdfium2
from PIL import Image, ImageDraw

# Render DPI (higher = sharper but slower)
_DEFAULT_DPI = 150

# ── bbox colours ─────────────────────────────────────────────────────────────
#   each entry: (R, G, B, A) — A is used for outline; fill uses a lighter alpha
_COLORS: Dict[str, Tuple[int, int, int, int]] = {
    "text_block":         (220,  50,  50, 255),  # red  — regular text block
    "text_in_table":      (255, 150,   0, 255),  # orange — text block inside a table
    "image":              ( 30, 130, 255, 255),  # blue  — image
    "table_candidate":    ( 30, 180,  60, 255),  # green — table candidate boundary
    "cell":               (160,   0, 220, 255),  # purple — individual table cell
}
_FILL_ALPHA   = 30   # semi-transparent fill (0-255)
_TEXT_WIDTH   = 1    # outline width for text blocks (px)
_OBJ_WIDTH    = 2    # outline width for images / tables (px)


# ── helpers ───────────────────────────────────────────────────────────────────

def _pt_to_px(v: float, scale: float) -> int:
    return round(v * scale)


def _pdf_to_img(
    x0: float, y0: float, x1: float, y1: float,
    page_h: float, scale: float,
) -> Tuple[int, int, int, int]:
    """PDF coords (bottom-left origin, pt) → image coords (top-left origin, px)."""
    return (
        _pt_to_px(x0, scale),
        _pt_to_px(page_h - y1, scale),
        _pt_to_px(x1, scale),
        _pt_to_px(page_h - y0, scale),
    )


def _center(bbox: Dict) -> Tuple[float, float]:
    return (
        (bbox["x0"] + bbox["x1"]) / 2,
        (bbox["y0"] + bbox["y1"]) / 2,
    )


def _inside(point: Tuple[float, float], bbox: Dict, margin: float = 1.0) -> bool:
    """True if point is inside (or within margin pt of) bbox."""
    cx, cy = point
    return (
        bbox["x0"] - margin <= cx <= bbox["x1"] + margin
        and bbox["y0"] - margin <= cy <= bbox["y1"] + margin
    )


def _draw_rect(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    color: Tuple[int, int, int, int],
    width: int,
) -> None:
    r, g, b, a = color
    fill = (r, g, b, _FILL_ALPHA)
    draw.rectangle(list(box), fill=fill, outline=(r, g, b, a), width=width)


# ── per-page renderer ─────────────────────────────────────────────────────────

def render_page_with_bboxes(
    pdf_path: Path,
    page_data: Dict,
    dpi: int = _DEFAULT_DPI,
    draw_text_blocks: bool = True,
    draw_images: bool = True,
    draw_tables: bool = True,
    draw_cells: bool = True,
) -> Image.Image:
    """
    Render one PDF page and overlay bbox annotations:
    - red    : text_block (outside any table)
    - orange : text_block (inside a table_candidate)
    - blue   : image
    - green  : table_candidate boundary
    """
    scale = dpi / 72.0
    page_no = page_data["page_no"]
    page_h = page_data["height_pt"]

    # ── render PDF page ────────────────────────────────────────────────────
    doc = pypdfium2.PdfDocument(str(pdf_path))
    try:
        page = doc[page_no - 1]
        bitmap = page.render(scale=scale, rotation=0)
        pil_img = bitmap.to_pil().convert("RGBA")
    finally:
        doc.close()

    overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def to_px(bbox_dict):
        return _pdf_to_img(
            bbox_dict["x0"], bbox_dict["y0"],
            bbox_dict["x1"], bbox_dict["y1"],
            page_h, scale,
        )

    table_bboxes = page_data.get("table_candidates", [])

    # ── layer 1: table candidate regions (drawn first / bottom) ───────────
    if draw_tables:
        for tbl in table_bboxes:
            _draw_rect(draw, to_px(tbl["bbox"]),
                       _COLORS["table_candidate"], _OBJ_WIDTH)

    # ── layer 2: individual table cells ───────────────────────────────────
    if draw_cells:
        for tbl in table_bboxes:
            for cell in tbl.get("cells", []):
                if cell["width_pt"] > 3.0 and cell["height_pt"] > 3.0:
                    _draw_rect(draw, to_px(cell["bbox"]),
                               _COLORS["cell"], _TEXT_WIDTH)

    # ── layer 3: text blocks — split into inside-table / outside-table ────
    if draw_text_blocks:
        for blk in page_data.get("text_blocks", []):
            cx, cy = _center(blk["bbox"])
            in_table = any(_inside((cx, cy), t["bbox"]) for t in table_bboxes)
            color_key = "text_in_table" if in_table else "text_block"
            _draw_rect(draw, to_px(blk["bbox"]),
                       _COLORS[color_key], _TEXT_WIDTH)

    # ── layer 4: images (top layer — always visible) ───────────────────────
    if draw_images:
        for img_obj in page_data.get("images", []):
            _draw_rect(draw, to_px(img_obj["bbox"]),
                       _COLORS["image"], _OBJ_WIDTH)

    annotated = Image.alpha_composite(pil_img, overlay).convert("RGB")
    return annotated


# ── CLI entry point ───────────────────────────────────────────────────────────

def run_viz(
    pdf_path: Path,
    json_path: Path,
    out_dir: Path,
    pages: Optional[List[int]],
    dpi: int = _DEFAULT_DPI,
    draw_text_blocks: bool = True,
    draw_images: bool = True,
    draw_tables: bool = True,
    draw_cells: bool = True,
) -> None:
    """
    Render annotated page images and save them to out_dir as PNG files.

    Legend:
        red    = text_block (outside table)
        orange = text_block (inside table_candidate)
        blue   = image
        green  = table_candidate boundary
        purple = individual table cell
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    all_pages = data["pages"]
    target_pages = (
        [p for p in all_pages if p["page_no"] in pages]
        if pages else all_pages
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    print("  legend: red=text_block  orange=text_in_table  "
          "blue=image  green=table_candidate  purple=cell")

    for page_data in target_pages:
        pno = page_data["page_no"]
        tbl_bboxes = page_data.get("table_candidates", [])

        # count text blocks inside vs outside tables
        n_in = n_out = 0
        for blk in page_data.get("text_blocks", []):
            cx, cy = _center(blk["bbox"])
            if any(_inside((cx, cy), t["bbox"]) for t in tbl_bboxes):
                n_in += 1
            else:
                n_out += 1

        print(
            f"  page {pno:>3}: "
            f"text={n_out}(+{n_in} in-table)  "
            f"img={len(page_data.get('images', []))}  "
            f"tables={len(tbl_bboxes)}"
            f" ...",
            end="", flush=True,
        )

        img = render_page_with_bboxes(
            pdf_path, page_data, dpi=dpi,
            draw_text_blocks=draw_text_blocks,
            draw_images=draw_images,
            draw_tables=draw_tables,
            draw_cells=draw_cells,
        )
        out_path = out_dir / f"page_{pno:04d}.png"
        img.save(out_path, "PNG")
        print(f" -> {out_path.name}")
