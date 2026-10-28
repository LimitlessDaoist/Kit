from __future__ import annotations
import importlib.util, subprocess, sys
from typing import Dict, List

REQUIRED_PACKAGES: Dict[str, str] = {
    "yt_dlp": "yt-dlp>=2024.8.6",
    "imageio_ffmpeg": "imageio-ffmpeg>=0.5.1",
    "PIL": "Pillow>=10.0.0",
    "pypdf": "pypdf>=4.0.0",
    "qrcode": "qrcode>=7.4.2",
    "rapidocr_onnxruntime": "rapidocr-onnxruntime>=1.3.0",
}

def ensure_dependencies(force: bool = False, packages: List[str] | None = None) -> None:
    targets = packages if packages is not None else ["yt_dlp", "imageio_ffmpeg", "PIL", "pypdf", "qrcode"]
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
