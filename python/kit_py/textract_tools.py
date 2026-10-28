from __future__ import annotations
import subprocess, tempfile
from pathlib import Path
from typing import Optional
from kit_py.auto_bootstrap import ensure_dependencies

MAX_IMAGE_PIXELS = 64_000_000

def copy_to_clipboard(text: str) -> None:
    try:
        subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
        print("Copied extracted text to clipboard!")
    except Exception:
        pass

def extract_text_from_image(image_path: Path) -> str:
    ensure_dependencies(packages=["PIL", "rapidocr_onnxruntime"])
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    with Image.open(image_path) as img:
        img.verify()
    engine = RapidOCR()
    result, _ = engine(str(image_path.resolve()))
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
        from PIL import Image, ImageGrab
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        grabbed = ImageGrab.grabclipboard()
        if grabbed is None:
            raise RuntimeError("No image found in your clipboard! Take a screenshot (Win+Shift+S) or copy an image file first.")
        if isinstance(grabbed, list):
            first_file = Path(grabbed[0])
            if not first_file.exists():
                raise RuntimeError("Clipboard file path does not exist.")
            extracted = extract_text_from_image(first_file)
        else:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                grabbed.save(tmp_path)
                extracted = extract_text_from_image(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
    else:
        if input_path is None:
            raise ValueError("Provide an image/PDF file path or pass --clip to read from clipboard.")
        resolved_in = input_path.resolve()
        if not resolved_in.exists():
            raise FileNotFoundError(f"File not found: {resolved_in}")
        if resolved_in.suffix.lower() == ".pdf":
            ensure_dependencies(packages=["pypdf"])
            from pypdf import PdfReader
            reader = PdfReader(str(resolved_in))
            pages = [page.extract_text() or "" for page in reader.pages]
            extracted = "\n\n".join(pages).strip()
        else:
            extracted = extract_text_from_image(resolved_in)

    if output_path:
        resolved_out = output_path.resolve()
        resolved_out.parent.mkdir(parents=True, exist_ok=True)
        resolved_out.write_text(extracted, encoding="utf-8")
        print(f"Saved extracted text to {resolved_out}")
    else:
        print(extracted if extracted else "[No text detected]")
    if copy_result and extracted:
        copy_to_clipboard(extracted)
    return extracted
