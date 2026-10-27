"""
Video & Audio Downloader module for Kit (`kit dl <url>`).
Uses the `yt_dlp` Python API if installed, or falls back to the `yt-dlp` CLI binary.
Supports resolution selection, audio extraction, subtitle downloading, and time clipping.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def build_yt_dlp_options(
    output_dir: Path,
    quality: str = "1080",
    audio_only: bool = False,
    audio_format: str = "mp3",
    clip: Optional[str] = None,
    subs: bool = False,
    info_only: bool = False,
) -> Dict[str, Any]:
    """Constructs deterministic yt-dlp configuration dictionary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(title).120s [%(id)s].%(ext)s")

    if audio_only:
        fmt = "bestaudio/best"
    elif quality.lower() == "best":
        fmt = "bestvideo+bestaudio/best"
    else:
        fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"

    opts: Dict[str, Any] = {
        "format": fmt,
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": info_only,
        "writesubtitles": subs,
        "writeautomaticsub": subs,
    }

    postprocessors = []
    if audio_only:
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        )

    if clip:
        if "-" in clip:
            start, end = clip.split("-", 1)
            opts["external_downloader_args"] = {
                "ffmpeg_i": ["-ss", start.strip(), "-to", end.strip()]
            }

    if postprocessors:
        opts["postprocessors"] = postprocessors

    return opts


def download_url(
    url: str,
    output_dir: Path = Path("./downloads"),
    quality: str = "1080",
    audio_only: bool = False,
    audio_format: str = "mp3",
    clip: Optional[str] = None,
    subs: bool = False,
    info_only: bool = False,
) -> Dict[str, Any]:
    """Downloads media from `url` using yt_dlp Python library or CLI fallback."""
    opts = build_yt_dlp_options(
        output_dir=output_dir,
        quality=quality,
        audio_only=audio_only,
        audio_format=audio_format,
        clip=clip,
        subs=subs,
        info_only=info_only,
    )

    try:
        import yt_dlp  # type: ignore

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=not info_only)
            summary = {
                "id": info.get("id"),
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "webpage_url": info.get("webpage_url", url),
                "output_dir": str(output_dir.resolve()),
            }
            if info_only:
                print(json.dumps(summary, indent=2))
            else:
                print(f"✓ Downloaded: {summary['title']} -> {summary['output_dir']}")
            return summary
    except ImportError:
        yt_bin = shutil.which("yt-dlp")
        if not yt_bin:
            raise RuntimeError(
                "Neither `yt_dlp` Python package nor `yt-dlp` binary was found. "
                "Install with: pip install yt-dlp"
            )
        cmd = [yt_bin, "-f", opts["format"], "-o", opts["outtmpl"], "--no-playlist"]
        if audio_only:
            cmd += ["-x", "--audio-format", audio_format]
        if subs:
            cmd += ["--write-subs", "--write-auto-subs"]
        if clip:
            cmd += ["--download-sections", f"*{clip}"]
        if info_only:
            cmd += ["--dump-json", "--skip-download"]
        cmd.append(url)
        subprocess.run(cmd, check=True)
        return {"url": url, "output_dir": str(output_dir.resolve())}
