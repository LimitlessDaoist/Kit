from __future__ import annotations
import collections, hashlib, json, math, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

DANGEROUS_EXTS = {".exe", ".scr", ".pif", ".vbs", ".vbe", ".js", ".jse", ".hta", ".cmd", ".bat", ".ps1", ".iso"}
COMMON_DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".png", ".txt", ".mp4"}
SYSTEM_EXE_NAMES = {"svchost.exe", "lsass.exe", "csrss.exe", "smss.exe", "services.exe", "explorer.exe"}

SCRIPT_THREAT_PATTERNS = [
    (re.compile(r"(?:System\.)?Net\.WebClient.*Download(File|String)", re.I), "PowerShell Download Cradle (remote dropper)"),
    (re.compile(r"Invoke-Expression|\bIEX\b", re.I), "Dynamic Code Execution (IEX cradle)"),
    (re.compile(r"-e(?:nc(?:odedcommand)?)?\s+[A-Za-z0-9+/=]{20,}", re.I), "Base64 Obfuscated Command Execution"),
    (re.compile(r"amsiInitFailed|AmsiScanBuffer", re.I), "AMSI Antivirus Bypass Pattern"),
    (re.compile(r"vssadmin.*delete\s+shadows|wmic.*shadowcopy\s+delete", re.I), "Ransomware Shadow Copy Deletion"),
    (re.compile(r"stratum\+tcp://|xmr-pool|cryptonight|xmrig", re.I), "Cryptocurrency Mining Pool / Protocol Indicator"),
    (re.compile(r"FromBase64String\s*\(", re.I), "Base64 Memory Payload Reflection"),
    (re.compile(r"CreateRemoteThread|VirtualAllocEx|WriteProcessMemory", re.I), "Process Injection API Signatures"),
]

def calculate_entropy(data: bytes) -> float:
    if not data: return 0.0
    entropy = 0.0
    counts = collections.Counter(data)
    length = len(data)
    for count in counts.values():
        p_x = count / length
        entropy -= p_x * math.log2(p_x)
    return round(entropy, 2)

def check_virustotal_hash(sha256_hash: str, api_key: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://www.virustotal.com/api/v3/files/{sha256_hash}"
        req = urllib.request.Request(url, headers={"x-apikey": api_key, "User-Agent": "KitScanner/0.6"})
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

def scan_file(file_path: Path, check_vt: bool = False, vt_key: Optional[str] = None) -> Dict[str, Any]:
    resolved = file_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    name = resolved.name.lower()
    size = resolved.stat().st_size
    findings: List[str] = []
    threat_score = 0

    parts = name.split(".")
    if len(parts) >= 3:
        penultimate = f".{parts[-2]}"
        final_ext = f".{parts[-1]}"
        if penultimate in COMMON_DOC_EXTS and final_ext in DANGEROUS_EXTS:
            findings.append(f"Deceptive double extension '{penultimate}{final_ext}' disguising an executable as a document.")
            threat_score += 3

    if name in SYSTEM_EXE_NAMES and "windows\\system32" not in str(resolved).lower():
        findings.append(f"Disguised system executable name '{resolved.name}' running outside System32.")
        threat_score += 2

    h = hashlib.sha256()
    sample_bytes = bytearray()
    with open(resolved, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
            if len(sample_bytes) < 1_000_000:
                sample_bytes.extend(chunk[: 1_000_000 - len(sample_bytes)])
    sha256_hex = h.hexdigest()

    ext = resolved.suffix.lower()
    if ext not in {".zip", ".gz", ".7z", ".rar", ".png", ".jpg", ".mp4", ".mp3"} and len(sample_bytes) >= 1024:
        entropy = calculate_entropy(bytes(sample_bytes))
        if entropy >= 7.3:
            findings.append(f"High Shannon entropy ({entropy}/8.0) indicates heavy encryption or UPX/custom packing.")
            threat_score += 1
    else:
        entropy = 0.0

    if ext in {".ps1", ".bat", ".cmd", ".vbs", ".js", ".hta", ".sh", ".json", ".txt"} or size < 2_000_000:
        try:
            text_sample = sample_bytes.decode("utf-8", errors="ignore")
            for pattern, desc in SCRIPT_THREAT_PATTERNS:
                if pattern.search(text_sample):
                    findings.append(desc)
                    threat_score += 3 if ("Cradle" in desc or "Ransomware" in desc or "Injection" in desc) else 2
        except Exception:
            pass

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
        "status": status,
        "threat_score": threat_score,
        "findings": findings,
        "virustotal": vt_stats,
    }

def scan_target(target_path: Path, check_vt: bool = False, vt_key: Optional[str] = None, as_json: bool = False) -> Dict[str, Any]:
    resolved = target_path.resolve()
    if not resolved.exists(): raise FileNotFoundError(f"Target not found: {resolved}")
    results: List[Dict[str, Any]] = []
    if resolved.is_file():
        results.append(scan_file(resolved, check_vt=check_vt, vt_key=vt_key))
    else:
        file_list: List[Path] = []
        for root, _, files in os.walk(resolved):
            for f in files: file_list.append(Path(root) / f)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(scan_file, fp, check_vt, vt_key) for fp in file_list]
            for fut in futures:
                try: results.append(fut.result())
                except Exception: continue

    clean_count = sum(1 for r in results if r["status"] == "CLEAN")
    suspicious_count = sum(1 for r in results if r["status"] == "SUSPICIOUS")
    malicious_count = sum(1 for r in results if r["status"] == "MALICIOUS")
    summary = {
        "target": str(resolved),
        "total_scanned": len(results),
        "clean": clean_count,
        "suspicious": suspicious_count,
        "malicious": malicious_count,
        "results": results,
    }
    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\nKit Threat Scanner Report: {resolved.name}")
        print("=========================================")
        print(f"Scanned: {len(results)} file(s) | Clean: {clean_count} | Suspicious: {suspicious_count} | Malicious: {malicious_count}\n")
        flagged = [r for r in results if r["status"] != "CLEAN"]
        if not flagged:
            print("All scanned files verified clean. No suspicious heuristics detected.")
        else:
            for item in flagged:
                print(f"  [{item['status']:<10}] {item['file']}")
                for f in item["findings"]: print(f"    - {f}")
                print(f"    SHA-256: {item['sha256']}\n")
    return summary
