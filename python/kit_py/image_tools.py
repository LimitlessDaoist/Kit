"""
Image Processing Utility (`kit img <input>`).
Powered by Pillow: supports format conversion (WebP/PNG/JPEG/ICO), smart resizing,
quality optimization, and EXIF metadata stripping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
from PIL import Image


def parse_resize(spec: str, current_size: Tuple[int, int]) -> Tuple[int, int]:
    """Parses '1280x720' or single width '1280' (preserving aspect ratio)."""
    w, h = current_size
    if "x" in spec.lower():
        parts = spec.lower().split("x", 1)
        return int(parts[0]), int(parts[1])
    target_w = int(spec)
    target_h = max(1, int(round(h * (target_w / float(w)))))
    return target_w, target_h


def process_image(
    input_path: Path,
    output_path: Optional[Path] = None,
    target_format: Optional[str] = None,
    resize_spec: Optional[str] = None,
    quality: int = 85,
    strip_exif: bool = False,
) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Image not found: {input_path}")

    with Image.open(input_path) as img:
        orig_size = img.size
        work_img = img.copy()

        if resize_spec:
            new_dims = parse_resize(resize_spec, orig_size)
            work_img = work_img.resize(new_dims, Image.Resampling.LANCZOS)

        if strip_exif:
            work_img = Image.frombytes(work_img.mode, work_img.size, work_img.tobytes())

        if output_path is None:
            ext = f".{target_format.lower().lstrip('.')}" if target_format else input_path.suffix
            output_path = input_path.with_name(f"{input_path.stem}_kit{ext}")

        save_ext = (target_format or output_path.suffix.lstrip(".")).lower()
        if save_ext in {"jpg", "jpeg"} and work_img.mode in {"RGBA", "P"}:
            work_img = work_img.convert("RGB")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs = {"optimize": True}
        if save_ext in {"jpg", "jpeg", "webp"}:
            save_kwargs["quality"] = quality

        pil_fmt = "JPEG" if save_ext in {"jpg", "jpeg"} else save_ext.upper()
        work_img.save(output_path, format=pil_fmt, **save_kwargs)

    print(
        f"??? Image processed: {input_path.name} ({orig_size[0]}x{orig_size[1]}) -> "
        f"{output_path} ({work_img.size[0]}x{work_img.size[1]})"
    )
    return output_path

