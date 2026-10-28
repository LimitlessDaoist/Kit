from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional
from kit_py.auto_bootstrap import ensure_dependencies

MAX_IMAGE_PIXELS = 64_000_000

def inspect_or_strip_meta(
    input_path: Path,
    strip: bool = False,
    output_path: Optional[Path] = None,
    as_json: bool = False,
) -> Dict[str, Any]:
    resolved = input_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    ext = resolved.suffix.lower()
    metadata: Dict[str, str] = {}
    cleaned_path: Optional[Path] = None

    if ext in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}:
        ensure_dependencies(packages=["PIL"])
        from PIL import ExifTags, Image
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with Image.open(resolved) as img:
            metadata["Format"] = str(img.format)
            metadata["Mode"] = str(img.mode)
            metadata["Dimensions"] = f"{img.size[0]}x{img.size[1]}"
            exif_data = img.getexif()
            if exif_data:
                for tag_id, val in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
                    metadata[str(tag_name)] = str(val)[:200]
            for k, v in (img.info or {}).items():
                if k not in {"exif", "icc_profile"} and isinstance(v, (str, int, float)):
                    metadata[f"Info.{k}"] = str(v)[:200]
            if strip:
                cleaned_path = (output_path or resolved.with_name(f"{resolved.stem}_clean{ext}")).resolve()
                clean_img = Image.frombytes(img.mode, img.size, img.tobytes())
                cleaned_path.parent.mkdir(parents=True, exist_ok=True)
                clean_img.save(cleaned_path)
    elif ext == ".pdf":
        ensure_dependencies(packages=["pypdf"])
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(str(resolved))
        metadata["Pages"] = str(len(reader.pages))
        if reader.metadata:
            for k, v in reader.metadata.items():
                if v:
                    metadata[str(k).lstrip("/")] = str(v)[:200]
        if strip:
            cleaned_path = (output_path or resolved.with_name(f"{resolved.stem}_clean.pdf")).resolve()
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata({})
            cleaned_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cleaned_path, "wb") as f:
                writer.write(f)
    else:
        metadata["File"] = resolved.name
        metadata["SizeBytes"] = str(resolved.stat().st_size)

    result: Dict[str, Any] = {
        "file": str(resolved),
        "metadata": metadata,
        "stripped_output": str(cleaned_path) if cleaned_path else None,
    }
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Metadata for {resolved.name}:")
        for k, v in metadata.items():
            print(f"  {k:<22}: {v}")
        if cleaned_path:
            print(f"\nStripped all metadata -> {cleaned_path}")
    return result

