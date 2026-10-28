from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json, socket, statistics, time, urllib.request
from typing import Any, Dict, List

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin": "https://speed.cloudflare.com",
    "Referer": "https://speed.cloudflare.com/",
    "Accept": "*/*",
}

def measure_ping(samples: int = 6) -> Dict[str, float]:
    rtts: List[float] = []
    targets = [("1.1.1.1", 443), ("8.8.8.8", 443)]
    for i in range(samples):
        host, port = targets[i % len(targets)]
        try:
            t0 = time.perf_counter()
            with socket.create_connection((host, port), timeout=5):
                rtts.append((time.perf_counter() - t0) * 1000.0)
        except Exception:
            continue
    if not rtts:
        return {"ping_ms": 0.0, "jitter_ms": 0.0}
    return {
        "ping_ms": round(min(rtts), 2),
        "jitter_ms": round(statistics.stdev(rtts), 2) if len(rtts) > 1 else 0.0,
    }

def _download_worker(url: str, max_bytes: int) -> int:
    req = urllib.request.Request(url, headers=HEADERS)
    received = 0
    with urllib.request.urlopen(req, timeout=25) as resp:
        while received < max_bytes:
            chunk = resp.read(min(65536, max_bytes - received))
            if not chunk:
                break
            received += len(chunk)
    return received

def measure_download(size_mb: int = 15) -> float:
    total_bytes = max(1, size_mb) * 1_000_000
    per_worker = max(1_000_000, total_bytes // 4)
    candidate_urls = [
        f"https://speed.cloudflare.com/__down?bytes={per_worker}",
        "https://proof.ovh.net/files/10Mb.dat",
        "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js",
    ]
    for url in candidate_urls:
        try:
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(_download_worker, url, per_worker) for _ in range(4)]
                received = sum(f.result() for f in futures)
            elapsed = max(0.001, time.perf_counter() - t0)
            if received > 0:
                return round((received * 8.0) / (elapsed * 1_000_000.0), 2)
        except Exception:
            continue
    return 0.0

def _upload_worker(url: str, payload: bytes) -> int:
    hdrs = dict(HEADERS)
    hdrs["Content-Type"] = "application/octet-stream"
    req = urllib.request.Request(url, data=payload, method="POST", headers=hdrs)
    with urllib.request.urlopen(req, timeout=25) as resp:
        resp.read(1024)
    return len(payload)

def measure_upload(size_mb: int = 4) -> float:
    chunk_bytes = max(500_000, (max(1, size_mb) * 1_000_000) // 4)
    payload = b"0" * chunk_bytes
    candidate_urls = [
        "https://speed.cloudflare.com/__up",
        "https://postman-echo.com/post",
        "https://httpbin.org/post",
    ]
    for url in candidate_urls:
        try:
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(_upload_worker, url, payload) for _ in range(4)]
                sent = sum(f.result() for f in futures)
            elapsed = max(0.001, time.perf_counter() - t0)
            if sent > 0:
                return round((sent * 8.0) / (elapsed * 1_000_000.0), 2)
        except Exception:
            continue
    return 0.0

def run_speedtest(size_mb: int = 15, as_json: bool = False) -> Dict[str, Any]:
    if not as_json:
        print("Kit Network Speed Test (Multi-Thread Edge Benchmark)")
        print("====================================================")
        print("  * Measuring latency & jitter...", end=" ", flush=True)
    latency = measure_ping(samples=6)
    if not as_json:
        print(f"{latency['ping_ms']} ms (jitter: {latency['jitter_ms']} ms)")
        print(f"  * Measuring download speed ({size_mb} MB, 4 threads)...", end=" ", flush=True)
    down_mbps = measure_download(size_mb=size_mb)
    if not as_json:
        print(f"{down_mbps} Mbps")
        print("  * Measuring upload speed (4 MB, 4 threads)...", end=" ", flush=True)
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
