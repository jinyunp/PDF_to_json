from __future__ import annotations

import argparse
from pathlib import Path

from .ocr import run_stage1_ocr
from .quality import run_check_completed, run_stage2_quality
from .structure import run_stage2_structure
from .keywords import run_stage4_keywords
from .ppt_to_pdf import run_pptx_to_pdf, run_pdf_extract, run_viz, run_table_headers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docpipe")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # ── stage1: OCR ──────────────────────────────────────────────────────────
    ocr = subparsers.add_parser("stage1_ocr", help="PDF -> DeepSeek OCR markdown")
    ocr.add_argument("--pdf_input", required=True, help="PDF file or directory")
    ocr.add_argument("--out_root", default="data/ocr", help="OCR output root")
    ocr.add_argument("--start_page", type=int, default=None, help="1-based start page")
    ocr.add_argument("--end_page", type=int, default=None, help="1-based end page")
    ocr.add_argument("--dpi", type=int, default=200, help="Render DPI")
    ocr.add_argument("--device", default=None, help="Force cuda/cpu")
    ocr.add_argument("--verbose", default=False, action="store_true", help="Show detailed output")

    # ── stage2: retry empty mmd ───────────────────────────────────────────────
    quality = subparsers.add_parser("stage2_quality", help="Retry OCR for empty result.mmd files")
    quality.add_argument("--root_dir", default="data/ocr", help="OCR root directory")
    quality.add_argument("--pdf", required=True, help="PDF folder name")
    quality.add_argument("--max_retry", type=int, default=1, help="Max retry count")
    quality.add_argument("--device", default=None, help="Force cuda/cpu")

    # ── stage3: structure ─────────────────────────────────────────────────────
    structure = subparsers.add_parser("stage3_structure", help="mmd -> structured JSON")
    structure.add_argument("--root_dir", default="data/ocr", help="OCR root directory")
    structure.add_argument("--pdf", required=True, help="PDF folder name")
    structure.add_argument("--out_root", default="data/json_output", help="JSON output root")

    # ── stage4: keywords ──────────────────────────────────────────────────────
    keywords = subparsers.add_parser("stage4_keywords", help="Extract frequent keywords from mmd files")
    keywords.add_argument("--root_dir", default="data/ocr", help="OCR root directory")
    keywords.add_argument("--pdf", required=True, help="PDF folder name")
    keywords.add_argument("--out_root", default="data/json_output", help="JSON output root")
    keywords.add_argument("--top_n", type=int, default=50, help="Number of top single keywords")
    keywords.add_argument("--top_n_phrases", type=int, default=None, help="Number of top phrases (default: same as top_n)")
    keywords.add_argument("--min_count", type=int, default=2, help="Minimum occurrence count")

    # ── aliases ───────────────────────────────────────────────────────────────
    ocr_alias = subparsers.add_parser("ocr", help="alias of stage1_ocr")
    ocr_alias.add_argument("--pdf_input", required=True)
    ocr_alias.add_argument("--out_root", default="data/ocr")
    ocr_alias.add_argument("--start_page", type=int, default=None)
    ocr_alias.add_argument("--end_page", type=int, default=None)
    ocr_alias.add_argument("--dpi", type=int, default=200)
    ocr_alias.add_argument("--device", default=None)
    ocr_alias.add_argument("--verbose", action="store_true")

    retry_empty = subparsers.add_parser("retry-empty", help="alias of stage2_quality")
    retry_empty.add_argument("--root_dir", default="data/ocr")
    retry_empty.add_argument("--pdf", required=True)
    retry_empty.add_argument("--max_retry", type=int, default=1)
    retry_empty.add_argument("--device", default=None)

    structure_alias = subparsers.add_parser("structure", help="alias of stage3_structure")
    structure_alias.add_argument("--root_dir", default="data/ocr")
    structure_alias.add_argument("--pdf", required=True)
    structure_alias.add_argument("--out_root", default="data/json_output")

    keywords_alias = subparsers.add_parser("keywords", help="alias of stage4_keywords")
    keywords_alias.add_argument("--root_dir", default="data/ocr")
    keywords_alias.add_argument("--pdf", required=True)
    keywords_alias.add_argument("--out_root", default="data/json_output")
    keywords_alias.add_argument("--top_n", type=int, default=50)
    keywords_alias.add_argument("--top_n_phrases", type=int, default=None)
    keywords_alias.add_argument("--min_count", type=int, default=2)

    # ── check: list completed pages ───────────────────────────────────────────
    check = subparsers.add_parser("check", help="List pages with completed OCR results")
    check.add_argument("--root_dir", default="data/ocr", help="OCR root directory")
    check.add_argument("--pdf", required=True, help="PDF folder name")

    # ── pptx2pdf: PPTX → born-digital PDF (Windows only) ─────────────────────
    p2p = subparsers.add_parser("pptx2pdf", help="Convert .pptx files to born-digital PDF via PowerPoint COM (Windows only)")
    p2p.add_argument("--raw_dir", default="data/raw", help="Directory containing .pptx files (기본: data/raw)")
    p2p.add_argument("--pdf_dir", default="data/pdf", help="Output directory for PDF files (기본: data/pdf)")
    p2p.add_argument("--overwrite", action="store_true", help="Overwrite existing PDF files")

    # ── pdf-extract: born-digital PDF → JSON (pypdfium2) ─────────────────────
    pex = subparsers.add_parser("pdf-extract", help="Extract text/metadata from PDF(s) into JSON using pypdfium2")
    pex_src = pex.add_mutually_exclusive_group(required=True)
    pex_src.add_argument("--pdf_dir", help="Directory of .pdf files to process (e.g. data/pdf)")
    pex_src.add_argument("--pdf_file", help="Single .pdf file to process")
    pex.add_argument("--out_root", default="data/json_output", help="JSON output root (기본: data/json_output)")

    # ── table-headers: 표 헤더 추출 → CSV ────────────────────────────────────
    th = subparsers.add_parser("table-headers", help="Extract first-content row of every table in PDFs → CSV")
    th.add_argument("--pdf_dir", required=True, help="Directory containing PDF files (recursively searched)")
    th.add_argument("--json_root", default="data/json_output", help="Root for pdf_extracted.json files (기본: data/json_output)")
    th.add_argument("--out", default=None, help="Output CSV path (기본: <json_root>/table_headers.csv)")

    # ── pdf-viz: bbox 시각화 ──────────────────────────────────────────────────
    viz = subparsers.add_parser("pdf-viz", help="Render PDF pages with bbox overlays (text_blocks / images / table_candidates)")
    viz.add_argument("--pdf_file", required=True, help="Source PDF file (e.g. data/pdf/foo.pdf)")
    viz.add_argument("--json_file", required=True, help="pdf_extracted.json from pdf-extract (e.g. data/json_output/foo/pdf_extracted.json)")
    viz.add_argument("--out_dir", default=None, help="Output directory for PNG files (기본: json_file 디렉토리/viz)")
    viz.add_argument("--pages", nargs="*", type=int, default=None, metavar="N", help="1-based page numbers to render (기본: 전체)")
    viz.add_argument("--dpi", type=int, default=150, help="Render DPI (기본: 150)")
    viz.add_argument("--no_text", action="store_true", help="Skip text block bboxes")
    viz.add_argument("--no_image", action="store_true", help="Skip image bboxes")
    viz.add_argument("--no_table", action="store_true", help="Skip table candidate bboxes")
    viz.add_argument("--no_cell", action="store_true", help="Skip individual cell bboxes")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand in {"stage1_ocr", "ocr"}:
        run_stage1_ocr(
            pdf_input=Path(args.pdf_input),
            out_root=Path(args.out_root),
            start_page=args.start_page,
            end_page=args.end_page,
            dpi=max(args.dpi, 72),
            device=args.device,
            verbose=args.verbose,
        )
        return 0

    if args.subcommand in {"stage2_quality", "retry-empty"}:
        run_stage2_quality(
            root_dir=Path(args.root_dir),
            pdf_folder_name=args.pdf,
            max_retry=max(args.max_retry, 1),
            device=args.device,
        )
        return 0

    if args.subcommand in {"stage3_structure", "structure"}:
        run_stage2_structure(
            root_dir=Path(args.root_dir),
            pdf_folder_name=args.pdf,
            out_root=Path(args.out_root),
        )
        return 0

    if args.subcommand in {"stage4_keywords", "keywords"}:
        run_stage4_keywords(
            root_dir=Path(args.root_dir),
            pdf_folder_name=args.pdf,
            out_root=Path(args.out_root),
            top_n=args.top_n,
            min_count=args.min_count,
            top_n_phrases=args.top_n_phrases,
        )
        return 0

    if args.subcommand == "check":
        run_check_completed(
            root_dir=Path(args.root_dir),
            pdf_folder_name=args.pdf,
        )
        return 0

    if args.subcommand == "pptx2pdf":
        run_pptx_to_pdf(
            raw_dir=Path(args.raw_dir),
            pdf_dir=Path(args.pdf_dir),
            overwrite=args.overwrite,
        )
        return 0

    if args.subcommand == "pdf-extract":
        run_pdf_extract(
            pdf_dir=Path(args.pdf_dir) if args.pdf_dir else None,
            pdf_file=Path(args.pdf_file) if args.pdf_file else None,
            out_root=Path(args.out_root),
        )
        return 0

    if args.subcommand == "table-headers":
        json_root = Path(args.json_root)
        out_path = Path(args.out) if args.out else json_root / "table_headers.csv"
        run_table_headers(
            pdf_dir=Path(args.pdf_dir),
            json_root=json_root,
            out_path=out_path,
        )
        return 0

    if args.subcommand == "pdf-viz":
        json_path = Path(args.json_file)
        out_dir = Path(args.out_dir) if args.out_dir else json_path.parent / "viz"
        print(f"[pdf-viz] {Path(args.pdf_file).name} -> {out_dir}")
        run_viz(
            pdf_path=Path(args.pdf_file),
            json_path=json_path,
            out_dir=out_dir,
            pages=args.pages or None,
            dpi=args.dpi,
            draw_text_blocks=not args.no_text,
            draw_images=not args.no_image,
            draw_tables=not args.no_table,
            draw_cells=not args.no_cell,
        )
        return 0

    parser.error(f"unknown subcommand: {args.subcommand}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
