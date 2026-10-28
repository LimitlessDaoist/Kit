from __future__ import annotations
import base64, hmac, json, os, secrets, socket, subprocess, tempfile, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from kit_py.audio_tools import run_audio_extract, run_silence_strip
from kit_py.media_dl import DEFAULT_DL_DIR, download_url
from kit_py.meta_tools import inspect_or_strip_meta
from kit_py.native_fallback import run_encode
from kit_py.net_speed import run_speedtest
from kit_py.qr_tools import render_qr
from kit_py.security_tools import decrypt_file, encrypt_file, generate_passwords, shred_file
from kit_py.textract_tools import run_textract

SESSION_TOKEN = secrets.token_urlsafe(32)
MAX_BODY_BYTES = 25 * 1024 * 1024
ALLOWED_OCR_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".pdf"}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KIT // WORKSTATION</title>
<style>
  :root {
    --bg: #09090b; --sidebar: #0e0e11; --surface: #141418; --surface-hover: #1c1c22;
    --input-bg: #09090b; --border: #26262c; --border-focus: #52525b; --text: #fafafa;
    --text-secondary: #a1a1aa; --text-muted: #71717a; --accent: #f4f4f5; --accent-fg: #09090b;
    --green: #10b981; --danger: #ef4444;
    --mono: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); font-size: 13.5px; line-height: 1.5; height: 100vh; display: flex; overflow: hidden; -webkit-font-smoothing: antialiased; }
  aside { width: 248px; background: var(--sidebar); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; user-select: none; }
  .brand-bar { height: 52px; padding: 0 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); }
  .brand-title { font-family: var(--mono); font-weight: 700; font-size: 13px; letter-spacing: 0.08em; display: flex; align-items: center; gap: 8px; }
  .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px rgba(16, 185, 129, 0.5); }
  .version-tag { font-family: var(--mono); font-size: 11px; color: var(--text-muted); background: #18181c; padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border); }
  .search-box { padding: 10px 12px; border-bottom: 1px solid var(--border); }
  .search-box input { width: 100%; background: var(--input-bg); border: 1px solid var(--border); color: var(--text); padding: 6px 10px; border-radius: 5px; font-size: 12px; font-family: var(--mono); outline: none; }
  .search-box input:focus { border-color: var(--border-focus); }
  .nav-scroll { flex: 1; overflow-y: auto; padding: 10px 8px; }
  .nav-group-label { font-family: var(--mono); font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); padding: 10px 8px 4px; }
  .nav-item { display: flex; align-items: center; justify-content: space-between; width: 100%; text-align: left; background: transparent; color: var(--text-secondary); border: none; padding: 7px 10px; border-radius: 5px; cursor: pointer; font-size: 13px; font-weight: 500; }
  .nav-item:hover { background: var(--surface); color: var(--text); }
  .nav-item.active { background: #1f1f26; color: var(--text); }
  .nav-cmd { font-family: var(--mono); font-size: 11px; color: var(--text-muted); }
  .sidebar-footer { padding: 12px; border-top: 1px solid var(--border); }
  main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .topbar { height: 52px; border-bottom: 1px solid var(--border); padding: 0 24px; display: flex; align-items: center; justify-content: space-between; background: var(--sidebar); }
  .topbar-path { font-family: var(--mono); font-size: 12px; color: var(--text-secondary); }
  .workspace { flex: 1; overflow-y: auto; padding: 28px 32px; max-width: 960px; }
  .panel { display: none; flex-direction: column; gap: 20px; }
  .panel.active { display: flex; }
  .panel-header { border-bottom: 1px solid var(--border); padding-bottom: 14px; }
  .panel-title { font-size: 18px; font-weight: 600; letter-spacing: -0.01em; display: flex; align-items: center; gap: 10px; }
  .cmd-pill { font-family: var(--mono); font-size: 11.5px; font-weight: 500; background: var(--surface); color: var(--text-secondary); border: 1px solid var(--border); padding: 2px 8px; border-radius: 4px; }
  .panel-desc { color: var(--text-secondary); font-size: 13px; margin-top: 4px; }
  .card-box { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 18px; display: flex; flex-direction: column; gap: 14px; }
  .field-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  label { display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 5px; }
  input[type="text"], input[type="password"], input[type="number"], select, textarea { width: 100%; background: var(--input-bg); border: 1px solid var(--border); color: var(--text); padding: 8px 11px; border-radius: 5px; font-size: 13px; font-family: var(--sans); outline: none; }
  .mono-input { font-family: var(--mono) !important; font-size: 12.5px !important; }
  input:focus, select:focus, textarea:focus { border-color: var(--border-focus); }
  .btn-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  button.btn { background: var(--accent); color: var(--accent-fg); border: 1px solid var(--accent); padding: 7px 14px; border-radius: 5px; font-size: 12.5px; font-weight: 600; cursor: pointer; }
  button.btn:disabled { opacity: 0.45; cursor: not-allowed; }
  button.btn-ghost { background: #1a1a20; color: var(--text); border: 1px solid var(--border); }
  button.btn-ghost:hover { background: var(--surface-hover); }
  button.btn-danger { background: rgba(239, 68, 68, 0.14); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.35); }
  .terminal-out { background: #060608; border: 1px solid var(--border); border-radius: 5px; padding: 12px 14px; font-family: var(--mono); font-size: 12px; color: #d4d4d8; white-space: pre-wrap; word-break: break-all; min-height: 76px; max-height: 280px; overflow-y: auto; }
  .metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
  .metric-cell { background: var(--input-bg); border: 1px solid var(--border); border-radius: 5px; padding: 12px 14px; }
  .metric-label { font-family: var(--mono); font-size: 11px; color: var(--text-muted); text-transform: uppercase; }
  .metric-val { font-family: var(--mono); font-size: 20px; font-weight: 700; color: var(--text); margin-top: 4px; }
  #toast { position: fixed; bottom: 18px; right: 22px; background: #18181b; color: var(--text); border: 1px solid #3f3f46; padding: 9px 14px; border-radius: 5px; font-family: var(--mono); font-size: 12px; display: none; z-index: 1000; }
</style>
</head>
<body>
  <aside>
    <div class="brand-bar">
      <div class="brand-title"><span class="status-dot"></span> KIT // STUDIO</div>
      <span class="version-tag">v0.4</span>
    </div>
    <div class="search-box">
      <input type="text" id="nav-filter" placeholder="Filter tools ( / )..." oninput="filterNav(this.value)">
    </div>
    <div class="nav-scroll" id="nav-list">
      <div class="nav-group-label">Media & Audio</div>
      <button class="nav-item active" onclick="switchPanel('dl', this)"><span>Video Downloader</span><span class="nav-cmd">dl</span></button>
      <button class="nav-item" onclick="switchPanel('audio', this)"><span>Audio Ripper & Norm</span><span class="nav-cmd">audio</span></button>
      <button class="nav-item" onclick="switchPanel('silence', this)"><span>Silence Trimmer</span><span class="nav-cmd">silence</span></button>
      <div class="nav-group-label">Security & Privacy</div>
      <button class="nav-item" onclick="switchPanel('pass', this)"><span>Password & Key Gen</span><span class="nav-cmd">pass</span></button>
      <button class="nav-item" onclick="switchPanel('crypt', this)"><span>AES-256 File Vault</span><span class="nav-cmd">encrypt</span></button>
      <button class="nav-item" onclick="switchPanel('meta', this)"><span>Metadata Inspector</span><span class="nav-cmd">meta</span></button>
      <button class="nav-item" onclick="switchPanel('shred', this)"><span>Secure File Shredder</span><span class="nav-cmd">shred</span></button>
      <div class="nav-group-label">Documents & OCR</div>
      <button class="nav-item" onclick="switchPanel('textract', this)"><span>OCR & PDF Textract</span><span class="nav-cmd">textract</span></button>
      <div class="nav-group-label">Network & Dev</div>
      <button class="nav-item" onclick="switchPanel('ns', this)"><span>Speed Benchmark</span><span class="nav-cmd">ns</span></button>
      <button class="nav-item" onclick="switchPanel('qr', this)"><span>QR & Encoding</span><span class="nav-cmd">qr/enc</span></button>
    </div>
    <div class="sidebar-footer">
      <button class="btn btn-ghost" style="width:100%;" onclick="openDownloads()">Open Downloads Dir</button>
    </div>
  </aside>
  <main>
    <div class="topbar">
      <div class="topbar-path" id="breadcrumb">kit / studio / dl</div>
      <div class="topbar-path">127.0.0.1 // SESSION VERIFIED</div>
    </div>
    <div class="workspace">
      <section class="panel active" id="panel-dl">
        <div class="panel-header">
          <div class="panel-title">Video & Stream Downloader <span class="cmd-pill">kit dl</span></div>
          <div class="panel-desc">Download video or extract audio streams via yt-dlp and bundled FFmpeg.</div>
        </div>
        <div class="card-box">
          <div><label>Source URL</label><input type="text" id="dl-url" class="mono-input" placeholder="https://www.youtube.com/watch?v=..."></div>
          <div class="field-grid">
            <div><label>Resolution Ceiling</label><select id="dl-quality"><option value="1080">1080p (Full HD)</option><option value="720" selected>720p (HD)</option><option value="480">480p</option><option value="best">Best Available</option></select></div>
            <div><label>Stream Mode</label><select id="dl-mode"><option value="video">Merged Video (MP4)</option><option value="audio">Audio Stream Only (MP3)</option></select></div>
            <div><label>Timestamp Clip (Optional)</label><input type="text" id="dl-clip" class="mono-input" placeholder="00:01:00-00:02:15"></div>
          </div>
          <div class="btn-row"><button class="btn" id="dl-btn" onclick="runDownload()">Execute Download</button><button class="btn btn-ghost" onclick="openDownloads()">Open Output Folder</button></div>
          <div class="terminal-out" id="dl-out">Ready. Output directory: D:\\kit\\downloads</div>
        </div>
      </section>
      <section class="panel" id="panel-audio">
        <div class="panel-header">
          <div class="panel-title">Audio Extractor & EBU R128 Normalizer <span class="cmd-pill">kit audio</span></div>
          <div class="panel-desc">Rip high-bitrate audio from local video files or URLs with optional broadcast loudness normalization.</div>
        </div>
        <div class="card-box">
          <div><label>Local File Path or Media URL</label><input type="text" id="audio-src" class="mono-input" placeholder="D:\\kit\\downloads\\video.mp4 or https://..."></div>
          <div class="field-grid">
            <div><label>Target Codec</label><select id="audio-fmt"><option value="mp3" selected>MP3</option><option value="flac">FLAC (Lossless)</option><option value="m4a">M4A (AAC)</option><option value="wav">WAV</option><option value="opus">Opus</option></select></div>
            <div><label>Bitrate</label><select id="audio-br"><option value="320k" selected>320 kbps</option><option value="256k">256 kbps</option><option value="192k">192 kbps</option><option value="128k">128 kbps</option></select></div>
            <div><label>Loudness Normalization</label><select id="audio-norm"><option value="true" selected>Enable EBU R128 (-16 LUFS)</option><option value="false">Direct Pass-Through</option></select></div>
          </div>
          <div class="btn-row"><button class="btn" id="audio-btn" onclick="runAudio()">Process Audio</button></div>
          <div class="terminal-out" id="audio-out">Waiting for input.</div>
        </div>
      </section>
      <section class="panel" id="panel-silence">
        <div class="panel-header">
          <div class="panel-title">Dead-Air & Silence Trimmer <span class="cmd-pill">kit silence</span></div>
          <div class="panel-desc">Automatically strip pauses and dead air from lectures, podcasts, or voice recordings.</div>
        </div>
        <div class="card-box">
          <div><label>Input Audio or Video File Path</label><input type="text" id="sil-input" class="mono-input" placeholder="D:\\kit\\downloads\\lecture.mp4"></div>
          <div class="field-grid">
            <div><label>Silence Threshold (dB)</label><input type="number" id="sil-db" class="mono-input" value="-38" min="-80" max="-10"></div>
            <div><label>Minimum Silence Duration (Seconds)</label><input type="number" id="sil-dur" class="mono-input" value="0.35" step="0.05" min="0.05" max="10"></div>
          </div>
          <div class="btn-row"><button class="btn" id="sil-btn" onclick="runSilence()">Strip Silence</button></div>
          <div class="terminal-out" id="sil-out">Ready. Output saved as &lt;filename&gt;_nosilence.&lt;ext&gt;.</div>
        </div>
      </section>
      <section class="panel" id="panel-pass">
        <div class="panel-header">
          <div class="panel-title">CSPRNG Password & Passphrase Generator <span class="cmd-pill">kit pass</span></div>
          <div class="panel-desc">Generate high-entropy credentials using OS-level cryptographic randomness (os.urandom).</div>
        </div>
        <div class="card-box">
          <div class="field-grid">
            <div><label>Mode</label><select id="pass-mode"><option value="password" selected>Random Character Password</option><option value="passphrase">Multi-Word Passphrase</option></select></div>
            <div><label>Length (Chars) / Word Count</label><input type="number" id="pass-len" class="mono-input" value="24" min="4" max="128"></div>
            <div><label>Symbol Set</label><select id="pass-sym"><option value="true" selected>Include Symbols (!@#$...)</option><option value="false">Alphanumeric Only</option></select></div>
            <div><label>Batch Count</label><input type="number" id="pass-count" class="mono-input" value="5" min="1" max="25"></div>
          </div>
          <div class="btn-row"><button class="btn" onclick="runPass()">Generate Credentials</button><button class="btn btn-ghost" onclick="copyText('pass-out')">Copy Output</button></div>
          <div class="terminal-out" id="pass-out">Click "Generate Credentials" to sample from OS CSPRNG.</div>
        </div>
      </section>
      <section class="panel" id="panel-crypt">
        <div class="panel-header">
          <div class="panel-title">AES-256-GCM Authenticated File Vault <span class="cmd-pill">kit encrypt / decrypt</span></div>
          <div class="panel-desc">Encrypt or decrypt local files using PBKDF2-HMAC-SHA256 (600,000 iterations) + AES-256-GCM.</div>
        </div>
        <div class="card-box">
          <div class="field-grid">
            <div><label>Operation</label><select id="crypt-op"><option value="encrypt" selected>Encrypt File (.kitenc)</option><option value="decrypt">Decrypt File</option></select></div>
            <div><label>Target File Path on Disk</label><input type="text" id="crypt-path" class="mono-input" placeholder="D:\\secret_document.pdf"></div>
          </div>
          <div><label>Passphrase</label><input type="password" id="crypt-pw" class="mono-input" placeholder="Enter strong encryption passphrase..."></div>
          <div class="btn-row"><button class="btn" id="crypt-btn" onclick="runCrypt()">Run Vault Operation</button></div>
          <div class="terminal-out" id="crypt-out">PBKDF2-HMAC-SHA256 (600,000 iterations) + 96-bit Nonce + 128-bit GCM Auth Tag.</div>
        </div>
      </section>
      <section class="panel" id="panel-meta">
        <div class="panel-header">
          <div class="panel-title">Metadata Inspector & Privacy Scrubber <span class="cmd-pill">kit meta</span></div>
          <div class="panel-desc">Inspect or strip hidden EXIF, GPS, camera serials, and PDF author/timestamp properties.</div>
        </div>
        <div class="card-box">
          <div><label>Local File Path (Image or PDF)</label><input type="text" id="meta-path" class="mono-input" placeholder="D:\\photo.jpg or D:\\report.pdf"></div>
          <div class="btn-row"><button class="btn" onclick="runMeta(false)">Inspect Metadata</button><button class="btn btn-ghost" onclick="runMeta(true)">Strip Metadata & Save Clean Copy</button></div>
          <div class="terminal-out" id="meta-out">Select an image or PDF path to inspect embedded tags.</div>
        </div>
      </section>
      <section class="panel" id="panel-shred">
        <div class="panel-header">
          <div class="panel-title">Multi-Pass Cryptographic File Shredder <span class="cmd-pill">kit shred</span></div>
          <div class="panel-desc">Overwrite file blocks in-place with random bytes + zero pass, flush to disk, obfuscate filename, and unlink.</div>
        </div>
        <div class="card-box">
          <div class="field-grid">
            <div style="grid-column: span 2;"><label>File Path to Permanently Destroy</label><input type="text" id="shred-path" class="mono-input" placeholder="D:\\temp_sensitive.txt"></div>
            <div><label>Overwrite Passes</label><select id="shred-passes"><option value="3" selected>3 Passes (CSPRNG + Zero)</option><option value="7">7 Passes</option><option value="1">1 Pass</option></select></div>
          </div>
          <div class="btn-row"><button class="btn btn-danger" onclick="runShred()">Permanently Shred File</button></div>
          <div class="terminal-out" id="shred-out">WARNING: Shredded files cannot be recovered by undelete tools.</div>
        </div>
      </section>
      <section class="panel" id="panel-textract">
        <div class="panel-header">
          <div class="panel-title">Optical Character Recognition & PDF Reader <span class="cmd-pill">kit textract</span></div>
          <div class="panel-desc">Extract text from images, PDF documents, or directly from your Windows clipboard screenshot (Win+Shift+S).</div>
        </div>
        <div class="card-box">
          <div class="btn-row">
            <input type="file" id="ocr-file" accept=".png,.jpg,.jpeg,.webp,.bmp,.pdf" style="flex:1;">
            <button class="btn" onclick="runOcrFile()">Extract Uploaded File</button>
            <button class="btn btn-ghost" onclick="runOcrClip()">Read Windows Clipboard</button>
          </div>
          <textarea id="ocr-out" class="mono-input" rows="8" placeholder="Extracted text output..."></textarea>
          <div class="btn-row"><button class="btn btn-ghost" onclick="copyText('ocr-out', true)">Copy Text to Clipboard</button></div>
        </div>
      </section>
      <section class="panel" id="panel-ns">
        <div class="panel-header">
          <div class="panel-title">Multi-Thread Network Speed Benchmark <span class="cmd-pill">kit ns</span></div>
          <div class="panel-desc">Measure TCP handshake latency, jitter, and 4-thread parallel throughput.</div>
        </div>
        <div class="card-box">
          <div class="metrics-row">
            <div class="metric-cell"><div class="metric-label">Latency</div><div class="metric-val" id="ns-ping">--</div></div>
            <div class="metric-cell"><div class="metric-label">Jitter</div><div class="metric-val" id="ns-jitter">--</div></div>
            <div class="metric-cell"><div class="metric-label">Download</div><div class="metric-val" id="ns-down">--</div></div>
            <div class="metric-cell"><div class="metric-label">Upload</div><div class="metric-val" id="ns-up">--</div></div>
          </div>
          <div class="btn-row"><button class="btn" id="ns-btn" onclick="runSpeedTest()">Run Benchmark</button></div>
          <div class="terminal-out" id="ns-out">Idle. Click "Run Benchmark" to test against edge CDN nodes.</div>
        </div>
      </section>
      <section class="panel" id="panel-qr">
        <div class="panel-header">
          <div class="panel-title">QR Matrix & Developer Encoding <span class="cmd-pill">kit qr / encode</span></div>
          <div class="panel-desc">Generate QR payloads or run Base64, Hex, JWT inspection, and UUIDv4 generation.</div>
        </div>
        <div class="card-box">
          <div><label>Input String / Token / URL</label><input type="text" id="util-input" class="mono-input" value="https://github.com/LimitlessDaoist/Kit"></div>
          <div class="btn-row">
            <button class="btn" onclick="runQr()">Render QR</button>
            <button class="btn btn-ghost" onclick="runEncode('base64-enc')">Base64 Encode</button>
            <button class="btn btn-ghost" onclick="runEncode('base64-dec')">Base64 Decode</button>
            <button class="btn btn-ghost" onclick="runEncode('hex-enc')">Hex Encode</button>
            <button class="btn btn-ghost" onclick="runEncode('jwt-decode')">JWT Inspect</button>
            <button class="btn btn-ghost" onclick="runEncode('uuid')">Generate UUIDv4</button>
          </div>
          <div class="terminal-out" id="util-out">Output buffer ready.</div>
          <div id="qr-img-wrap" style="margin-top:8px;"></div>
        </div>
      </section>
    </div>
  </main>
  <div id="toast"></div>
<script>
const KIT_TOKEN = "__KIT_SESSION_TOKEN__";
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => { t.style.display = 'none'; }, 2600);
}
function switchPanel(id, btn) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  const target = document.getElementById('panel-' + id);
  if (target) target.classList.add('active');
  if (btn) btn.classList.add('active');
  document.getElementById('breadcrumb').textContent = 'kit / studio / ' + id;
}
function filterNav(q) {
  const query = q.toLowerCase().trim();
  document.querySelectorAll('#nav-list .nav-item').forEach(btn => {
    btn.style.display = btn.textContent.toLowerCase().includes(query) ? 'flex' : 'none';
  });
}
document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault();
    document.getElementById('nav-filter').focus();
  }
});
function copyText(elId, isInput) {
  const el = document.getElementById(elId);
  navigator.clipboard.writeText((isInput ? el.value : el.textContent) || '');
  showToast('Copied to clipboard');
}
async function api(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Kit-Token': KIT_TOKEN },
    body: JSON.stringify(body || {})
  });
  return await res.json();
}
async function openDownloads() { await api('/api/open-downloads', {}); showToast('Opened downloads folder'); }
async function runDownload() {
  const url = document.getElementById('dl-url').value.trim();
  if (!url) { showToast('Enter a URL first'); return; }
  const quality = document.getElementById('dl-quality').value;
  const audio_only = document.getElementById('dl-mode').value === 'audio';
  const clip = document.getElementById('dl-clip').value.trim() || null;
  const out = document.getElementById('dl-out');
  const btn = document.getElementById('dl-btn');
  btn.disabled = true;
  out.textContent = 'Running yt-dlp stream extraction...';
  try {
    const data = await api('/api/dl', { url, quality, audio_only, clip });
    out.textContent = data.error ? ('Error: ' + data.error) : ('Completed: ' + (data.title || url) + '\\nOutput: ' + data.output_dir);
  } catch (e) { out.textContent = 'Error: ' + e; } finally { btn.disabled = false; }
}
async function runAudio() {
  const source = document.getElementById('audio-src').value.trim();
  if (!source) { showToast('Enter a file path or URL'); return; }
  const format = document.getElementById('audio-fmt').value;
  const bitrate = document.getElementById('audio-br').value;
  const normalize = document.getElementById('audio-norm').value === 'true';
  const out = document.getElementById('audio-out');
  const btn = document.getElementById('audio-btn');
  btn.disabled = true;
  out.textContent = 'Extracting and processing audio stream...';
  try {
    const data = await api('/api/audio', { source, format, bitrate, normalize });
    out.textContent = data.error ? ('Error: ' + data.error) : ('Saved audio output:\\n' + data.output);
  } catch (e) { out.textContent = 'Error: ' + e; } finally { btn.disabled = false; }
}
async function runSilence() {
  const input = document.getElementById('sil-input').value.trim();
  if (!input) { showToast('Enter an input file path'); return; }
  const threshold_db = parseInt(document.getElementById('sil-db').value || '-38', 10);
  const min_silence = parseFloat(document.getElementById('sil-dur').value || '0.35');
  const out = document.getElementById('sil-out');
  const btn = document.getElementById('sil-btn');
  btn.disabled = true;
  out.textContent = 'Scanning and stripping silence intervals via FFmpeg...';
  try {
    const data = await api('/api/silence', { input, threshold_db, min_silence });
    out.textContent = data.error ? ('Error: ' + data.error) : ('Saved silence-trimmed media:\\n' + data.output);
  } catch (e) { out.textContent = 'Error: ' + e; } finally { btn.disabled = false; }
}
async function runPass() {
  const passphrase = document.getElementById('pass-mode').value === 'passphrase';
  const length = parseInt(document.getElementById('pass-len').value || '24', 10);
  const use_symbols = document.getElementById('pass-sym').value === 'true';
  const count = parseInt(document.getElementById('pass-count').value || '5', 10);
  const out = document.getElementById('pass-out');
  const data = await api('/api/pass', { length, use_symbols, passphrase, words: length, count });
  out.textContent = data.error ? ('Error: ' + data.error) : (data.items.join('\\n') + '\\n\\n[Entropy: ~' + data.entropy_bits + ' bits | CSPRNG: os.urandom]');
}
async function runCrypt() {
  const mode = document.getElementById('crypt-op').value;
  const path = document.getElementById('crypt-path').value.trim();
  const password = document.getElementById('crypt-pw').value;
  if (!path || !password) { showToast('Provide both file path and passphrase'); return; }
  const out = document.getElementById('crypt-out');
  const btn = document.getElementById('crypt-btn');
  btn.disabled = true;
  out.textContent = 'Deriving 256-bit key (600,000 PBKDF2 iterations)...';
  try {
    const data = await api('/api/crypt', { mode, path, password });
    out.textContent = data.error ? ('Error: ' + data.error) : ('Success (' + mode + '):\\n' + data.output);
  } catch (e) { out.textContent = 'Error: ' + e; } finally { btn.disabled = false; }
}
async function runMeta(strip) {
  const path = document.getElementById('meta-path').value.trim();
  if (!path) { showToast('Enter a file path first'); return; }
  const out = document.getElementById('meta-out');
  out.textContent = 'Reading file metadata...';
  const data = await api('/api/meta', { path, strip });
  if (data.error) { out.textContent = 'Error: ' + data.error; return; }
  const lines = Object.entries(data.metadata || {}).map(([k, v]) => k.padEnd(22, ' ') + ': ' + v);
  if (data.stripped_output) lines.push('\\nStripped clean file saved to: ' + data.stripped_output);
  out.textContent = lines.length ? lines.join('\\n') : 'No embedded metadata tags present.';
}
async function runShred() {
  const path = document.getElementById('shred-path').value.trim();
  const passes = parseInt(document.getElementById('shred-passes').value || '3', 10);
  if (!path) { showToast('Enter a file path to shred'); return; }
  if (!confirm('Permanently overwrite and destroy ' + path + '? This cannot be undone.')) return;
  const out = document.getElementById('shred-out');
  out.textContent = 'Overwriting blocks and flushing to disk...';
  const data = await api('/api/shred', { path, passes });
  out.textContent = data.error ? ('Error: ' + data.error) : ('Destroyed: ' + data.shredded + ' (' + data.bytes + ' bytes, ' + data.passes + ' passes)');
}
async function runSpeedTest() {
  const out = document.getElementById('ns-out');
  const btn = document.getElementById('ns-btn');
  btn.disabled = true;
  out.textContent = 'Running 4-thread edge benchmark...';
  try {
    const data = await api('/api/ns', { size_mb: 10 });
    if (data.error) out.textContent = 'Error: ' + data.error;
    else {
      document.getElementById('ns-ping').textContent = data.ping_ms + ' ms';
      document.getElementById('ns-jitter').textContent = data.jitter_ms + ' ms';
      document.getElementById('ns-down').textContent = data.download_mbps + ' Mbps';
      document.getElementById('ns-up').textContent = data.upload_mbps + ' Mbps';
      out.textContent = 'Benchmark complete.';
    }
  } catch (e) { out.textContent = 'Error: ' + e; } finally { btn.disabled = false; }
}
async function runOcrClip() {
  const out = document.getElementById('ocr-out');
  out.value = 'Reading image from Windows clipboard...';
  const data = await api('/api/textract', { clip: true });
  out.value = data.error ? ('Error: ' + data.error) : (data.text || '[No text detected]');
}
async function runOcrFile() {
  const fileInput = document.getElementById('ocr-file');
  const out = document.getElementById('ocr-out');
  if (!fileInput.files.length) { showToast('Select an image or PDF file'); return; }
  const file = fileInput.files[0];
  out.value = 'Extracting text from ' + file.name + '...';
  const reader = new FileReader();
  reader.onload = async () => {
    const b64 = reader.result.split(',')[1];
    const data = await api('/api/textract', { filename: file.name, data_b64: b64 });
    out.value = data.error ? ('Error: ' + data.error) : (data.text || '[No text detected]');
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
    img.style.maxWidth = '168px';
    img.style.border = '1px solid #26262c';
    img.style.borderRadius = '4px';
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
                res = download_url(url=str(body.get("url", "")), quality=str(body.get("quality", "720")), audio_only=bool(body.get("audio_only", False)), clip=body.get("clip"), open_folder=True)
                self._send_json(res)
            elif self.path == "/api/audio":
                res = run_audio_extract(source=str(body.get("source", "")), audio_format=str(body.get("format", "mp3")), bitrate=str(body.get("bitrate", "320k")), normalize=bool(body.get("normalize", False)))
                self._send_json(res)
            elif self.path == "/api/silence":
                out = run_silence_strip(input_path=Path(str(body.get("input", ""))), threshold_db=int(body.get("threshold_db", -38)), min_silence=float(body.get("min_silence", 0.35)))
                self._send_json({"output": str(out)})
            elif self.path == "/api/pass":
                res = generate_passwords(length=int(body.get("length", 24)), use_symbols=bool(body.get("use_symbols", True)), passphrase=bool(body.get("passphrase", False)), words=int(body.get("words", 5)), count=int(body.get("count", 5)))
                self._send_json(res)
            elif self.path == "/api/crypt":
                mode = str(body.get("mode", "encrypt"))
                target = Path(str(body.get("path", "")))
                pw = str(body.get("password", ""))
                out_p = decrypt_file(target, password=pw) if mode == "decrypt" else encrypt_file(target, password=pw)
                self._send_json({"output": str(out_p)})
            elif self.path == "/api/meta":
                res = inspect_or_strip_meta(input_path=Path(str(body.get("path", ""))), strip=bool(body.get("strip", False)), as_json=True)
                self._send_json(res)
            elif self.path == "/api/shred":
                res = shred_file(target_path=Path(str(body.get("path", ""))), passes=int(body.get("passes", 3)))
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
    print(f"KIT // WORKSTATION running at: {url} (CSRF & DNS-Rebinding protection active)")
    print("Press Ctrl+C in this terminal to stop the server.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Kit Workstation.")
        server.server_close()
