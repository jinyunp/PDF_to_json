from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

if sys.platform != "win32":
    raise RuntimeError("pptx->PDF conversion requires Windows (PowerPoint COM automation).")

import win32com.client  # noqa: E402 — win32com is Windows-only

# PowerPoint COM constants
_PP_FIXED_FORMAT_PDF = 2    # PpFixedFormatType.ppFixedFormatTypePDF
_PP_FIXED_INTENT_PRINT = 2  # PpFixedFormatIntent.ppFixedFormatIntentPrint
_PP_PRINT_OUTPUT_SLIDES = 1 # PpPrintOutputType.ppPrintOutputSlides
_PP_PRINT_ALL = 1           # PpPrintRangeType.ppPrintAll


def _abs(path: Path) -> str:
    """Return Windows absolute path string required by COM."""
    return str(path.resolve())


def _print(msg: str) -> None:
    """Print with safe encoding for Windows terminals."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))


def convert_pptx_to_pdf(src: Path, dst: Path) -> None:
    """
    Convert a single PPTX file to a born-digital PDF using PowerPoint COM.

    Born-digital settings applied:
    - BitmapMissingFonts=False  : text stays as real text even if fonts are missing
    - DocStructureTags=True     : embeds document structure for searchability
    - IncludeDocProperties=True : preserves metadata
    - UseISO19005_1=False       : standard PDF (not PDF/A which restricts features)
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    ppt_app = win32com.client.Dispatch("PowerPoint.Application")

    try:
        prs = ppt_app.Presentations.Open(
            _abs(src),
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
        try:
            prs.ExportAsFixedFormat(
                _abs(dst),
                _PP_FIXED_FORMAT_PDF,
                Intent=_PP_FIXED_INTENT_PRINT,
                FrameSlides=False,
                HandoutOrder=1,
                OutputType=_PP_PRINT_OUTPUT_SLIDES,
                PrintHiddenSlides=False,
                PrintRange=None,
                RangeType=_PP_PRINT_ALL,
                SlideShowName="",
                IncludeDocProperties=True,
                KeepIRMSettings=True,
                DocStructureTags=True,
                BitmapMissingFonts=False,
                UseISO19005_1=False,
            )
        finally:
            prs.Close()
    finally:
        ppt_app.Quit()


def convert_directory(
    raw_dir: Path,
    pdf_dir: Path,
    overwrite: bool = False,
) -> Tuple[List[Path], List[Tuple[Path, str]]]:
    """
    Convert all .pptx files in *raw_dir* to born-digital PDFs in *pdf_dir*.

    Returns:
        ok     -- list of successfully converted PDF paths
        failed -- list of (src_path, error_message) for failures
    """
    pptx_files = sorted(raw_dir.glob("*.pptx"))
    if not pptx_files:
        _print(f"No .pptx files found in {raw_dir}")
        return [], []

    ok: List[Path] = []
    failed: List[Tuple[Path, str]] = []

    for src in pptx_files:
        dst = pdf_dir / (src.stem + ".pdf")

        if dst.exists() and not overwrite:
            _print(f"  [skip] {src.name} (already exists)")
            ok.append(dst)
            continue

        _print(f"  [converting] {src.name} ...")
        try:
            convert_pptx_to_pdf(src, dst)
            _print(f"  [done] {dst.name}")
            ok.append(dst)
        except Exception as exc:  # noqa: BLE001
            _print(f"  [FAILED] {src.name}: {exc}")
            failed.append((src, str(exc)))

    return ok, failed


def run_pptx_to_pdf(
    raw_dir: Path,
    pdf_dir: Path,
    overwrite: bool = False,
) -> None:
    """Entry point called from the CLI."""
    _print(f"[pptx2pdf] {raw_dir} -> {pdf_dir}")
    ok, failed = convert_directory(raw_dir, pdf_dir, overwrite=overwrite)
    _print(f"\n[pptx2pdf] done: {len(ok)} converted, {len(failed)} failed")
    if failed:
        _print("Failed files:")
        for src, err in failed:
            _print(f"  {src.name}: {err}")
