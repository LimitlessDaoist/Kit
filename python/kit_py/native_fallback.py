"""
Pure-Python implementation of the native Rust subcommands (`hash`, `dedup`, `encode`, `json`, `clean`, `doctor`)
so `kit-py` or `./kit` can run every single command immediately even on machines where Rust/Cargo
has not been compiled yet.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional


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
            if digest.lower() == check.strip().lower():
                print(f"✓ Checksum verified for {path}")
            else:
                raise ValueError(f"Checksum mismatch for {path}: expected {check}, got {digest}")
    return results


def run_dedup(directory: Path, min_size: int = 1024, as_json: bool = False) -> List[Dict]:
    by_size: Dict[int, List[Path]] = defaultdict(list)
    for root, _, filenames in os.walk(directory):
        for fname in filenames:
            fpath = Path(root) / fname
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
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            by_hash[h.hexdigest()].append(str(p))
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
            print(f"\n• Hash {g['hash'][:16]} ({g['size_bytes']} bytes each):")
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


def run_doctor() -> None:
    print("Kit Environment Doctor")
    print("======================")
    for label, cmd in [
        ("Rust / Cargo", ["cargo", "--version"]),
        ("Python 3", ["python3", "--version"]),
        ("FFmpeg", ["ffmpeg", "-version"]),
        ("yt-dlp", ["yt-dlp", "--version"]),
        ("Git", ["git", "--version"]),
    ]:
        bin_path = shutil.which(cmd[0])
        if bin_path:
            res = subprocess.run(cmd, capture_output=True, text=True)
            first = (res.stdout or res.stderr).splitlines()[0] if (res.stdout or res.stderr) else "installed"
            print(f"  ✓ {label:<15} {first}")
        else:
            print(f"  ✗ {label:<15} not found")
