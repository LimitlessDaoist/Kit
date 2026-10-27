from __future__ import annotations
import json, statistics, time, urllib.request
from typing import Any, Dict

CF_DOWN_URL = "https://speed.cloudflare.com/__down?bytes="
CF_UP_URL = "https://speed.cloudflare.com/__up"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KitCLI/0.2"

def measure_ping(samples: int = 5) -> Dict[str, float]:
    rtts = []
    for _ in range(samples):
        req = urllib.request.Request(f"{CF_DOWN_URL}0", headers={"User-Agent": USER_AGENT})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        rtts.append((time.perf_counter() - t0) * 1000.0)
    return {
        "ping_ms": round(min(rtts), 2),
        "jitter_ms": round(statistics.stdev(rtts), 2) if len(rtts) > 1 else 0.0,
    }

def measure_download(size_mb: int = 15) -> float:
    total_bytes = max(1, size_mb) * 1_000_000
    req = urllib.request.Request(f"{CF_DOWN_URL}{total_bytes}", headers={"User-Agent": USER_AGENT})
    received = 0
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            received += len(chunk)
    elapsed = max(0.001, time.perf_counter() - t0)
    return round((received * 8.0) / (elapsed * 1_000_000.0), 2)

def measure_upload(size_mb: int = 4) -> float:
    payload = b"0" * (max(1, size_mb) * 1_000_000)
    req = urllib.request.Request(
        CF_UP_URL,
        data=payload,
        method="POST",
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/octet-stream"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()
    elapsed = max(0.001, time.perf_counter() - t0)
    return round((len(payload) * 8.0) / (elapsed * 1_000_000.0), 2)

def run_speedtest(size_mb: int = 15, as_json: bool = False) -> Dict[str, Any]:
    if not as_json:
        print("Kit Network Speed Test (Cloudflare Global Edge)")
        print("===============================================")
        print("  * Measuring latency & jitter...", end=" ", flush=True)
    latency = measure_ping(samples=5)
    if not as_json:
        print(f"{latency['ping_ms']} ms (jitter: {latency['jitter_ms']} ms)")
        print(f"  * Measuring download speed ({size_mb} MB)...", end=" ", flush=True)
    down_mbps = measure_download(size_mb=size_mb)
    if not as_json:
        print(f"{down_mbps} Mbps")
        print("  * Measuring upload speed (4 MB)...", end=" ", flush=True)
    up_mbps = measure_upload(size_mb=4)
    if not as_json:
        print(f"{up_mbps} Mbps")
    result = {
        "ping_ms": latency["ping_ms"],
        "jitter_ms": latency["jitter_ms"],
        "download_mbps": down_mbps,
        "upload_mbps": up_mbps,
    }
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print("\nSummary:")
        print(f"  Ping:     {result['ping_ms']} ms (Jitter: {result['jitter_ms']} ms)")
        print(f"  Download: {result['download_mbps']} Mbps")
        print(f"  Upload:   {result['upload_mbps']} Mbps")
    return result
