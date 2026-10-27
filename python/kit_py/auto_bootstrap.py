from __future__ import annotations
import importlib.util, subprocess, sys
from typing import Dict, List

REQUIRED_PACKAGES: Dict[str, str] = {
    "yt_dlp": "yt-dlp>=2024.8.6",
    "PIL": "Pillow>=10.0.0",
    "pypdf": "pypdf>=4.0.0",
    "qrcode": "qrcode>=7.4.2",
}

def ensure_dependencies(force: bool = False, packages: List[str] | None = None) -> None:
    targets = packages if packages is not None else list(REQUIRED_PACKAGES.keys())
    missing_specs: List[str] = []
    for mod_name in targets:
        pip_spec = REQUIRED_PACKAGES.get(mod_name, mod_name)
        if force or importlib.util.find_spec(mod_name) is None:
            missing_specs.append(pip_spec)
    if not missing_specs:
        return
    print(f"[Kit] Auto-installing missing Python packages ({', '.join(missing_specs)})...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade"] + missing_specs, check=True)
