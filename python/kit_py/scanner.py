from __future__ import annotations

import base64
import collections
import hashlib
import json
import math
import os
import re
import struct
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCANNER_ENGINE_VERSION = "2.0-local-pe"

DANGEROUS_EXTS = {
    ".exe", ".dll", ".sys", ".scr", ".pif", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".hta", ".cmd", ".bat", ".ps1", ".msi", ".cpl", ".iso"
}
COMMON_DOC_EXTS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".txt", ".csv", ".mp3", ".mp4", ".wav"
}
SCRIPT_OR_TEXT_EXTS = {
    ".ps1", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse",
    ".wsf", ".wsh", ".hta", ".sh", ".py", ".json", ".txt", ".xml", ".reg"
}
SYSTEM_EXE_NAMES = {
    "svchost.exe", "lsass.exe", "csrss.exe", "smss.exe",
    "services.exe", "wininit.exe", "winlogon.exe", "dwm.exe", "taskhostw.exe"
}

SKIP_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules",
    ".venv", "venv", "env", ".pytest_cache", ".idea", ".vscode",
    "target", "dist", "build", ".eggs", ".mypy_cache", ".tox", ".next"
}

ARCHIVE_OR_COMPRESSED_EXTS = {
    ".zip", ".gz", ".7z", ".rar", ".tar", ".bz2", ".xz", ".zst",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".avif",
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav",
    ".pdf", ".docx", ".xlsx", ".pptx", ".woff", ".woff2", ".ttf", ".otf", ".wasm", ".pyc", ".kitenc"
}

PACKER_SECTION_NAMES = {
    "upx0", "upx1", "upx2", ".upx0", ".upx1",
    ".vmp0", ".vmp1", ".vmp2", "vmp0", "vmp1",
    ".themida", "themida", ".enigma1", ".enigma2",
    ".aspack", "aspack", ".petite", ".mpress1", ".mpress2", ".nsp0", ".nsp1"
}

UNICODE_SPOOF_CHARS = {"\u202e", "\u202d", "\u200e", "\u200f", "\u202a", "\u202b", "\u202c"}

_ENCODED_SCRIPT_RULES: List[Tuple[str, bytes, str, int]] = [
    ("ps_cradle", b"KD86U3lzdGVtXC4pP05ldFwuV2ViQ2xpZW50LipEb3dubG9hZCg/OkZpbGV8U3RyaW5nKXxJbnZva2UtV2ViUmVxdWVzdC4qLU91dEZpbGV8U3RhcnQtQml0c1RyYW5zZmVy", "PowerShell Download Cradle (remote dropper)", 3),
    ("ps_exec", b"SW52b2tlLUV4cHJlc3Npb258XGJJRVhcYnxcW1N5c3RlbVwuUmVmbGVjdGlvblwuQXNzZW1ibHlcXTo6TG9hZA==", "PowerShell Dynamic Code Execution Cradle", 3),
    ("b64_cmd", b"LWUoPzpuYyg/Om9kZWRjb21tYW5kKT8pP1xzK1tBLVphLXowLTkrLz1dezIwLH0=", "Base64 Obfuscated Command Execution", 2),
    ("amsi_bypass", b"YW1zaUluaXRGYWlsZWR8QW1zaVNjYW5CdWZmZXJ8RGlzYWJsZVJlYWx0aW1lTW9uaXRvcmluZ3xBZGQtTXBQcmVmZXJlbmNlXHMrLUV4Y2x1c2lvbg==", "Antimalware Scan Interface / Defender Bypass Pattern", 3),
    ("shadow_del", b"dnNzYWRtaW4uKmRlbGV0ZVxzK3NoYWRvd3N8d21pYy4qc2hhZG93Y29weVxzK2RlbGV0ZXxiY2RlZGl0LipyZWNvdmVyeWVuYWJsZWRccytub3x3YmFkbWluXHMrZGVsZXRlXHMrY2F0YWxvZw==", "Ransomware Shadow Copy / Recovery Deletion", 4),
    ("miner_proto", b"c3RyYXR1bVwrKD86dGNwfHNzbCk6Ly98eG1yLXBvb2x8Y3J5cHRvbmlnaHR8eG1yaWd8cmFuZG9teHwtLWRvbmF0ZS1sZXZlbA==", "Mining Protocol / Pool Indicator", 3),
    ("b64_reflect", b"RnJvbUJhc2U2NFN0cmluZ1xzKlwo", "Base64 Memory Payload Reflection", 2),
    ("proc_inject", b"Q3JlYXRlUmVtb3RlVGhyZWFkfFZpcnR1YWxBbGxvY0V4fFdyaXRlUHJvY2Vzc01lbW9yeXxOdFVubWFwVmlld09mU2VjdGlvbnxRdWV1ZVVzZXJBUEM=", "Process Memory Injection Signatures", 3),
    ("lolbin_abuse", b"Y2VydHV0aWxccystdXJsY2FjaGVccystc3BsaXR8bXNodGFccysoPzp2YnNjcmlwdHxqYXZhc2NyaXB0fGh0dHApfHJlZ3N2cjMyXHMrL3NccysvblxzKy91XHMrL2k6fHJ1bmRsbDMyXHMramF2YXNjcmlwdDo=", "Living-Off-The-Land Binary (LOLBin) Dropper Execution", 3),
    ("cred_dump", b"c2VrdXJsc2E6OmxvZ29ucGFzc3dvcmRzfGxzYWR1bXA6OnNhbXxNaW5pRHVtcFdyaXRlRHVtcHxtaW1pa2F0eg==", "Credential Harvesting / LSASS Memory Dump Pattern", 4),
]

SCRIPT_THREAT_PATTERNS = [
    (re.compile(base64.b64decode(enc).decode("utf-8"), re.I), desc)
    for _, enc, desc, _ in _ENCODED_SCRIPT_RULES
]

_MASTER_RULE_MAP: Dict[str, Tuple[str, int]] = {}
_master_branches: List[str] = []
for _rid, _enc, _desc, _score in _ENCODED_SCRIPT_RULES:
    _pat_str = base64.b64decode(_enc).decode("utf-8")
    _MASTER_RULE_MAP[_rid] = (_desc, _score)
    _master_branches.append(f"(?P<{_rid}>{_pat_str})")
MASTER_THREAT_REGEX = re.compile("|".join(_master_branches), re.I)

_ENCODED_API_CLUSTERS: List[Tuple[str, int, int, List[str]]] = [
    (
        "Process Hollowing / Remote Memory Injection API Cluster",
        3,
        2,
        [
            "VmlydHVhbEFsbG9jRXg=",
            "V3JpdGVQcm9jZXNzTWVtb3J5",
            "Q3JlYXRlUmVtb3RlVGhyZWFk",
            "TnRVbm1hcFZpZXdPZlNlY3Rpb24=",
            "UXVldWVVc2VyQVBD",
            "U2V0VGhyZWFkQ29udGV4dA==",
        ],
    ),
    (
        "Keylogging & Input Espionage API Cluster",
        2,
        2,
        [
            "U2V0V2luZG93c0hvb2tFeEE=",
            "U2V0V2luZG93c0hvb2tFeFc=",
            "R2V0QXN5bmNLZXlTdGF0ZQ==",
            "R2V0Rm9yZWdyb3VuZFdpbmRvdw==",
        ],
    ),
    (
        "Credential / LSASS Vault Extraction API Cluster",
        3,
        1,
        [
            "TWluaUR1bXBXcml0ZUR1bXA=",
            "Q3J5cHRVbnByb3RlY3REYXRh",
            "THNhRW51bWVyYXRlTG9nb25TZXNzaW9ucw==",
            "U2FtSUNvbm5lY3Q=",
        ],
    ),
]

DECODED_API_CLUSTERS: List[Tuple[str, int, int, List[bytes]]] = [
    (desc, score, min_hits, [base64.b64decode(b) for b in b64_list])
    for desc, score, min_hits, b64_list in _ENCODED_API_CLUSTERS
]


def calculate_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    length = len(data)
    if length > 65536:
        third = length // 3
        two_thirds = (length * 2) // 3
        sample = (
            data[:16384]
            + data[third : third + 16384]
            + data[two_thirds : two_thirds + 16384]
            + data[-16384:]
        )
        length = len(sample)
        counts = collections.Counter(sample)
    else:
        counts = collections.Counter(data)

    inv_len = 1.0 / length
    log2 = math.log2
    entropy = -sum((c * inv_len) * log2(c * inv_len) for c in counts.values())
    return round(entropy, 2)


def analyze_pe_binary(header_and_sample: bytes, file_size: int) -> Tuple[List[str], int, Optional[Dict[str, Any]]]:
    findings: List[str] = []
    score = 0

    if len(header_and_sample) < 0x100 or header_and_sample[:2] != b"MZ":
        return findings, score, None

    try:
        e_lfanew = struct.unpack_from("<I", header_and_sample, 0x3C)[0]
        if e_lfanew < 0x40 or e_lfanew + 24 > len(header_and_sample):
            return findings, score, None

        if header_and_sample[e_lfanew : e_lfanew + 4] != b"PE\x00\x00":
            return findings, score, None

        machine, num_sections, timestamp, _, _, opt_hdr_size, characteristics = struct.unpack_from(
            "<HHIIIHH", header_and_sample, e_lfanew + 4
        )
        arch = {0x8664: "x64", 0x014C: "x86", 0xAA64: "ARM64"}.get(machine, f"0x{machine:04x}")

        sec_table_offset = e_lfanew + 24 + opt_hdr_size
        rwx_sections: List[str] = []
        packer_sections: List[str] = []
        high_entropy_sections: List[str] = []
        inflated_sections: List[str] = []
        max_raw_end = 0

        for i in range(min(num_sections, 48)):
            sec_off = sec_table_offset + (i * 40)
            if sec_off + 40 > len(header_and_sample):
                break

            raw_name, virt_size, virt_addr, raw_size, raw_ptr, _, _, _, _, sec_chars = struct.unpack_from(
                "<8sIIIIIIHHI", header_and_sample, sec_off
            )
            sec_name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip() or f"sec_{i}"
            sec_name_lower = sec_name.lower()

            if raw_ptr > 0 and raw_size > 0:
                max_raw_end = max(max_raw_end, raw_ptr + raw_size)

            is_exec = bool(sec_chars & 0x20000000)
            is_write = bool(sec_chars & 0x80000000)
            if is_exec and is_write:
                rwx_sections.append(sec_name)

            if sec_name_lower in PACKER_SECTION_NAMES:
                packer_sections.append(sec_name)

            if is_exec and virt_size > 65536 and (raw_size == 0 or virt_size > raw_size * 5):
                inflated_sections.append(f"{sec_name} (Virt:{virt_size // 1024}KB vs Raw:{raw_size // 1024}KB)")

            if raw_size >= 2048 and raw_ptr + min(raw_size, 65536) <= len(header_and_sample):
                sec_slice = header_and_sample[raw_ptr : raw_ptr + min(raw_size, 65536)]
                sec_ent = calculate_entropy(sec_slice)
                if sec_ent >= 7.65:
                    high_entropy_sections.append(f"{sec_name} ({sec_ent}/8.0)")

        if rwx_sections:
            findings.append(
                f"PE Anomaly: Write+Execute (RWX) self-modifying code section(s) [{', '.join(rwx_sections)}] typical of shellcode stubs or process hollowing."
            )
            score += 2

        if packer_sections:
            findings.append(
                f"PE Packer Detected: Known binary packer/crypter section(s) [{', '.join(packer_sections)}]."
            )
            score += 2

        if inflated_sections:
            findings.append(
                f"PE Unpacking Stub: Executable section virtual size vastly exceeds disk size [{', '.join(inflated_sections)}]."
            )
            score += 2

        if high_entropy_sections:
            findings.append(
                f"PE Encrypted Section(s): High Shannon entropy in [{', '.join(high_entropy_sections)}] indicates packed/encrypted payload."
            )
            score += 1

        matched_clusters: List[str] = []
        for cluster_desc, cluster_score, min_hits, api_bytes_list in DECODED_API_CLUSTERS:
            hits = [api.decode("ascii") for api in api_bytes_list if api in header_and_sample]
            if len(hits) >= min_hits:
                findings.append(f"PE Capability [{cluster_desc}]: imports {', '.join(hits[:4])}.")
                score += cluster_score
                matched_clusters.append(cluster_desc)

        pe_meta = {
            "arch": arch,
            "sections": num_sections,
            "is_dll": bool(characteristics & 0x2000),
            "rwx_sections": rwx_sections,
            "packer_sections": packer_sections,
            "max_section_end": max_raw_end,
            "api_clusters": matched_clusters,
        }
        return findings, score, pe_meta
    except Exception:
        return findings, score, None


def inspect_ntfs_zone_identifier(resolved_path: Path) -> Optional[str]:
    if os.name != "nt":
        return None
    try:
        ads_path = f"{resolved_path}:Zone.Identifier"
        with open(ads_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(2048)
        if "ZoneId=3" in content or "ZoneId=4" in content:
            host_match = re.search(r"HostUrl=(.+)", content)
            origin = host_match.group(1).strip() if host_match else "Internet Zone (ZoneId=3)"
            return origin
    except Exception:
        pass
    return None


def check_virustotal_hash(sha256_hash: str, api_key: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://www.virustotal.com/api/v3/files/{sha256_hash}"
        req = urllib.request.Request(url, headers={"x-apikey": api_key, "User-Agent": "KitScanner/2.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            return {
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "undetected": stats.get("undetected", 0),
            }
    except Exception:
        return None


def scan_file(
    file_path: Path | str,
    check_vt: bool = False,
    vt_key: Optional[str] = None,
) -> Dict[str, Any]:
    resolved = Path(file_path).resolve()
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")

    raw_filename = resolved.name
    name = raw_filename.lower()
    stat_info = resolved.stat()
    size = stat_info.st_size
    findings: List[str] = []
    threat_score = 0

    if any(c in raw_filename for c in UNICODE_SPOOF_CHARS):
        findings.append("CRITICAL: Filename contains hidden Unicode Right-to-Left Override (RLO) spoofing characters.")
        threat_score += 4

    parts = name.split(".")
    if len(parts) >= 3:
        penultimate_raw = parts[-2]
        penultimate_clean = f".{penultimate_raw.strip()}"
        final_ext = f".{parts[-1]}"
        if penultimate_clean in COMMON_DOC_EXTS and final_ext in DANGEROUS_EXTS:
            findings.append(f"Deceptive double extension '{penultimate_clean}{final_ext}' disguising an executable as a document.")
            threat_score += 3
        elif len(penultimate_raw) > len(penultimate_raw.rstrip()) + 4 and final_ext in DANGEROUS_EXTS:
            findings.append(f"Whitespace-padded extension obfuscation detected before '{final_ext}'.")
            threat_score += 3

    resolved_lower = str(resolved).lower().replace("/", "\\")
    if name in SYSTEM_EXE_NAMES:
        if "windows\\system32" not in resolved_lower and "windows\\syswow64" not in resolved_lower and "windows\\winsxs" not in resolved_lower:
            findings.append(f"Masquerading system executable '{resolved.name}' located outside Windows System32.")
            threat_score += 3

    h = hashlib.sha256()
    head_sample = bytearray()
    tail_chunk = b""
    HEAD_LIMIT = 524_288

    with open(resolved, "rb") as f:
        while chunk := f.read(131072):
            h.update(chunk)
            if len(head_sample) < HEAD_LIMIT:
                head_sample.extend(chunk[: HEAD_LIMIT - len(head_sample)])
            tail_chunk = chunk[-32768:] if len(chunk) >= 32768 else chunk

    sha256_hex = h.hexdigest()
    sample_bytes = bytes(head_sample)
    ext = resolved.suffix.lower()

    is_pe_binary = sample_bytes.startswith(b"MZ")
    is_elf_binary = sample_bytes.startswith(b"\x7fELF")
    if (is_pe_binary or is_elf_binary) and ext in COMMON_DOC_EXTS:
        bin_type = "Windows PE (MZ)" if is_pe_binary else "Linux ELF"
        findings.append(f"CRITICAL Magic-Byte Mismatch: {bin_type} executable disguised with safe '{ext}' extension.")
        threat_score += 4

    pe_info = None
    if is_pe_binary:
        pe_findings, pe_score, pe_info = analyze_pe_binary(sample_bytes, size)
        findings.extend(pe_findings)
        threat_score += pe_score

    if ext not in ARCHIVE_OR_COMPRESSED_EXTS and size >= 1024:
        combined_sample = sample_bytes + (tail_chunk if size > HEAD_LIMIT else b"")
        entropy = calculate_entropy(combined_sample)
        if entropy >= 7.6 and not (pe_info and pe_info.get("packer_sections")):
            findings.append(f"High Shannon entropy ({entropy}/8.0) indicates heavy encryption or custom crypter packing.")
            threat_score += 1
    else:
        entropy = 0.0

    if ext in SCRIPT_OR_TEXT_EXTS or (size < 2_000_000 and ext not in ARCHIVE_OR_COMPRESSED_EXTS):
        try:
            text_sample = sample_bytes.decode("utf-8", errors="ignore")
            if "\x00" in text_sample[:128]:
                text_sample += "\n" + sample_bytes.decode("utf-16-le", errors="ignore")

            seen_rules = set()
            for match in MASTER_THREAT_REGEX.finditer(text_sample):
                rid = match.lastgroup
                if rid and rid not in seen_rules:
                    seen_rules.add(rid)
                    desc, sc = _MASTER_RULE_MAP[rid]
                    findings.append(desc)
                    threat_score += sc
        except Exception:
            pass

    motw_origin = inspect_ntfs_zone_identifier(resolved)
    if motw_origin and (threat_score > 0 or ext in DANGEROUS_EXTS):
        findings.append(f"NTFS Mark-of-the-Web (Zone.Identifier): Downloaded from {motw_origin}")
        if ext in DANGEROUS_EXTS and threat_score > 0:
            threat_score += 1

    vt_stats = None
    if check_vt:
        effective_key = vt_key or os.environ.get("VIRUSTOTAL_API_KEY")
        if effective_key:
            vt_stats = check_virustotal_hash(sha256_hex, effective_key)
            if vt_stats and vt_stats.get("malicious", 0) > 0:
                findings.append(f"VirusTotal detection: {vt_stats['malicious']} engines flagged this SHA-256 hash.")
                threat_score += max(3, vt_stats["malicious"])

    status = "MALICIOUS" if threat_score >= 3 else ("SUSPICIOUS" if threat_score >= 1 else "CLEAN")
    return {
        "file": str(resolved),
        "name": resolved.name,
        "size_bytes": size,
        "sha256": sha256_hex,
        "entropy": entropy,
        "pe_info": pe_info,
        "status": status,
        "threat_score": threat_score,
        "findings": findings,
        "virustotal": vt_stats,
    }


def _get_cache_path() -> Path:
    base = Path.home() / ".kit_cache"
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base / "scan_cache_v2.json"
    except Exception:
        return Path(os.environ.get("TEMP", "/tmp")) / "kit_scan_cache_v2.json"


def _load_scan_cache() -> Dict[str, Any]:
    cp = _get_cache_path()
    if cp.exists():
        try:
            data = json.loads(cp.read_text(encoding="utf-8"))
            if data.get("version") == SCANNER_ENGINE_VERSION:
                return data.get("entries", {})
        except Exception:
            pass
    return {}


def _save_scan_cache(entries: Dict[str, Any]) -> None:
    cp = _get_cache_path()
    try:
        if len(entries) > 25000:
            keys = list(entries.keys())[-20000:]
            entries = {k: entries[k] for k in keys}
        cp.write_text(
            json.dumps({"version": SCANNER_ENGINE_VERSION, "entries": entries}),
            encoding="utf-8",
        )
    except Exception:
        pass


def scan_target(
    target_path: Path | str,
    check_vt: bool = False,
    vt_key: Optional[str] = None,
    as_json: bool = False,
    use_cache: bool = True,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    resolved = Path(target_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Target not found: {resolved}")

    cache = _load_scan_cache() if (use_cache and not check_vt) else {}
    cache_hits = 0
    results: List[Dict[str, Any]] = []

    if resolved.is_file():
        results.append(scan_file(resolved, check_vt=check_vt, vt_key=vt_key))
    else:
        to_scan: List[Tuple[Path, str]] = []
        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]
            for f in files:
                if f.endswith(".pyc") or f.endswith(".pyo") or f.startswith("."):
                    continue
                fp = Path(root) / f
                try:
                    st = fp.stat()
                    cache_key = f"{fp}|{st.st_mtime_ns}|{st.st_size}"
                    if use_cache and not check_vt and cache_key in cache:
                        results.append(cache[cache_key])
                        cache_hits += 1
                    else:
                        to_scan.append((fp, cache_key))
                except Exception:
                    continue

        if to_scan:
            workers = min(32, (os.cpu_count() or 4) * 2)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                future_map = {
                    pool.submit(scan_file, fp, check_vt, vt_key): cache_key
                    for fp, cache_key in to_scan
                }
                for fut, ckey in future_map.items():
                    try:
                        res = fut.result()
                        results.append(res)
                        if use_cache and not check_vt:
                            cache[ckey] = res
                    except Exception:
                        continue

            if use_cache and not check_vt:
                _save_scan_cache(cache)

    elapsed = max(0.001, time.perf_counter() - t0)
    total_bytes = sum(r.get("size_bytes", 0) for r in results)
    mb_per_sec = round((total_bytes / (1024 * 1024)) / elapsed, 1)

    clean_count = sum(1 for r in results if r["status"] == "CLEAN")
    suspicious_count = sum(1 for r in results if r["status"] == "SUSPICIOUS")
    malicious_count = sum(1 for r in results if r["status"] == "MALICIOUS")

    summary = {
        "engine": SCANNER_ENGINE_VERSION,
        "target": str(resolved),
        "total_scanned": len(results),
        "cached_hits": cache_hits,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_mb_s": mb_per_sec,
        "clean": clean_count,
        "suspicious": suspicious_count,
        "malicious": malicious_count,
        "results": results,
    }

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\nKit Local Threat Engine ({SCANNER_ENGINE_VERSION}): {resolved.name}")
        print("=" * 64)
        print(
            f"Scanned: {len(results)} file(s) ({cache_hits} cached) in {elapsed:.2f}s ({mb_per_sec} MB/s)\n"
            f"Status : Clean: {clean_count} | Suspicious: {suspicious_count} | Malicious: {malicious_count}\n"
        )
        flagged = sorted(
            [r for r in results if r["status"] != "CLEAN"],
            key=lambda x: x.get("threat_score", 0),
            reverse=True,
        )
        if not flagged:
            print("✓ All scanned files verified clean (PE headers, magic bytes, entropy & DFA rules).")
        else:
            for item in flagged:
                score_tag = f"Score:{item.get('threat_score', 0)}"
                print(f"  [{item['status']:<10} | {score_tag:<7}] {item['file']}")
                pe = item.get("pe_info")
                if pe:
                    kind = "DLL" if pe.get("is_dll") else "EXE"
                    print(f"    • PE Binary : {pe.get('arch')} {kind} ({pe.get('sections')} sections)")
                for f in item["findings"]:
                    print(f"    - {f}")
                print(f"    SHA-256: {item['sha256']}\n")
    return summary
