from __future__ import annotations
import importlib.util, os, shutil, subprocess, sys
from pathlib import Path
from typing import Dict, List, Optional

MAX_IMAGE_PIXELS = 64_000_000
DEFAULT_DL_DIR = Path("D:/kit/downloads") if os.name == "nt" else Path("./downloads")

REQUIRED_PACKAGES: Dict[str, str] = {
    "yt_dlp": "yt-dlp>=2024.8.6",
    "imageio_ffmpeg": "imageio-ffmpeg>=0.5.1",
    "PIL": "Pillow>=10.0.0",
    "pypdf": "pypdf>=4.0.0",
    "qrcode": "qrcode>=7.4.2",
    "cryptography": "cryptography>=42.0.0",
    "rapidocr_onnxruntime": "rapidocr-onnxruntime>=1.3.0",
}

def ensure_dependencies(force: bool = False, packages: List[str] | None = None) -> None:
    targets = packages if packages is not None else ["yt_dlp", "imageio_ffmpeg", "PIL", "pypdf", "qrcode", "cryptography"]
    missing_specs: List[str] = []
    for mod_name in targets:
        if mod_name not in REQUIRED_PACKAGES:
            raise ValueError(f"Security policy: package '{mod_name}' is not in the allowed package list.")
        pip_spec = REQUIRED_PACKAGES[mod_name]
        if force or importlib.util.find_spec(mod_name) is None:
            missing_specs.append(pip_spec)
    if not missing_specs:
        return
    print(f"[Kit] Auto-installing missing Python packages ({', '.join(missing_specs)})...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--upgrade"] + missing_specs, check=True)

def get_ffmpeg_path() -> Optional[str]:
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

def copy_to_clipboard(text: str) -> bool:
    try:
        if os.name == "nt":
            subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
            return True
        for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
            if shutil.which(cmd[0]):
                subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                return True
    except Exception:
        pass
    return False
