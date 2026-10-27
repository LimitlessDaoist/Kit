"""
FFmpeg Media Converter & Compressor (`kit media <input> -o <output>`).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    start: Optional[str] = None,
    end: Optional[str] = None,
    crf: int = 23,
) -> List[str]:
    """Builds the ffmpeg command line for format conversion, trimming, or GIF creation."""
    cmd = ["ffmpeg", "-y"]
    if start:
        cmd += ["-ss", start]
    if end:
        cmd += ["-to", end]
    cmd += ["-i", str(input_path)]

    ext = output_path.suffix.lower()
    if ext == ".gif":
        cmd += ["-vf", "fps=12,scale=640:-1:flags=lanczos"]
    elif ext in {".mp3", ".m4a", ".wav", ".flac"}:
        cmd += ["-vn"]
    elif ext in {".mp4", ".mkv", ".mov"}:
        cmd += ["-c:v", "libx264", "-crf", str(crf), "-preset", "fast", "-c:a", "aac"]

    cmd.append(str(output_path))
    return cmd


def convert_media(
    input_path: Path,
    output_path: Path,
    start: Optional[str] = None,
    end: Optional[str] = None,
    crf: int = 23,
) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("`ffmpeg` binary not found in PATH.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_command(input_path, output_path, start=start, end=end, crf=crf)
    subprocess.run(cmd, check=True)
    print(f"✓ Media saved to {output_path}")
    return output_path
