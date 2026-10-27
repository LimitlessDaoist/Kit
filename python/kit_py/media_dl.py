from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_DL_DIR = Path("D:/kit/downloads")

def get_ffmpeg_path() -> Optional[str]:
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

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
    if str(output_dir) in (".", "./downloads", "downloads"):
        output_dir = DEFAULT_DL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_exe = get_ffmpeg_path()
    outtmpl = str(output_dir / "%(title).120s [%(id)s].%(ext)s")

    if audio_only:
        fmt = "bestaudio/best"
    elif not ffmpeg_exe:
        fmt = "b[ext=mp4]/b"
    elif quality.lower() == "best":
        fmt = "bv*+ba/b"
    else:
        fmt = f"bv*[height<={quality}]+ba/b[height<={quality}]/b"

    opts: Dict[str, Any] = {
        "format": fmt,
        "outtmpl": outtmpl,
        "noplaylist": True,
        "writesubtitles": subs,
        "writeautomaticsub": subs,
    }
    if ffmpeg_exe:
        opts["ffmpeg_location"] = ffmpeg_exe
        if not audio_only:
            opts["merge_output_format"] = "mp4"
        else:
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": audio_format, "preferredquality": "192"}]

    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=not info_only)
        resolved_dir = str(output_dir.resolve())
        print(f"\n? Saved video to: {resolved_dir}")
        if os.name == "nt" and not info_only:
            subprocess.Popen(["explorer", resolved_dir])
        return {"title": info.get("title"), "output_dir": resolved_dir}
