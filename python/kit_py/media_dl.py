from __future__ import annotations
import json, os, shutil, subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from kit_py.auto_bootstrap import ensure_dependencies

DEFAULT_DL_DIR = Path("D:/kit/downloads")

def build_yt_dlp_options(
    output_dir: Path = DEFAULT_DL_DIR,
    quality: str = "1080",
    audio_only: bool = False,
    audio_format: str = "mp3",
    clip: Optional[str] = None,
    subs: bool = False,
    info_only: bool = False,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(title).120s [%(id)s].%(ext)s")
    has_ffmpeg = shutil.which("ffmpeg") is not None

    if audio_only:
        fmt = "bestaudio/best"
    elif not has_ffmpeg:
        # Single-file MP4 fallback when ffmpeg is not installed
        fmt = "best[ext=mp4]/best" if quality.lower() == "best" else f"best[height<={quality}][ext=mp4]/best[height<={quality}]/best"
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
    if has_ffmpeg and not audio_only:
        opts["merge_output_format"] = "mp4"
    if audio_only and has_ffmpeg:
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": audio_format, "preferredquality": "192"}]
    if clip and "-" in clip and has_ffmpeg:
        start, end = clip.split("-", 1)
        opts["external_downloader_args"] = {"ffmpeg_i": ["-ss", start.strip(), "-to", end.strip()]}
    return opts

def download_url(
    url: str,
    output_dir: Path = DEFAULT_DL_DIR,
    quality: str = "1080",
    audio_only: bool = False,
    audio_format: str = "mp3",
    clip: Optional[str] = None,
    subs: bool = False,
    info_only: bool = False,
) -> Dict[str, Any]:
    ensure_dependencies(packages=["yt_dlp"])
    if str(output_dir) in (".", "./downloads", "downloads"):
        output_dir = DEFAULT_DL_DIR
    opts = build_yt_dlp_options(output_dir, quality, audio_only, audio_format, clip, subs, info_only)
    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=not info_only)
        resolved_dir = str(output_dir.resolve())
        print(f"\n✓ Saved to folder: {resolved_dir}")
        if os.name == "nt" and not info_only:
            subprocess.Popen(["explorer", resolved_dir])
        return {"title": info.get("title"), "output_dir": resolved_dir}
