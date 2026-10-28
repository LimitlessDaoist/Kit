from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from kit_py.auto_bootstrap import ensure_dependencies
from kit_py.media_dl import download_url, get_ffmpeg_path

ALLOWED_AUDIO_CODECS: Dict[str, List[str]] = {
    "mp3": ["-c:a", "libmp3lame"],
    "flac": ["-c:a", "flac"],
    "m4a": ["-c:a", "aac"],
    "wav": ["-c:a", "pcm_s16le"],
    "opus": ["-c:a", "libopus"],
}
ALLOWED_BITRATES = {"96k", "128k", "192k", "256k", "320k"}

def build_audio_extract_cmd(
    input_path: Path,
    output_path: Path,
    audio_format: str = "mp3",
    bitrate: str = "320k",
    normalize: bool = False,
    ffmpeg_bin: str = "ffmpeg",
) -> List[str]:
    fmt = audio_format.lower().strip().lstrip(".")
    if fmt not in ALLOWED_AUDIO_CODECS:
        raise ValueError(f"Unsupported audio format '{audio_format}'.")
    br = bitrate.lower().strip()
    if br not in ALLOWED_BITRATES:
        raise ValueError(f"Unsupported bitrate '{bitrate}'.")
    cmd = [ffmpeg_bin, "-y", "-i", str(input_path.resolve()), "-vn"]
    if normalize:
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
    cmd += ALLOWED_AUDIO_CODECS[fmt]
    if fmt in {"mp3", "m4a", "opus"}:
        cmd += ["-b:a", br]
    cmd.append(str(output_path.resolve()))
    return cmd

def run_audio_extract(
    source: str,
    output_path: Optional[Path] = None,
    audio_format: str = "mp3",
    bitrate: str = "320k",
    normalize: bool = False,
) -> Dict[str, str]:
    fmt = audio_format.lower().strip().lstrip(".")
    if fmt not in ALLOWED_AUDIO_CODECS:
        raise ValueError(f"Unsupported audio format '{audio_format}'.")
    if source.strip().lower().startswith(("http://", "https://")):
        res = download_url(url=source, audio_only=True, audio_format=fmt)
        return {"source": source, "output": res["output_dir"], "mode": "url"}
    in_path = Path(source).resolve()
    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")
    ensure_dependencies(packages=["imageio_ffmpeg"])
    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg binary not available.")
    if output_path is None:
        suffix_tag = "_norm" if normalize else "_audio"
        output_path = in_path.with_name(f"{in_path.stem}{suffix_tag}.{fmt}")
    else:
        output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_audio_extract_cmd(in_path, output_path, fmt, bitrate, normalize, ffmpeg_bin)
    subprocess.run(cmd, check=True)
    print(f"Extracted audio -> {output_path}")
    return {"source": str(in_path), "output": str(output_path), "mode": "file"}

def build_silence_strip_cmd(
    input_path: Path,
    output_path: Path,
    threshold_db: int = -38,
    min_silence: float = 0.35,
    ffmpeg_bin: str = "ffmpeg",
) -> List[str]:
    safe_db = max(-80, min(-10, int(threshold_db)))
    safe_dur = round(max(0.05, min(10.0, float(min_silence))), 2)
    af_filter = (
        f"silenceremove=start_periods=1:start_silence={safe_dur}:start_threshold={safe_db}dB:"
        f"stop_periods=-1:stop_silence={safe_dur}:stop_threshold={safe_db}dB"
    )
    return [ffmpeg_bin, "-y", "-i", str(input_path.resolve()), "-af", af_filter, str(output_path.resolve())]

def run_silence_strip(
    input_path: Path,
    output_path: Optional[Path] = None,
    threshold_db: int = -38,
    min_silence: float = 0.35,
) -> Path:
    in_resolved = input_path.resolve()
    if not in_resolved.exists():
        raise FileNotFoundError(f"Input file not found: {in_resolved}")
    ensure_dependencies(packages=["imageio_ffmpeg"])
    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg binary not available.")
    if output_path is None:
        output_path = in_resolved.with_name(f"{in_resolved.stem}_nosilence{in_resolved.suffix}")
    else:
        output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_silence_strip_cmd(in_resolved, output_path, threshold_db, min_silence, ffmpeg_bin)
    subprocess.run(cmd, check=True)
    print(f"Trimmed silence -> {output_path}")
    return output_path
