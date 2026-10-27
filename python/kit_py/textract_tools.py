from __future__ import annotations
import subprocess, tempfile
from pathlib import Path
from typing import Optional
from kit_py.auto_bootstrap import ensure_dependencies

def copy_to_clipboard(text: str) -> None:
    try:
        subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
        print("Copied extracted text to clipboard!")
    except Exception:
        pass

def extract_text_from_image(image_path: Path) -> str:
    ensure_dependencies(packages=["PIL", "rapidocr_onnxruntime"])
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    result, _ = engine(str(image_path))
    if not result:
        return ""
    lines = [item[1] for item in result if len(item) >= 2 and item[1]]
    return "\n".join(lines).strip()

def run_textract(
    input_path: Optional[Path] = None,
    from_clipboard: bool = False,
    output_path: Optional[Path] = None,
    copy_result: bool = False,
) -> str:
    if from_clipboard:
        ensure_dependencies(packages=["PIL"])
        from PIL import ImageGrab
        grabbed = ImageGrab.grabclipboard()
        if grabbed is None:
            raise RuntimeError("No image found in your clipboard! Take a screenshot (Win+Shift+S) first.")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        grabbed.save(tmp_path)
        try:
            extracted = extract_text_from_image(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        if input_path is None:
            raise ValueError("Provide an image/PDF file path or pass --clip to read from clipboard.")
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")
        if input_path.suffix.lower() == ".pdf":
            ensure_dependencies(packages=["pypdf"])
            from pypdf import PdfReader
            reader = PdfReader(str(input_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            extracted = "\n\n".join(pages).strip()
        else:
            extracted = extract_text_from_image(input_path)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(extracted, encoding="utf-8")
        print(f"Saved extracted text to {output_path}")
    else:
        print(extracted if extracted else "[No text detected]")

    if copy_result and extracted:
        copy_to_clipboard(extracted)
    return extracted
