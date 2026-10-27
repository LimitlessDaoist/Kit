from __future__ import annotations
import argparse, sys
from pathlib import Path
from typing import List, Optional
from kit_py.auto_bootstrap import ensure_dependencies
from kit_py.image_tools import process_image
from kit_py.media_conv import convert_media
from kit_py.media_dl import DEFAULT_DL_DIR, download_url
from kit_py.native_fallback import run_dedup, run_doctor, run_encode, run_hash, run_json
from kit_py.net_speed import run_speedtest
from kit_py.pdf_tools import extract_pdf_text, merge_pdfs, split_pdf
from kit_py.qr_tools import render_qr
from kit_py.textract_tools import run_textract
from kit_py.web_ui import launch_ui

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kit", description="Kit: Fast Hybrid (Rust + Python) All-in-One CLI & Web UI Toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dl = sub.add_parser("dl", help="Download video or audio by URL (via yt-dlp)")
    p_dl.add_argument("url", help="Video or playlist URL")
    p_dl.add_argument("-x", "--audio-only", action="store_true", help="Extract audio only")
    p_dl.add_argument("--audio-format", default="mp3", help="Audio codec (mp3, m4a, flac, wav)")
    p_dl.add_argument("-q", "--quality", default="1080", help="Max video height (2160, 1080, 720, best)")
    p_dl.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_DL_DIR, help="Output folder")
    p_dl.add_argument("--clip", help="Time range clip, e.g. 00:01:00-00:02:00")
    p_dl.add_argument("--subs", action="store_true", help="Download subtitles")
    p_dl.add_argument("--info-only", action="store_true", help="Print video metadata JSON without downloading")

    p_ns = sub.add_parser("ns", help="Run a fast network speed test (ping, jitter, download & upload Mbps)")
    p_ns.add_argument("-s", "--size-mb", type=int, default=15, help="Download payload size in MB (default: 15)")
    p_ns.add_argument("--json", action="store_true", help="Output speed test results as JSON")

    p_tx = sub.add_parser("textract", help="Extract text (OCR) from images, PDFs, or clipboard screenshots")
    p_tx.add_argument("input", type=Path, nargs="?", help="Image or PDF file path (omit if using --clip)")
    p_tx.add_argument("-c", "--clip", action="store_true", help="Extract text from image in system clipboard")
    p_tx.add_argument("-o", "--output", type=Path, help="Save extracted text to a file")
    p_tx.add_argument("--copy", action="store_true", help="Copy extracted text back to clipboard")

    p_ui = sub.add_parser("ui", help="Open the interactive Kit Web UI dashboard in your browser")
    p_ui.add_argument("-p", "--port", type=int, default=8420, help="Local port (default: 8420)")
    p_ui.add_argument("--no-open", action="store_true", help="Start server without opening browser automatically")

    p_media = sub.add_parser("media", help="Convert, compress, trim, or extract GIF/audio via FFmpeg")
    p_media.add_argument("input", type=Path, help="Input media file")
    p_media.add_argument("-o", "--output", type=Path, required=True, help="Output media file")
    p_media.add_argument("--start", help="Start timestamp")
    p_media.add_argument("--end", help="End timestamp")
    p_media.add_argument("--crf", type=int, default=23, help="H.264 CRF compression (18-28)")

    p_img = sub.add_parser("img", help="Convert, resize, compress, or strip EXIF from images")
    p_img.add_argument("input", type=Path, help="Input image path")
    p_img.add_argument("-o", "--output", type=Path, help="Output image path")
    p_img.add_argument("-f", "--format", help="Target format (webp, png, jpg, ico)")
    p_img.add_argument("-r", "--resize", help="Resize spec (e.g. 1280x720 or 1280)")
    p_img.add_argument("-q", "--quality", type=int, default=85, help="Compression quality (1-100)")
    p_img.add_argument("--strip-exif", action="store_true", help="Strip EXIF metadata")

    p_pdf = sub.add_parser("pdf", help="Merge, split, or extract text from PDFs")
    pdf_sub = p_pdf.add_subparsers(dest="pdf_action", required=True)
    p_pdf_merge = pdf_sub.add_parser("merge", help="Merge multiple PDFs into one")
    p_pdf_merge.add_argument("-o", "--output", type=Path, required=True)
    p_pdf_merge.add_argument("inputs", type=Path, nargs="+")
    p_pdf_split = pdf_sub.add_parser("split", help="Extract page ranges from a PDF")
    p_pdf_split.add_argument("input", type=Path)
    p_pdf_split.add_argument("-p", "--pages", required=True)
    p_pdf_split.add_argument("-o", "--output", type=Path, required=True)
    p_pdf_text = pdf_sub.add_parser("text", help="Extract text from a PDF")
    p_pdf_text.add_argument("input", type=Path)
    p_pdf_text.add_argument("-o", "--output", type=Path)

    p_qr = sub.add_parser("qr", help="Generate terminal ASCII QR code or save PNG image")
    p_qr.add_argument("payload", help="URL or text to encode")
    p_qr.add_argument("-o", "--output", type=Path, help="Optional PNG file output path")

    p_hash = sub.add_parser("hash", help="Compute cryptographic file checksums")
    p_hash.add_argument("files", type=Path, nargs="+")
    p_hash.add_argument("-a", "--algo", choices=["blake3", "sha256", "sha512", "md5"], default="blake3")
    p_hash.add_argument("-c", "--check")

    p_dedup = sub.add_parser("dedup", help="Find duplicate files by size + content hash")
    p_dedup.add_argument("dir", type=Path, nargs="?", default=Path("."))
    p_dedup.add_argument("--min-size", type=int, default=1024)
    p_dedup.add_argument("--json", action="store_true")

    p_enc = sub.add_parser("encode", help="Base64/Hex encode & decode, JWT inspect, or UUIDv4 generation")
    p_enc.add_argument("mode", choices=["base64-enc", "base64-dec", "hex-enc", "hex-dec", "jwt-decode", "uuid"])
    p_enc.add_argument("input", nargs="?")

    p_json = sub.add_parser("json", help="Format, minify, or query JSON files")
    p_json.add_argument("input", nargs="?", default="-")
    p_json.add_argument("-m", "--minify", action="store_true")
    p_json.add_argument("-q", "--query")

    sub.add_parser("doctor", help="Check installed system dependencies")
    sub.add_parser("setup", help="Auto-install or upgrade all required Python libraries")
    return parser

def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "setup":
        ensure_dependencies(force=True)
    elif args.command == "dl":
        download_url(args.url, args.output_dir, args.quality, args.audio_only, args.audio_format, args.clip, args.subs, args.info_only)
    elif args.command == "ns":
        run_speedtest(size_mb=args.size_mb, as_json=args.json)
    elif args.command == "textract":
        run_textract(input_path=args.input, from_clipboard=args.clip, output_path=args.output, copy_result=args.copy)
    elif args.command == "ui":
        launch_ui(port=args.port, open_browser=not args.no_open)
    elif args.command == "media":
        convert_media(args.input, args.output, start=args.start, end=args.end, crf=args.crf)
    elif args.command == "img":
        process_image(args.input, output_path=args.output, target_format=args.format, resize_spec=args.resize, quality=args.quality, strip_exif=args.strip_exif)
    elif args.command == "pdf":
        if args.pdf_action == "merge":
            merge_pdfs(args.inputs, args.output)
        elif args.pdf_action == "split":
            split_pdf(args.input, args.pages, args.output)
        elif args.pdf_action == "text":
            extract_pdf_text(args.input, args.output)
    elif args.command == "qr":
        render_qr(args.payload, args.output)
    elif args.command == "hash":
        run_hash(args.files, algo=args.algo, check=args.check)
    elif args.command == "dedup":
        run_dedup(args.dir, min_size=args.min_size, as_json=args.json)
    elif args.command == "encode":
        run_encode(args.mode, args.input)
    elif args.command == "json":
        run_json(args.input, minify=args.minify, query=args.query)
    elif args.command == "doctor":
        run_doctor()
    return 0

if __name__ == "__main__":
    sys.exit(main())
