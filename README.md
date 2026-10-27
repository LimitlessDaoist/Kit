# Kit (`kit`) — Fast Hybrid Rust + Python CLI Toolkit

**Kit** is a blazing-fast command-line swiss-army knife that combines **Rust's native zero-overhead performance** with **Python's rich media and document ecosystem**.

## Why Rust + Python Together?

| Layer | Technology | What It Handles | Why It Fits |
| :--- | :--- | :--- | :--- |
| **CLI Router & Native Core** | **Rust** (`clap`, `rayon`, `blake3`, `serde_json`) | Instant `<2ms` startup, shell completions, parallel file hashing, duplicate file scanning, build cache cleaning, Base64/Hex/JWT encoding, and JSON querying | Native multi-threaded speed with zero interpreter overhead for everyday file and developer operations |
| **Media & Document Engine** | **Python** (`yt-dlp`, `ffmpeg`, `Pillow`, `pypdf`) | Video/audio downloading from 1,000+ sites, media conversion/clipping, image resizing & EXIF stripping, PDF merging/splitting, and QR code generation | Direct access to actively maintained libraries (`yt-dlp`, `Pillow`, `pypdf`) without reinventing extractors |

> **Zero-Friction Fallback**: The root `./kit` launcher automatically runs the compiled `./target/release/kit` Rust binary if present, or seamlessly falls back to the pure-Python `kit_py` runner so you can use every command immediately after cloning.

## Included Tools & Commands

### 1. Media & Video Tools
- **`kit dl <url>`** — Download videos or extract audio from YouTube, Twitch, TikTok, Vimeo, X, and 1,000+ sites (powered by `yt-dlp` + `ffmpeg`).
  ```bash
  # Download up to 1080p MP4 into ./downloads
  ./kit dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -q 1080

  # Extract high-quality MP3 audio only
  ./kit dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -x --audio-format mp3

  # Download only a specific timestamp clip (01:15 to 02:30) with subtitles
  ./kit dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --clip "00:01:15-00:02:30" --subs
  ```
- **`kit media <input> -o <output>`** — Convert video/audio formats, compress H.264 video (`--crf`), trim timestamps, or turn video clips into optimized GIFs.
  ```bash
  # Convert a video clip into an optimized GIF
  ./kit media demo.mp4 -o demo.gif --start 00:00:03 --end 00:00:09

  # Compress a large recording with CRF 26
  ./kit media raw_capture.mov -o compressed.mp4 --crf 26
  ```

### 2. Image & Document Tools
- **`kit img <input>`** — Convert images (`webp`, `png`, `jpg`, `ico`), resize preserving aspect ratio, compress, and strip camera/GPS EXIF metadata.
  ```bash
  # Convert PNG to WebP at 80% quality, resized to 1280px wide, with EXIF stripped
  ./kit img photo.png -f webp -r 1280 -q 80 --strip-exif
  ```
- **`kit pdf <merge|split|text>`** — Merge multiple PDFs, extract page ranges (`1-3,5`), or dump plain text.
  ```bash
  ./kit pdf merge -o combined.pdf part1.pdf part2.pdf
  ./kit pdf split combined.pdf --pages "1-3,5" -o excerpt.pdf
  ./kit pdf text combined.pdf -o extracted.txt
  ```
- **`kit qr <payload>`** — Render an instant scannable ASCII QR code in your terminal or save a high-contrast `.png`.
  ```bash
  ./kit qr "https://github.com/your-org/kit"
  ./kit qr "WIFI:S:MyNetwork;T:WPA;P:secret;;" -o wifi_qr.png
  ```

### 3. Native Rust File, Crypto & Dev Tools
- **`kit hash <files...>`** — Compute BLAKE3, SHA-256, SHA-512, or MD5 checksums and verify against expected digests.
  ```bash
  ./kit hash installer.iso --algo sha256 --check 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
  ```
- **`kit dedup <dir>`** — Parallel two-pass duplicate file finder (groups by exact byte size first, then hashes only candidate collisions with BLAKE3).
  ```bash
  ./kit dedup ~/Downloads --min-size 10240
  ```
- **`kit clean <dir>`** — Find and reclaim disk space from heavy build directories (`node_modules`, `target`, `__pycache__`, `.next`, `dist`).
  ```bash
  ./kit clean ~/Projects          # Dry-run summary
  ./kit clean ~/Projects --apply  # Delete matched cache directories
  ```
- **`kit encode <mode> [input]`** — Encode/decode Base64 & Hex, inspect JWT headers/payloads without sending tokens to external websites, or generate UUIDv4s.
  ```bash
  ./kit encode base64-enc "hello world"
  ./kit encode jwt-decode "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig"
  ./kit encode uuid
  ```
- **`kit json <file>`** — Pretty-print, minify, validate, and query JSON keys via dot-notation (`-q data.items.0.id`).
- **`kit doctor`** — Verify that `cargo`, `python3`, `ffmpeg`, `yt-dlp`, and `git` are installed and ready.

## Project Layout

```text
kit/
├── Cargo.toml                 # Rust crate manifest (`kit` native binary)
├── pyproject.toml             # Python package manifest (`kit-py` companion engine)
├── Makefile                   # One-command setup, build, test, and install targets
├── kit                        # Smart launcher (runs Rust binary or Python fallback)
├── src/                       # Rust CLI source
│   ├── main.rs                # Entrypoint & command dispatcher
│   ├── cli.rs                 # Clap derive subcommands & flags
│   ├── bridge.rs              # Seamless Rust -> Python subprocess bridge
│   └── commands/              # Native Rust commands
│       ├── hash.rs            # BLAKE3 / SHA2 / MD5 file hashing
│       ├── dedup.rs           # Rayon parallel duplicate file detector
│       ├── clean.rs           # Build artifact scanner & cleaner
│       ├── encode.rs          # Base64, Hex, JWT inspector, UUIDv4
│       ├── json_fmt.rs        # JSON formatter & dot-path query tool
│       └── doctor.rs          # Dependency health check
├── python/
│   └── kit_py/                # Python media & document toolkit
│       ├── cli.py             # Python CLI dispatcher
│       ├── media_dl.py        # yt-dlp video/audio downloader & clipper
│       ├── media_conv.py      # FFmpeg format converter & GIF generator
│       ├── image_tools.py     # Pillow image converter, resizer & EXIF stripper
│       ├── pdf_tools.py       # pypdf merge, split & text extractor
│       ├── qr_tools.py        # Terminal ASCII & PNG QR code generator
│       └── native_fallback.py # Pure-Python fallback for native commands
└── tests/
    └── test_kit.py            # Automated unit tests for all toolkit modules
```

## Quick Start

```bash
# 1. Install Python dependencies (yt-dlp, Pillow, pypdf)
make setup

# 2. Run immediately via the smart launcher (even before building Rust!)
./kit doctor
./kit qr "https://example.com"

# 3. Compile the native Rust binary (requires Rust / Cargo)
make build

# 4. Run the test suite
make test
```
