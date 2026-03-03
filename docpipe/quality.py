from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

DEEPSEEK_MODEL_ID = os.environ.get("DEEPSEEK_MODEL_ID", "/workspace/models/DeepSeek-OCR-2")


PROMPT = (
    f"""<image>\n<|grounding|>Convert the document to markdown.
    The layout of the document may show both sides in one image or just one page in a image.
    If the image shows two sides, please separate the content of the left and right sides into two sections in the markdown output.
    
    Guidelines:
    * Math: express formulas as plain strings such as "CO2 40%" or "Si2 = 0.5", use A/B for fractions, and avoid LaTeX commands like \\frac, _ or ^.
    * Tables: Use colspan and rowspan attributes to match table structure.
    * Formatting: Maintain consistent formatting with the image, including spacing, indentation, subscripts/superscripts, and special characters.
    * Images/Diagrams: summarize complex diagrams or arrow flows in a short sentence and rely on the cropped image instead of reproducing every shape.
    * Forms: Mark checkboxes and radio buttons properly.
    * Text: join lines together properly into paragraphs using <p>...</p> tags. Use <br> only when absolutely necessary.
    * Use the simplest possible HTML structure that accurately represents the content of the block.
    * Make sure the text is accurate and easy for a human to read and interpret. Reading order should be correct and natural.
    \n<|end|>\n
    """
)


def _append_unique(log_path: Path, lines: Iterable[str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if log_path.exists():
        existing = {x.strip() for x in log_path.read_text(encoding="utf-8").splitlines() if x.strip()}
    for line in lines:
        if line not in existing:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            existing.add(line)


def _find_page_image(page_dir: Path) -> Optional[Path]:
    direct = page_dir / f"{page_dir.name}.png"
    if direct.exists():
        return direct
    sibling = page_dir.parent / f"{page_dir.name}.png"
    if sibling.exists():
        return sibling
    for candidate in page_dir.glob("*.png"):
        return candidate
    return None


def _is_empty_mmd(mmd_path: Path) -> bool:
    if not mmd_path.exists():
        return True
    return not mmd_path.read_text(encoding="utf-8", errors="ignore").strip()


@dataclass
class DeepSeekOCR2Runner:
    model_id: str = DEEPSEEK_MODEL_ID
    device: Optional[str] = None
    _model: object = None
    _tokenizer: object = None

    def _load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        import torch
        from transformers import AutoModel, AutoTokenizer

        if self.device:
            device = torch.device(self.device)
        else:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.bfloat16 if device.type == "cuda" else torch.float32

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        self._model = AutoModel.from_pretrained(
            self.model_id,
            trust_remote_code=True,
            torch_dtype=dtype,
            attn_implementation="flash_attention_2",
            device_map="cuda" if device.type == "cuda" else None,
            use_safetensors=True,
        ).to(device).eval()

    def infer_page(self, image_file: Path, output_path: Path) -> None:
        self._load()
        output_path.mkdir(parents=True, exist_ok=True)
        self._model.infer(
            self._tokenizer,
            prompt=PROMPT,
            image_file=str(image_file),
            output_path=str(output_path),
            base_size=1024,
            image_size=768,
            crop_mode=True,
            save_results=True,
        )


def run_stage2_quality(root_dir: Path, pdf_folder_name: str, max_retry: int = 1, device: Optional[str] = None) -> None:
    pdf_dir = root_dir / pdf_folder_name
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF folder not found: {pdf_dir}")

    page_dirs = sorted([p for p in pdf_dir.iterdir() if p.is_dir() and p.name.startswith("page_")])
    empty_pages = [p for p in page_dirs if _is_empty_mmd(p / "result.mmd")]

    logs_dir = pdf_dir / "logs"
    quality_log = logs_dir / "empty_pages_quality.txt"
    retry_failed_log = logs_dir / "empty_pages_retry_failed.txt"
    _append_unique(quality_log, [p.name for p in empty_pages])

    if not empty_pages:
        return

    runner = DeepSeekOCR2Runner(device=device)
    failed = []

    for page_dir in empty_pages:
        image_path = _find_page_image(page_dir)
        if image_path is None:
            failed.append(page_dir.name)
            continue

        success = False
        for _ in range(max_retry):
            runner.infer_page(image_file=image_path, output_path=page_dir)
            if not _is_empty_mmd(page_dir / "result.mmd"):
                success = True
                break
        if not success:
            failed.append(page_dir.name)

    _append_unique(retry_failed_log, failed)
    run_check_completed(root_dir=root_dir, pdf_folder_name=pdf_folder_name)


def run_check_completed(root_dir: Path, pdf_folder_name: str) -> None:
    pdf_dir = root_dir / pdf_folder_name
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF folder not found: {pdf_dir}")

    page_dirs = sorted([p for p in pdf_dir.iterdir() if p.is_dir() and p.name.startswith("page_")])
    completed = [p.name for p in page_dirs if not _is_empty_mmd(p / "result.mmd")]
    missing = [p.name for p in page_dirs if _is_empty_mmd(p / "result.mmd")]

    logs_dir = pdf_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    completed_log = logs_dir / "completed_pages.txt"
    completed_log.write_text("\n".join(completed) + ("\n" if completed else ""), encoding="utf-8")

    total = len(page_dirs)
    print(f"[{pdf_folder_name}] 완료: {len(completed)}/{total} 페이지")
    print(f"저장됨: {completed_log}")
    if missing:
        print(f"미완료 페이지 ({len(missing)}개): {', '.join(missing)}")
