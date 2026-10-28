from __future__ import annotations
import csv, datetime, os, re, subprocess, time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from kit_py.auto_bootstrap import DEFAULT_DL_DIR

SUSPICIOUS_PATH_PATTERNS = [
    re.compile(r"appdata[\\/]local[\\/]temp", re.I),
    re.compile(r"appdata[\\/]roaming", re.I),
    re.compile(r"programdata", re.I),
    re.compile(r"/tmp/|/var/tmp/", re.I),
]
MINER_PATTERNS = re.compile(r"xmrig|minergate|cryptonight|stratum\+tcp|ethminer", re.I)

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
                        "exe": "", "cmd": "", "cpu_percent": 0.0,
                        "mem_mb": float(row[4].replace(" K", "").replace(",", "")) / 1024.0 if "K" in row[4] else 0.0,
                    })
        except Exception:
            pass
    return procs

def run_watchdog(
    interval: float = 2.0,
    top_n: int = 5,
    cpu_threshold: float = 15.0,
    duration_secs: Optional[int] = None,
    log_csv: Optional[Path] = None,
    on_sample: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    DEFAULT_DL_DIR.mkdir(parents=True, exist_ok=True)
    session_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = (log_csv or (DEFAULT_DL_DIR / f"gamewatch_{session_ts}.csv")).resolve()

    print("Kit Game Watchdog & Stealth Miner Hunter")
    print("========================================")
    print(f"Sampling every {interval}s | CPU Spike Threshold: {cpu_threshold}%")
    print(f"Log will be saved to: {csv_path}")
    print("Press Ctrl+C to stop recording and generate session audit report.\n")

    history: Dict[int, Dict[str, Any]] = {}
    evasive_alerts: List[Dict[str, Any]] = []
    samples_count = 0
    start_time = time.time()

    csv_file = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow(["Timestamp", "PID", "Name", "CPU_Percent", "Memory_MB", "Executable", "Suspicious_Flags"])

    try:
        try:
            import psutil
            psutil.cpu_percent(None)
        except ImportError:
            pass

        while True:
            time.sleep(interval)
            samples_count += 1
            now_iso = datetime.datetime.now().strftime("%H:%M:%S")
            procs = snapshot_processes_native()
            sorted_procs = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)

            for p in sorted_procs[:top_n]:
                pid = p["pid"]
                flags = []
                exe = p["exe"]
                cmd = p["cmd"]
                for pat in SUSPICIOUS_PATH_PATTERNS:
                    if (exe and pat.search(exe)) or (cmd and pat.search(cmd)):
                        flags.append("UserTempDirectoryExecution")
                        break
                if (exe and MINER_PATTERNS.search(exe)) or (cmd and MINER_PATTERNS.search(cmd)):
                    flags.append("CryptominerSignatureMatch")

                if p["cpu_percent"] >= cpu_threshold and flags:
                    evasive_alerts.append({ "time": now_iso, "pid": pid, "name": p["name"], "cpu": p["cpu_percent"], "exe": exe or cmd, "flags": flags })

                flag_str = ";".join(flags) if flags else "none"
                writer.writerow([now_iso, pid, p["name"], p["cpu_percent"], p["mem_mb"], exe or cmd, flag_str])

                if pid not in history:
                    history[pid] = { "name": p["name"], "exe": exe or cmd, "peak_cpu": p["cpu_percent"], "peak_mem": p["mem_mb"], "samples": 1, "flags": flags }
                else:
                    history[pid]["peak_cpu"] = max(history[pid]["peak_cpu"], p["cpu_percent"])
                    history[pid]["peak_mem"] = max(history[pid]["peak_mem"], p["mem_mb"])
                    history[pid]["samples"] += 1

            csv_file.flush()
            top_line = ", ".join(f"{p['name']} ({p['cpu_percent']}%)" for p in sorted_procs[:3] if p["cpu_percent"] > 0) or "idle"
            print(f"[{now_iso}] Top: {top_line}")
            if on_sample:
                on_sample({ "time": now_iso, "top": sorted_procs[:top_n], "alerts": len(evasive_alerts) })
            if duration_secs and (time.time() - start_time) >= duration_secs:
                break
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")
    finally:
        csv_file.close()

    elapsed_mins = round((time.time() - start_time) / 60.0, 1)
    print("\n==================================================")
    print(f"Session Audit Report ({samples_count} samples over {elapsed_mins} mins)")
    print(f"Session CSV: {csv_path}")
    print("==================================================")
    ranked = sorted(history.values(), key=lambda x: x["peak_cpu"], reverse=True)
    print("\nTop Resource Consumers:")
    for item in ranked[:5]:
        print(f"  * {item['name']:<22} Peak CPU: {item['peak_cpu']:>5.1f}% | Peak RAM: {item['peak_mem']:>6.1f} MB | {item['exe'][:60]}")
    if evasive_alerts:
        print(f"\nWARNING: Detected {len(evasive_alerts)} suspicious or evasive background spike(s):")
        for alert in evasive_alerts[:5]:
            print(f"  [ALERT] {alert['time']} | PID {alert['pid']} ({alert['name']}) spiked {alert['cpu']}% CPU | Flags: {', '.join(alert['flags'])}")
            print(f"          Path: {alert['exe']}")
    else:
        print("\nNo stealth cryptominers or suspicious AppData/Temp background spikes detected.")

    return { "csv_path": str(csv_path), "samples": samples_count, "elapsed_mins": elapsed_mins, "top_consumers": ranked[:5], "alerts": evasive_alerts }
