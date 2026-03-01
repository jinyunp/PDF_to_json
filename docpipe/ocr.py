from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .quality import DeepSeekOCR2Runner


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
) -> None:
    import fitz

    pdf_paths = _collect_pdf_paths(pdf_input)
    out_root.mkdir(parents=True, exist_ok=True)
    runner = DeepSeekOCR2Runner(device=device)
    zoom = dpi / 72.0

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

            all_markdown = []
            for page_no in range(page_start, page_end + 1):
                page = doc.load_page(page_no - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)

                page_image_path = pdf_out_dir / f"page_{page_no:04d}.png"
                page_dir = pdf_out_dir / f"page_{page_no:04d}"
                page_dir.mkdir(parents=True, exist_ok=True)

                pix.save(str(page_image_path))
                runner.infer_page(image_file=page_image_path, output_path=page_dir)

                mmd_path = page_dir / "result.mmd"
                page_md = mmd_path.read_text(encoding="utf-8", errors="ignore") if mmd_path.exists() else ""
                all_markdown.append(f"\n\n<!-- Page {page_no} -->\n\n{page_md}")

            merged_md = pdf_out_dir / f"{pdf_name}_{page_start}-{page_end}.md"
            merged_md.write_text("".join(all_markdown), encoding="utf-8")
        finally:
            doc.close()
