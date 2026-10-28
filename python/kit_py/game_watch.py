from __future__ import annotations

import base64
import csv
import datetime
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from kit_py.auto_bootstrap import DEFAULT_DL_DIR
from kit_py.scanner import SYSTEM_EXE_NAMES, scan_file

SUSPICIOUS_PATH_PATTERNS = [
    re.compile(r"appdata[\\/]local[\\/]temp", re.I),
    re.compile(r"appdata[\\/]roaming", re.I),
    re.compile(r"programdata", re.I),
    re.compile(r"users[\\/]public", re.I),
    re.compile(r"windows[\\/]temp", re.I),
    re.compile(r"/tmp/|/var/tmp/|/dev/shm/", re.I),
]

_MINER_SIG = b"eG1yaWd8bWluZXJnYXRlfGNyeXB0b25pZ2h0fHN0cmF0dW1cK3RjcHxldGhtaW5lcnxyYW5kb214fG5hbm9wb29sfDJtaW5lcnM="
MINER_PATTERNS = re.compile(base64.b64decode(_MINER_SIG).decode("ascii"), re.I)

_BINARY_SCAN_CACHE: Dict[str, Dict[str, Any]] = {}


def snapshot_processes_native() -> List[Dict[str, Any]]:
    procs: List[Dict[str, Any]] = []
    try:
        import psutil
        for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                cmd = " ".join(info.get("cmdline") or [])
                mem_mb = round((info.get("memory_info").rss / (1024 * 1024)), 1) if info.get("memory_info") else 0.0
                procs.append({
                    "pid": info["pid"],
                    "name": info.get("name") or "unknown",
                    "exe": info.get("exe") or "",
                    "cmd": cmd,
                    "cpu_percent": info.get("cpu_percent") or 0.0,
                    "mem_mb": mem_mb,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return procs
    except ImportError:
        pass

    if os.name == "nt":
        try:
            res = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True)
            for row in csv.reader(res.stdout.splitlines()):
                if len(row) >= 5:
                    procs.append({
                        "pid": int(row[1]) if row[1].isdigit() else 0,
                        "name": row[0],
                        "exe": "",
                        "cmd": "",
                        "cpu_percent": 0.0,
                        "mem_mb": 0.0,
                    })
        except Exception:
            pass

    return procs


def assess_threat(proc: Dict[str, Any], cpu_threshold: float = 15.0) -> List[str]:
    reasons: List[str] = []
    exe_raw = proc.get("exe") or ""
    exe = exe_raw.lower().replace("/", "\\")
    cmd = (proc.get("cmd") or "").lower()
    name = (proc.get("name") or "").lower()
    cpu = proc.get("cpu_percent", 0.0)

    for pat in SUSPICIOUS_PATH_PATTERNS:
        if pat.search(exe) or pat.search(cmd):
            reasons.append(f"Executing from unprivileged temporary/AppData directory: {exe_raw or cmd}")
            break

    if name in SYSTEM_EXE_NAMES and exe and "windows\\system32" not in exe and "windows\\syswow64" not in exe:
        reasons.append(f"Masquerading system process '{name}' running outside System32 ({exe_raw})")

    if MINER_PATTERNS.search(cmd) or MINER_PATTERNS.search(name):
        reasons.append("Cryptocurrency mining pool/protocol indicators detected in process arguments")

    if cpu >= cpu_threshold and reasons:
        reasons.append(f"Sustained background CPU load ({cpu}%) exceeding threshold ({cpu_threshold}%)")

    if (reasons or cpu >= cpu_threshold * 1.5) and exe_raw and os.path.isfile(exe_raw):
        if exe_raw not in _BINARY_SCAN_CACHE:
            try:
                _BINARY_SCAN_CACHE[exe_raw] = scan_file(Path(exe_raw))
            except Exception:
                _BINARY_SCAN_CACHE[exe_raw] = {}
        scan_res = _BINARY_SCAN_CACHE.get(exe_raw) or {}
        if scan_res.get("status") in {"SUSPICIOUS", "MALICIOUS"}:
            for finding in scan_res.get("findings", [])[:2]:
                reasons.append(f"Binary PE Scan [{scan_res['status']}]: {finding}")

    return reasons


def run_game_watch(
    interval_seconds: float = 2.0,
    duration_seconds: Optional[int] = None,
    cpu_threshold: float = 15.0,
    output_csv: Optional[Path] = None,
    on_snapshot: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    DEFAULT_DL_DIR.mkdir(parents=True, exist_ok=True)
    csv_file = output_csv or (DEFAULT_DL_DIR / f"gamewatch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

    seen_anomalies: List[Dict[str, Any]] = []
    high_cpu_history: Dict[int, Dict[str, Any]] = {}
    start_time = time.time()
    snapshots_taken = 0

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "PID", "Name", "CPU%", "MemMB", "Executable", "ThreatFindings"])

        print("Kit Game Watchdog & Stealth Miner Hunter (v2.0 Local PE + Behavioral Engine)")
        print(f"Sampling every {interval_seconds}s | Flagging background CPU >= {cpu_threshold}%")
        print(f"Session log: {csv_file}")
        print("Press Ctrl+C at any time to finish your gaming session and view the audit summary.\n")

        try:
            while True:
                snapshots_taken += 1
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                procs = snapshot_processes_native()
                current_pids = set()

                for p in procs:
                    pid = p["pid"]
                    current_pids.add(pid)
                    cpu = p.get("cpu_percent", 0.0)

                    if cpu >= cpu_threshold:
                        high_cpu_history[pid] = {
                            "name": p["name"],
                            "exe": p.get("exe") or "",
                            "peak_cpu": max(cpu, high_cpu_history.get(pid, {}).get("peak_cpu", 0.0)),
                            "last_seen": now_str,
                        }

                    findings = assess_threat(p, cpu_threshold=cpu_threshold)
                    if findings:
                        p_copy = dict(p)
                        p_copy["timestamp"] = now_str
                        p_copy["findings"] = findings
                        seen_anomalies.append(p_copy)
                        writer.writerow([now_str, pid, p["name"], cpu, p["mem_mb"], p["exe"], " | ".join(findings)])
                        print(f"[{now_str}] [SUSPICIOUS] PID {pid} ({p['name']}) CPU: {cpu}% | {findings[0]}")

                vanished_pids = [pid for pid in list(high_cpu_history.keys()) if pid not in current_pids]
                for vpid in vanished_pids:
                    info = high_cpu_history.pop(vpid)
                    if info["exe"] and any(pat.search(info["exe"]) for pat in SUSPICIOUS_PATH_PATTERNS):
                        evasion_msg = (
                            f"Evasive termination: Process peaked at {info['peak_cpu']}% CPU and exited abruptly ({info['exe']})"
                        )
                        anomaly = {
                            "timestamp": now_str,
                            "pid": vpid,
                            "name": info["name"],
                            "exe": info["exe"],
                            "cpu_percent": info["peak_cpu"],
                            "mem_mb": 0.0,
                            "findings": [evasion_msg],
                        }
                        seen_anomalies.append(anomaly)
                        writer.writerow([now_str, vpid, info["name"], info["peak_cpu"], 0.0, info["exe"], evasion_msg])
                        print(f"[{now_str}] [EVASIVE]    PID {vpid} ({info['name']}) Peak CPU: {info['peak_cpu']}% | {evasion_msg}")

                if on_snapshot:
                    on_snapshot({"timestamp": now_str, "anomalies": seen_anomalies})

                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break

                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nSession stopped by user.")

    elapsed = round(time.time() - start_time, 1)
    print("\nGame Watchdog Session Summary")
    print("=============================")
    print(f"Elapsed: {elapsed}s | Snapshots: {snapshots_taken} | Anomalies Detected: {len(seen_anomalies)}")
    print(f"Full CSV Log: {csv_file}\n")

    return {
        "elapsed_seconds": elapsed,
        "snapshots": snapshots_taken,
        "anomalies": seen_anomalies,
        "csv_path": str(csv_file),
    }
