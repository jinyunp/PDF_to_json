from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from pptx import Presentation

# Known LibreOffice soffice binary locations (searched in order)
_SOFFICE_CANDIDATES = [
    # Standard Windows installs
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    # Linux / macOS
    "/usr/bin/soffice",
    "/usr/lib/libreoffice/program/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def _find_soffice() -> Optional[Path]:
    """Return the first soffice binary found on this machine, or None."""
    import shutil
    # 1. PATH lookup
    found = shutil.which("soffice")
    if found:
        return Path(found)
    # 2. Hard-coded candidate paths
    for candidate in _SOFFICE_CANDIDATES:
        p = Path(candidate)
        if p.exists():
            return p
    return None


def _print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(msg.encode(enc, errors="replace").decode(enc))


def _validate_pptx(src: Path) -> None:
    """Open with python-pptx to confirm the file is a valid PPTX."""
    prs = Presentation(str(src))
    if len(prs.slides) == 0:
        raise ValueError(f"PPTX has 0 slides: {src}")


def convert_pptx_to_pdf(src: Path, dst: Path, soffice: Optional[Path] = None) -> None:
    """
    Convert a single PPTX file to a born-digital PDF using LibreOffice headless.

    Validates the source file with python-pptx before conversion.

    Args:
        src:      Source .pptx file path.
        dst:      Output .pdf file path.
        soffice:  Explicit path to the soffice binary. Auto-detected if None.

    Raises:
        RuntimeError: if LibreOffice is not found.
        ValueError:   if the PPTX file is invalid (no slides).
        subprocess.CalledProcessError: if LibreOffice exits with an error.
    """
    # 1. Validate PPTX with python-pptx
    _validate_pptx(src)

    # 2. Locate soffice
    if soffice is None:
        soffice = _find_soffice()
    if soffice is None:
        raise RuntimeError(
            "LibreOffice (soffice) not found. "
            "Install from https://www.libreoffice.org/ and ensure it is on PATH."
        )

    # 3. LibreOffice outputs to the directory of the source file by default;
    #    use dst.parent as the output dir, then rename if needed.
    dst.parent.mkdir(parents=True, exist_ok=True)
    expected_out = dst.parent / (src.stem + ".pdf")

    cmd = [
        str(soffice),
        "--headless",
        "--norestore",
        "--nofirststartwizard",
        "--convert-to", "pdf",
        "--outdir", str(dst.parent.resolve()),
        str(src.resolve()),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd,
            output=result.stdout,
            stderr=result.stderr,
        )

    # 4. Rename if the caller wants a different filename
    if expected_out.resolve() != dst.resolve() and expected_out.exists():
        expected_out.replace(dst)


def convert_directory(
    raw_dir: Path,
    pdf_dir: Path,
    overwrite: bool = False,
    soffice: Optional[Path] = None,
) -> Tuple[List[Path], List[Tuple[Path, str]]]:
    """
    Convert all .pptx files in *raw_dir* to born-digital PDFs in *pdf_dir*.

    Returns:
        ok     -- list of successfully converted PDF paths
        failed -- list of (src_path, error_message) for failures
    """
    # Locate soffice once and reuse for all files
    _soffice = soffice or _find_soffice()
    if _soffice is None:
        raise RuntimeError(
            "LibreOffice (soffice) not found. "
            "Install from https://www.libreoffice.org/ and ensure it is on PATH."
        )

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
            convert_pptx_to_pdf(src, dst, soffice=_soffice)
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
