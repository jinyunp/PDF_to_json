from __future__ import annotations

import argparse
from pathlib import Path

from .ocr import run_stage1_ocr
from .quality import run_check_completed, run_stage2_quality
from .structure import run_stage2_structure
from .keywords import run_stage4_keywords
from .ppt_to_json import run_pptx_to_pdf


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

    parser.error(f"unknown subcommand: {args.subcommand}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
