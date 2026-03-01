from __future__ import annotations

import contextlib
import logging
import os
import sys
from pathlib import Path
from typing import Generator, List, Optional

from .quality import DeepSeekOCR2Runner


@contextlib.contextmanager
def _quiet_mode() -> Generator[None, None, None]:
    """Suppress all stdout/stderr noise at the file-descriptor level."""
    for name in ("transformers", "torch", "accelerate", "filelock", "PIL", "urllib3"):
        logging.getLogger(name).setLevel(logging.ERROR)
    try:
        from transformers import logging as hf_logging
        hf_logging.set_verbosity_error()
    except Exception:
        pass

    # Flush before redirecting so buffered Python output isn't lost.
    sys.stdout.flush()
    sys.stderr.flush()

    # Duplicate the real fds so we can restore them later.
    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        # Also swap Python-level streams so logging handlers are silenced too.
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
        try:
            yield
        finally:
            sys.stdout.close()
            sys.stderr.close()
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    finally:
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)
        os.close(devnull_fd)


def _collect_pdf_paths(pdf_input: Path) -> List[Path]:
    if pdf_input.is_file():
        if pdf_input.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {pdf_input}")
        return [pdf_input]
    if pdf_input.is_dir():
        pdfs = sorted(pdf_input.glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError(f"No PDF files found in: {pdf_input}")
        return pdfs
    raise FileNotFoundError(f"Input path not found: {pdf_input}")


def run_stage1_ocr(
    pdf_input: Path,
    out_root: Path,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    dpi: int = 200,
    device: Optional[str] = None,
    verbose: bool = False,
) -> None:
    import fitz

    pdf_paths = _collect_pdf_paths(pdf_input)
    out_root.mkdir(parents=True, exist_ok=True)
    runner = DeepSeekOCR2Runner(device=device)
    zoom = dpi / 72.0

    tty = sys.stdout
    for pdf_path in pdf_paths:
        doc = fitz.open(str(pdf_path))
        try:
            total_pages = len(doc)
            page_start = 1 if start_page is None else start_page
            page_end = total_pages if end_page is None else end_page
            if page_start < 1 or page_end > total_pages or page_start > page_end:
                raise ValueError(
                    f"Invalid page range for {pdf_path.name}: "
                    f"{page_start}~{page_end} (Total pages: {total_pages})"
                )

            pdf_name = pdf_path.stem
            pdf_out_dir = out_root / pdf_name
            pdf_out_dir.mkdir(parents=True, exist_ok=True)

            total_in_range = page_end - page_start + 1
            all_markdown = []
            for page_no in range(page_start, page_end + 1):
                if not verbose:
                    idx = page_no - page_start + 1
                    tty.write(f"\r[{pdf_path.name}] {idx}/{total_in_range} 페이지 처리 중...")
                    tty.flush()
                page = doc.load_page(page_no - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)

                page_image_path = pdf_out_dir / f"page_{page_no:04d}.png"
                page_dir = pdf_out_dir / f"page_{page_no:04d}"
                page_dir.mkdir(parents=True, exist_ok=True)

                pix.save(str(page_image_path))
                with (_quiet_mode() if not verbose else contextlib.nullcontext()):
                    runner.infer_page(image_file=page_image_path, output_path=page_dir)

                mmd_path = page_dir / "result.mmd"
                page_md = mmd_path.read_text(encoding="utf-8", errors="ignore") if mmd_path.exists() else ""
                all_markdown.append(f"\n\n<!-- Page {page_no} -->\n\n{page_md}")

            if not verbose:
                tty.write("\n")
                tty.flush()
            merged_md = pdf_out_dir / f"{pdf_name}_{page_start}-{page_end}.md"
            merged_md.write_text("".join(all_markdown), encoding="utf-8")
        finally:
            doc.close()
