from __future__ import annotations
import base64, hashlib, hmac, importlib.util, json, os, shutil, subprocess, sys, uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
from kit_py.auto_bootstrap import get_ffmpeg_path

def run_hash(files: List[Path], algo: str = "sha256", check: Optional[str] = None) -> Dict[str, str]:
    results: Dict[str, str] = {}
    algo_norm = algo.lower()
    for path in files:
        if algo_norm == "blake3":
            h = hashlib.blake2b(digest_size=32)
        elif algo_norm == "sha512":
            h = hashlib.sha512()
        elif algo_norm == "md5":
            h = hashlib.md5()
        else:
            h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        digest = h.hexdigest()
        results[str(path)] = digest
        print(f"{digest}  {path}")
        if check:
            if hmac.compare_digest(digest.lower(), check.strip().lower()):
                print(f"Checksum verified for {path}")
            else:
                raise ValueError(f"Checksum mismatch for {path}: expected {check}, got {digest}")
    return results

def run_dedup(directory: Path, min_size: int = 1024, as_json: bool = False) -> List[Dict]:
    by_size: Dict[int, List[Path]] = defaultdict(list)
    for root, _, filenames in os.walk(directory):
        for fname in filenames:
            fpath = Path(root) / fname
            if fpath.is_symlink():
                continue
            try:
                sz = fpath.stat().st_size
                if sz >= min_size:
                    by_size[sz].append(fpath)
            except OSError:
                continue
    groups = []
    for sz, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash: Dict[str, List[str]] = defaultdict(list)
        for p in paths:
            h = hashlib.blake2b(digest_size=32)
            try:
                with open(p, "rb") as f:
                    while chunk := f.read(65536):
                        h.update(chunk)
                by_hash[h.hexdigest()].append(str(p))
            except OSError:
                continue
        for digest, dup_files in by_hash.items():
            if len(dup_files) > 1:
                groups.append({"hash": digest, "size_bytes": sz, "files": dup_files})
    if as_json:
        print(json.dumps(groups, indent=2))
    elif not groups:
        print(f"No duplicate files found (min_size = {min_size} bytes).")
    else:
        print(f"Found {len(groups)} duplicate group(s):")
        for g in groups:
            print(f"\n* Hash {g['hash'][:16]} ({g['size_bytes']} bytes each):")
            for f in g["files"]:
                print(f"    - {f}")
    return groups

def run_encode(mode: str, text: Optional[str] = None) -> str:
    if mode == "uuid":
        out = str(uuid.uuid4())
        print(out)
        return out
    if text is None:
        raise ValueError(f"Input text is required for mode '{mode}'")
    if mode == "base64-enc":
        out = base64.b64encode(text.encode("utf-8")).decode("ascii")
    elif mode == "base64-dec":
        out = base64.b64decode(text.strip()).decode("utf-8", errors="replace")
    elif mode == "hex-enc":
        out = text.encode("utf-8").hex()
    elif mode == "hex-dec":
        out = bytes.fromhex(text.strip()).decode("utf-8", errors="replace")
    elif mode == "jwt-decode":
        parts = text.strip().split(".")
        if len(parts) < 2:
            raise ValueError("Invalid JWT token format")
        pad = lambda s: s + "=" * (-len(s) % 4)
        hdr = base64.urlsafe_b64decode(pad(parts[0])).decode("utf-8", errors="replace")
        pay = base64.urlsafe_b64decode(pad(parts[1])).decode("utf-8", errors="replace")
        out = f"Header:  {hdr}\nPayload: {pay}"
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    print(out)
    return out

def run_json(input_src: str = "-", minify: bool = False, query: Optional[str] = None) -> str:
    raw = sys.stdin.read() if input_src == "-" else Path(input_src).read_text(encoding="utf-8")
    data = json.loads(raw)
    if query:
        for key in query.split("."):
            if not key:
                continue
            data = data[int(key)] if isinstance(data, list) else data[key]
    out = json.dumps(data, separators=(",", ":")) if minify else json.dumps(data, indent=2)
    print(out)
    return out

def run_doctor() -> Dict[str, bool]:
    print("Kit Environment Doctor (v0.5.0)")
    print("===============================")
    status: Dict[str, bool] = {}
    py_cmd = "python" if os.name == "nt" else "python3"
    for label, cmd in [
        ("Python 3", [py_cmd, "--version"]),
        ("Git", ["git", "--version"]),
        ("Rust / Cargo", ["cargo", "--version"]),
    ]:
        bin_path = shutil.which(cmd[0])
        if bin_path:
            res = subprocess.run(cmd, capture_output=True, text=True)
            first = (res.stdout or res.stderr).splitlines()[0] if (res.stdout or res.stderr) else "installed"
            print(f"  [OK] {label:<18} {first}")
            status[label] = True
        else:
            print(f"  [--] {label:<18} optional (not installed)")
            status[label] = False

    ffmpeg_bin = get_ffmpeg_path()
    if ffmpeg_bin:
        print(f"  [OK] {'FFmpeg Engine':<18} {ffmpeg_bin}")
        status["FFmpeg"] = True
    else:
        print(f"  [--] {'FFmpeg Engine':<18} not found (run `kit setup`)")
        status["FFmpeg"] = False

    for label, mod_name in [
        ("yt-dlp", "yt_dlp"),
        ("Pillow (Images)", "PIL"),
        ("pypdf (PDFs)", "pypdf"),
        ("AES-256 Crypto", "cryptography"),
        ("RapidOCR", "rapidocr_onnxruntime"),
    ]:
        found = importlib.util.find_spec(mod_name) is not None
        mark = "[OK]" if found else "[--]"
        state_str = "ready" if found else "auto-installs on first use"
        print(f"  {mark} {label:<18} {state_str}")
        status[label] = found
    return status
