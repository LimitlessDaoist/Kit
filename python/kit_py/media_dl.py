from __future__ import annotations
import ipaddress, os, re, shutil, subprocess, urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional
from kit_py.auto_bootstrap import ensure_dependencies

DEFAULT_DL_DIR = Path("D:/kit/downloads") if os.name == "nt" else Path("./downloads")
CLIP_REGEX = re.compile(r"^\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?-\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?$")
ALLOWED_AUDIO_FORMATS = {"mp3", "m4a", "flac", "wav", "opus"}

def validate_media_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(f"Unsupported or unsafe URL scheme '{parsed.scheme}'. Only http:// and https:// are allowed.")
    if not parsed.hostname:
        raise ValueError("Invalid URL: missing hostname.")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or host.endswith(".local"):
        raise ValueError("Security policy: loopback and local network URLs are not allowed.")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Security policy: private or reserved IP addresses are not allowed.")
    except ValueError as exc:
        if "Security policy" in str(exc):
            raise
    return url.strip()

def validate_clip_range(clip: str) -> tuple[str, str]:
    clean = clip.strip()
    if not CLIP_REGEX.match(clean):
        raise ValueError(f"Invalid --clip format '{clip}'. Expected HH:MM:SS-HH:MM:SS or MM:SS-MM:SS.")
    start, end = clean.split("-", 1)
    return start.strip(), end.strip()

def get_ffmpeg_path() -> Optional[str]:
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

def build_yt_dlp_options(
    output_dir: Path = DEFAULT_DL_DIR,
    quality: str = "1080",
    audio_only: bool = False,
    audio_format: str = "mp3",
    clip: Optional[str] = None,
    subs: bool = False,
    info_only: bool = False,
) -> Dict[str, Any]:
    audio_fmt = audio_format.lower().strip()
    if audio_fmt not in ALLOWED_AUDIO_FORMATS:
        raise ValueError(f"Unsupported audio format '{audio_format}'.")
    q_clean = quality.lower().strip()
    if q_clean != "best" and not q_clean.isdigit():
        raise ValueError(f"Invalid quality '{quality}'. Use 'best' or a number like 1080, 720, 480.")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(title).100s [%(id)s].%(ext)s")
    ffmpeg_exe = get_ffmpeg_path()

    if audio_only:
        fmt = "bestaudio/best"
    elif q_clean == "best":
        fmt = "bestvideo+bestaudio/best"
    else:
        fmt = f"bestvideo[height<={q_clean}]+bestaudio/best[height<={q_clean}]/best"

    opts: Dict[str, Any] = {
        "format": fmt,
        "outtmpl": outtmpl,
        "restrictfilenames": True,
        "windowsfilenames": True,
        "noplaylist": True,
        "quiet": info_only,
        "writesubtitles": subs,
        "writeautomaticsub": subs,
    }
    if ffmpeg_exe:
        opts["ffmpeg_location"] = ffmpeg_exe
        if not audio_only:
            opts["merge_output_format"] = "mp4"
    if audio_only:
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": audio_fmt, "preferredquality": "192"}]
    if clip:
        start, end = validate_clip_range(clip)
        opts["external_downloader_args"] = {"ffmpeg_i": ["-ss", start, "-to", end]}
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
    open_folder: bool = True,
) -> Dict[str, Any]:
    safe_url = validate_media_url(url)
    ensure_dependencies(packages=["yt_dlp", "imageio_ffmpeg"])
    if str(output_dir) in (".", "./downloads", "downloads") and os.name == "nt":
        output_dir = DEFAULT_DL_DIR
    opts = build_yt_dlp_options(output_dir, quality, audio_only, audio_format, clip, subs, info_only)
    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(safe_url, download=not info_only)
        resolved_dir = str(output_dir.resolve())
        print(f"\nSaved media to: {resolved_dir}")
        if os.name == "nt" and not info_only and open_folder:
            subprocess.Popen(["explorer", resolved_dir])
        return {"id": info.get("id"), "title": info.get("title"), "output_dir": resolved_dir}
