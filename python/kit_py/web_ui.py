from __future__ import annotations
import base64, hmac, json, os, secrets, socket, subprocess, tempfile, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from kit_py.media_dl import DEFAULT_DL_DIR, download_url
from kit_py.native_fallback import run_encode
from kit_py.net_speed import run_speedtest
from kit_py.qr_tools import render_qr
from kit_py.textract_tools import run_textract

SESSION_TOKEN = secrets.token_urlsafe(32)
MAX_BODY_BYTES = 25 * 1024 * 1024
ALLOWED_OCR_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".pdf"}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kit Studio - Fast All-in-One Toolkit</title>
<style>
  :root { --bg:#0b0f19; --card:#131b2e; --border:#23304d; --accent:#38bdf8; --accent2:#818cf8; --text:#f1f5f9; --muted:#94a3b8; --success:#34d399; }
  * { box-sizing:border-box; margin:0; padding:0; font-family:'Segoe UI',system-ui,sans-serif; }
  body { background:var(--bg); color:var(--text); min-height:100vh; padding:28px; }
  .container { max-width:1120px; margin:0 auto; }
  header { display:flex; justify-content:space-between; align-items:center; margin-bottom:28px; padding-bottom:18px; border-bottom:1px solid var(--border); }
  .brand { display:flex; align-items:center; gap:12px; }
  .logo { width:42px; height:42px; border-radius:10px; background:linear-gradient(135deg,var(--accent),var(--accent2)); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:20px; color:#0b0f19; }
  h1 { font-size:24px; font-weight:700; }
  .badge { background:rgba(52,211,153,0.15); color:var(--success); border:1px solid rgba(52,211,153,0.3); padding:5px 12px; border-radius:999px; font-size:13px; font-weight:600; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(480px,1fr)); gap:22px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:22px; display:flex; flex-direction:column; gap:14px; box-shadow:0 8px 24px rgba(0,0,0,0.25); }
  .card h2 { font-size:18px; color:var(--accent); }
  .card p { font-size:13.5px; color:var(--muted); }
  label { font-size:13px; color:var(--muted); font-weight:600; display:block; margin-bottom:6px; }
  input[type="text"], select, textarea { width:100%; background:#090d16; border:1px solid var(--border); color:var(--text); padding:10px 13px; border-radius:8px; font-size:14px; outline:none; }
  .row { display:flex; gap:10px; align-items:center; }
  button { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#0b0f19; font-weight:700; border:none; padding:10px 16px; border-radius:8px; cursor:pointer; font-size:14px; white-space:nowrap; }
  button:disabled { opacity:0.5; cursor:not-allowed; }
  button.secondary { background:#1e293b; color:var(--text); border:1px solid var(--border); font-weight:600; }
  .output { background:#070a12; border:1px solid var(--border); border-radius:8px; padding:12px; font-family:Consolas,monospace; font-size:13px; white-space:pre-wrap; word-break:break-all; min-height:54px; max-height:220px; overflow-y:auto; color:#cbd5e1; }
  .stats { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-top:6px; }
  .stat-box { background:#090d16; border:1px solid var(--border); border-radius:10px; padding:12px; text-align:center; }
  .stat-val { font-size:20px; font-weight:800; color:var(--success); margin-top:4px; }
  .stat-lbl { font-size:11.5px; color:var(--muted); text-transform:uppercase; }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="brand">
      <div class="logo">K</div>
      <div>
        <h1>Kit Web Studio</h1>
        <p style="font-size:13px;color:var(--muted);">CSRF-Protected Local Hybrid Dashboard</p>
      </div>
    </div>
    <div class="row">
      <button class="secondary" onclick="openDownloads()">Open Downloads Folder</button>
      <span class="badge">Secured Local Session</span>
    </div>
  </header>
  <div class="grid">
    <div class="card">
      <h2>Video & Audio Downloader (kit dl)</h2>
      <p>Download MP4 video or MP3 audio from YouTube, TikTok, Twitch, X, and 1,000+ sites.</p>
      <div>
        <label>Video or Playlist URL (http/https)</label>
        <input type="text" id="dl-url" placeholder="https://www.youtube.com/watch?v=...">
      </div>
      <div class="row">
        <div style="flex:1;"><label>Max Quality</label><select id="dl-quality"><option value="1080">1080p Full HD</option><option value="720" selected>720p HD</option><option value="480">480p</option><option value="best">Best Available</option></select></div>
        <div style="flex:1;"><label>Mode</label><select id="dl-mode"><option value="video">Video (MP4)</option><option value="audio">Audio Only (MP3)</option></select></div>
      </div>
      <div class="row">
        <button onclick="runDownload()" id="dl-btn">Download Now</button>
        <button class="secondary" onclick="openDownloads()">Open Folder</button>
      </div>
      <div class="output" id="dl-out">Ready to download into D:\\kit\\downloads.</div>
    </div>
    <div class="card">
      <h2>Network Speed Test (kit ns)</h2>
      <p>Measure real-time Ping, Jitter, Download Mbps, and Upload Mbps across 4 parallel threads.</p>
      <div class="stats">
        <div class="stat-box"><div class="stat-lbl">Ping</div><div class="stat-val" id="ns-ping">--</div></div>
        <div class="stat-box"><div class="stat-lbl">Jitter</div><div class="stat-val" id="ns-jitter">--</div></div>
        <div class="stat-box"><div class="stat-lbl">Download</div><div class="stat-val" id="ns-down">--</div></div>
        <div class="stat-box"><div class="stat-lbl">Upload</div><div class="stat-val" id="ns-up">--</div></div>
      </div>
      <div class="row"><button onclick="runSpeedTest()" id="ns-btn">Start Speed Test</button></div>
      <div class="output" id="ns-out">Click "Start Speed Test" to benchmark your connection.</div>
    </div>
    <div class="card">
      <h2>Textract OCR & PDF Reader (kit textract)</h2>
      <p>Extract text from any image (.png, .jpg, .webp), PDF file, or directly from your Windows clipboard screenshot.</p>
      <div class="row">
        <input type="file" id="ocr-file" accept=".png,.jpg,.jpeg,.webp,.bmp,.pdf" style="flex:1;color:var(--muted);font-size:13px;">
        <button onclick="runOcrFile()">Extract File</button>
        <button class="secondary" onclick="runOcrClip()">From Clipboard</button>
      </div>
      <textarea id="ocr-out" rows="5" placeholder="Extracted text will appear here..."></textarea>
      <div class="row"><button class="secondary" onclick="navigator.clipboard.writeText(document.getElementById('ocr-out').value)">Copy Text</button></div>
    </div>
    <div class="card">
      <h2>QR Generator & Dev Encode (kit qr / encode)</h2>
      <p>Generate instant QR codes or encode/decode Base64, Hex, JWT, and UUIDs.</p>
      <div class="row">
        <input type="text" id="util-input" placeholder="Enter URL, text, or token..." value="https://github.com/LimitlessDaoist/Kit">
        <button onclick="runQr()">QR Code</button>
      </div>
      <div class="row">
        <button class="secondary" onclick="runEncode('base64-enc')">Base64 Encode</button>
        <button class="secondary" onclick="runEncode('base64-dec')">Base64 Decode</button>
        <button class="secondary" onclick="runEncode('uuid')">New UUID</button>
      </div>
      <div class="output" id="util-out">Output will appear here.</div>
      <div id="qr-img-wrap" style="text-align:center;"></div>
    </div>
  </div>
</div>
<script>
const KIT_TOKEN = "__KIT_SESSION_TOKEN__";
async function api(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Kit-Token': KIT_TOKEN },
    body: JSON.stringify(body || {})
  });
  return await res.json();
}
async function openDownloads() { await api('/api/open-downloads', {}); }
async function runDownload() {
  const url = document.getElementById('dl-url').value.trim();
  if (!url) { alert('Please enter a video URL first'); return; }
  const quality = document.getElementById('dl-quality').value;
  const audio_only = document.getElementById('dl-mode').value === 'audio';
  const out = document.getElementById('dl-out');
  const btn = document.getElementById('dl-btn');
  btn.disabled = true;
  out.textContent = 'Downloading... please wait...';
  try {
    const data = await api('/api/dl', { url, quality, audio_only });
    out.textContent = data.error ? ('Error: ' + data.error) : ('Downloaded: ' + (data.title || url) + '\\nSaved in: ' + data.output_dir);
  } catch (e) { out.textContent = 'Error: ' + e; } finally { btn.disabled = false; }
}
async function runSpeedTest() {
  const out = document.getElementById('ns-out');
  const btn = document.getElementById('ns-btn');
  btn.disabled = true;
  out.textContent = 'Testing ping, download, and upload speeds...';
  try {
    const data = await api('/api/ns', { size_mb: 10 });
    if (data.error) out.textContent = 'Error: ' + data.error;
    else {
      document.getElementById('ns-ping').textContent = data.ping_ms + ' ms';
      document.getElementById('ns-jitter').textContent = data.jitter_ms + ' ms';
      document.getElementById('ns-down').textContent = data.download_mbps + ' Mbps';
      document.getElementById('ns-up').textContent = data.upload_mbps + ' Mbps';
      out.textContent = 'Speed test complete!';
    }
  } catch (e) { out.textContent = 'Error: ' + e; } finally { btn.disabled = false; }
}
async function runOcrClip() {
  const out = document.getElementById('ocr-out');
  out.value = 'Extracting text from clipboard image...';
  const data = await api('/api/textract', { clip: true });
  out.value = data.error ? ('Error: ' + data.error) : (data.text || '[No text found]');
}
async function runOcrFile() {
  const fileInput = document.getElementById('ocr-file');
  const out = document.getElementById('ocr-out');
  if (!fileInput.files.length) { alert('Choose an image or PDF file first'); return; }
  const file = fileInput.files[0];
  out.value = 'Processing ' + file.name + '...';
  const reader = new FileReader();
  reader.onload = async () => {
    const b64 = reader.result.split(',')[1];
    const data = await api('/api/textract', { filename: file.name, data_b64: b64 });
    out.value = data.error ? ('Error: ' + data.error) : (data.text || '[No text found]');
  };
  reader.readAsDataURL(file);
}
async function runQr() {
  const payload = document.getElementById('util-input').value.trim();
  const data = await api('/api/qr', { payload });
  document.getElementById('util-out').textContent = data.ascii || '';
  const wrap = document.getElementById('qr-img-wrap');
  wrap.textContent = '';
  if (data.png_b64) {
    const img = document.createElement('img');
    img.src = 'data:image/png;base64,' + data.png_b64;
    img.style.maxWidth = '180px';
    img.style.borderRadius = '8px';
    img.style.marginTop = '8px';
    wrap.appendChild(img);
  }
}
async function runEncode(mode) {
  const input = document.getElementById('util-input').value;
  const data = await api('/api/encode', { mode, input });
  document.getElementById('qr-img-wrap').textContent = '';
  document.getElementById('util-out').textContent = data.error ? ('Error: ' + data.error) : data.result;
}
</script>
</body>
</html>"""

HTML_PAGE = HTML_TEMPLATE.replace("__KIT_SESSION_TOKEN__", SESSION_TOKEN)

def is_authorized_request(headers: Any, server_port: int) -> tuple[bool, str]:
    host = (headers.get("Host") or "").lower().strip()
    allowed_hosts = {f"127.0.0.1:{server_port}", f"localhost:{server_port}", "127.0.0.1", "localhost"}
    if host not in allowed_hosts:
        return False, "Forbidden Host header (DNS rebinding protection)."
    origin = (headers.get("Origin") or "").lower().strip()
    if origin and origin not in {f"http://127.0.0.1:{server_port}", f"http://localhost:{server_port}"}:
        return False, "Forbidden Cross-Origin request."
    provided_token = headers.get("X-Kit-Token") or ""
    if not hmac.compare_digest(provided_token, SESSION_TOKEN):
        return False, "Missing or invalid X-Kit-Token (CSRF protection)."
    return True, "ok"

class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

class KitUiHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass
    def _add_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';")
    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self._add_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self._send_json({"error": "Not found"}, status=404)
            return
        raw = HTML_TEMPLATE.replace("__KIT_SESSION_TOKEN__", SESSION_TOKEN).encode("utf-8")
        self.send_response(200)
        self._add_security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_POST(self) -> None:
        ok, reason = is_authorized_request(self.headers, self.server.server_port)
        if not ok:
            self._send_json({"error": reason}, status=403)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            self._send_json({"error": "Payload exceeds 25 MB limit."}, status=413)
            return
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        try:
            if self.path == "/api/open-downloads":
                DEFAULT_DL_DIR.mkdir(parents=True, exist_ok=True)
                if os.name == "nt":
                    subprocess.Popen(["explorer", str(DEFAULT_DL_DIR.resolve())])
                self._send_json({"ok": True})
            elif self.path == "/api/dl":
                res = download_url(url=str(body.get("url", "")), quality=str(body.get("quality", "720")), audio_only=bool(body.get("audio_only", False)), open_folder=True)
                self._send_json(res)
            elif self.path == "/api/ns":
                res = run_speedtest(size_mb=int(body.get("size_mb", 10)), as_json=True)
                self._send_json(res)
            elif self.path == "/api/textract":
                if body.get("clip"):
                    text = run_textract(from_clipboard=True)
                else:
                    suffix = Path(str(body.get("filename", "upload.png"))).suffix.lower() or ".png"
                    if suffix not in ALLOWED_OCR_EXTS:
                        raise ValueError(f"Unsupported file extension '{suffix}'.")
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                        tmp.write(base64.b64decode(body["data_b64"]))
                        tmp_path = Path(tmp.name)
                    try:
                        text = run_textract(input_path=tmp_path)
                    finally:
                        tmp_path.unlink(missing_ok=True)
                self._send_json({"text": text})
            elif self.path == "/api/qr":
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                try:
                    ascii_art = render_qr(str(body.get("payload", "https://kit.local"))[:2048], output=tmp_path)
                    b64 = base64.b64encode(tmp_path.read_bytes()).decode("ascii")
                finally:
                    tmp_path.unlink(missing_ok=True)
                self._send_json({"ascii": ascii_art, "png_b64": b64})
            elif self.path == "/api/encode":
                res = run_encode(str(body["mode"]), body.get("input"))
                self._send_json({"result": res})
            else:
                self._send_json({"error": "Unknown endpoint"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

def find_available_port(preferred: int = 8420) -> int:
    for candidate in range(preferred, preferred + 15):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", candidate)) != 0:
                return candidate
    return preferred

def launch_ui(port: int = 8420, open_browser: bool = True) -> None:
    actual_port = find_available_port(port)
    url = f"http://127.0.0.1:{actual_port}"
    server = ReusableThreadingHTTPServer(("127.0.0.1", actual_port), KitUiHandler)
    print(f"Kit Web Studio running at: {url} (CSRF & DNS-Rebinding protection active)")
    print("Press Ctrl+C in this terminal to stop the server.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Kit Web Studio.")
        server.server_close()
