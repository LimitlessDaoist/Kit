from __future__ import annotations
import argparse, sys
from pathlib import Path
from typing import List, Optional
from kit_py.auto_bootstrap import DEFAULT_DL_DIR

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kit", description="Kit: Fast Hybrid (Rust + Python) All-in-One CLI & Web Workstation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dl = sub.add_parser("dl", help="Download video or audio by URL (via yt-dlp)")
    p_dl.add_argument("url")
    p_dl.add_argument("-x", "--audio-only", action="store_true")
    p_dl.add_argument("--audio-format", default="mp3")
    p_dl.add_argument("-q", "--quality", default="1080")
    p_dl.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_DL_DIR)
    p_dl.add_argument("--clip")
    p_dl.add_argument("--subs", action="store_true")
    p_dl.add_argument("--info-only", action="store_true")

    p_aud = sub.add_parser("audio", help="Extract high-bitrate audio from local video or URL with optional loudness normalization")
    p_aud.add_argument("source")
    p_aud.add_argument("-o", "--output", type=Path)
    p_aud.add_argument("-f", "--format", default="mp3", choices=["mp3", "flac", "m4a", "wav", "opus"])
    p_aud.add_argument("-b", "--bitrate", default="320k", choices=["96k", "128k", "192k", "256k", "320k"])
    p_aud.add_argument("-n", "--normalize", action="store_true")

    p_sil = sub.add_parser("silence", help="Automatically detect and strip silence/dead air from audio or video")
    p_sil.add_argument("input", type=Path)
    p_sil.add_argument("-o", "--output", type=Path)
    p_sil.add_argument("-t", "--threshold-db", type=int, default=-38)
    p_sil.add_argument("-d", "--min-silence", type=float, default=0.35)

    p_pass = sub.add_parser("pass", help="Generate cryptographically secure passwords or passphrases")
    p_pass.add_argument("length", type=int, nargs="?", default=20)
    p_pass.add_argument("--no-symbols", action="store_true")
    p_pass.add_argument("-p", "--passphrase", action="store_true")
    p_pass.add_argument("-w", "--words", type=int, default=5)
    p_pass.add_argument("-c", "--count", type=int, default=1)
    p_pass.add_argument("--copy", action="store_true")

    p_enc_file = sub.add_parser("encrypt", help="Encrypt a file with AES-256-GCM (600,000 PBKDF2 iterations)")
    p_enc_file.add_argument("input", type=Path)
    p_enc_file.add_argument("-o", "--output", type=Path)
    p_enc_file.add_argument("-p", "--password")

    p_dec_file = sub.add_parser("decrypt", help="Decrypt a .kitenc AES-256-GCM encrypted file")
    p_dec_file.add_argument("input", type=Path)
    p_dec_file.add_argument("-o", "--output", type=Path)
    p_dec_file.add_argument("-p", "--password")

    p_shred = sub.add_parser("shred", help="Securely overwrite and permanently destroy a file")
    p_shred.add_argument("target", type=Path)
    p_shred.add_argument("-p", "--passes", type=int, default=3)

    p_meta = sub.add_parser("meta", help="Inspect or strip hidden EXIF, GPS, and PDF metadata")
    p_meta.add_argument("input", type=Path)
    p_meta.add_argument("-s", "--strip", action="store_true")
    p_meta.add_argument("-o", "--output", type=Path)
    p_meta.add_argument("--json", action="store_true")

    p_ns = sub.add_parser("ns", help="Run a fast network speed test")
    p_ns.add_argument("-s", "--size-mb", type=int, default=15)
    p_ns.add_argument("--json", action="store_true")

    p_tx = sub.add_parser("textract", help="Extract text (OCR) from images, PDFs, or clipboard screenshots")
    p_tx.add_argument("input", type=Path, nargs="?")
    p_tx.add_argument("-c", "--clip", action="store_true")
    p_tx.add_argument("-o", "--output", type=Path)
    p_tx.add_argument("--copy", action="store_true")

    p_ui = sub.add_parser("ui", help="Open the Kit Workstation Web UI in your browser")
    p_ui.add_argument("-p", "--port", type=int, default=8420)
    p_ui.add_argument("--no-open", action="store_true")

    p_media = sub.add_parser("media", help="Convert, compress, trim, or extract GIF/audio via FFmpeg")
    p_media.add_argument("input", type=Path)
    p_media.add_argument("-o", "--output", type=Path, required=True)
    p_media.add_argument("--start")
    p_media.add_argument("--end")
    p_media.add_argument("--crf", type=int, default=23)

    p_img = sub.add_parser("img", help="Convert, resize, compress, or strip EXIF from images")
    p_img.add_argument("input", type=Path)
    p_img.add_argument("-o", "--output", type=Path)
    p_img.add_argument("-f", "--format")
    p_img.add_argument("-r", "--resize")
    p_img.add_argument("-q", "--quality", type=int, default=85)
    p_img.add_argument("--strip-exif", action="store_true")

    p_pdf = sub.add_parser("pdf", help="Merge, split, or extract text from PDFs")
    pdf_sub = p_pdf.add_subparsers(dest="pdf_action", required=True)
    p_pdf_merge = pdf_sub.add_parser("merge")
    p_pdf_merge.add_argument("-o", "--output", type=Path, required=True)
    p_pdf_merge.add_argument("inputs", type=Path, nargs="+")
    p_pdf_split = pdf_sub.add_parser("split")
    p_pdf_split.add_argument("input", type=Path)
    p_pdf_split.add_argument("-p", "--pages", required=True)
    p_pdf_split.add_argument("-o", "--output", type=Path, required=True)
    p_pdf_text = pdf_sub.add_parser("text")
    p_pdf_text.add_argument("input", type=Path)
    p_pdf_text.add_argument("-o", "--output", type=Path)

    p_qr = sub.add_parser("qr", help="Generate terminal ASCII QR code or save PNG image")
    p_qr.add_argument("payload")
    p_qr.add_argument("-o", "--output", type=Path)

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
    cmd = args.command
    try:
        if cmd == "setup":
            from kit_py.auto_bootstrap import ensure_dependencies
            ensure_dependencies(force=True)
        elif cmd == "dl":
            from kit_py.media_dl import download_url
            download_url(args.url, args.output_dir, args.quality, args.audio_only, args.audio_format, args.clip, args.subs, args.info_only)
        elif cmd == "audio":
            from kit_py.audio_tools import run_audio_extract
            run_audio_extract(args.source, args.output, args.format, args.bitrate, args.normalize)
        elif cmd == "silence":
            from kit_py.audio_tools import run_silence_strip
            run_silence_strip(args.input, args.output, args.threshold_db, args.min_silence)
        elif cmd in {"pass", "encrypt", "decrypt", "shred"}:
            from kit_py.security_tools import decrypt_file, encrypt_file, generate_passwords, shred_file
            if cmd == "pass":
                generate_passwords(args.length, not args.no_symbols, args.passphrase, args.words, args.count, args.copy)
            elif cmd == "encrypt":
                encrypt_file(args.input, args.output, args.password)
            elif cmd == "decrypt":
                decrypt_file(args.input, args.output, args.password)
            else:
                shred_file(args.target, args.passes)
        elif cmd == "meta":
            from kit_py.meta_tools import inspect_or_strip_meta
            inspect_or_strip_meta(args.input, args.strip, args.output, args.json)
        elif cmd == "ns":
            from kit_py.net_speed import run_speedtest
            run_speedtest(size_mb=args.size_mb, as_json=args.json)
        elif cmd == "textract":
            from kit_py.textract_tools import run_textract
            run_textract(args.input, args.clip, args.output, args.copy)
        elif cmd == "ui":
            from kit_py.web_ui import launch_ui
            launch_ui(port=args.port, open_browser=not args.no_open)
        elif cmd == "media":
            from kit_py.media_conv import convert_media
            convert_media(args.input, args.output, start=args.start, end=args.end, crf=args.crf)
        elif cmd == "img":
            from kit_py.image_tools import process_image
            process_image(args.input, output_path=args.output, target_format=args.format, resize_spec=args.resize, quality=args.quality, strip_exif=args.strip_exif)
        elif cmd == "pdf":
            from kit_py.pdf_tools import extract_pdf_text, merge_pdfs, split_pdf
            if args.pdf_action == "merge":
                merge_pdfs(args.inputs, args.output)
            elif args.pdf_action == "split":
                split_pdf(args.input, args.pages, args.output)
            elif args.pdf_action == "text":
                extract_pdf_text(args.input, args.output)
        elif cmd == "qr":
            from kit_py.qr_tools import render_qr
            render_qr(args.payload, args.output)
        elif cmd in {"hash", "dedup", "encode", "json", "doctor"}:
            from kit_py.native_fallback import run_dedup, run_doctor, run_encode, run_hash, run_json
            if cmd == "hash":
                run_hash(args.files, algo=args.algo, check=args.check)
            elif cmd == "dedup":
                run_dedup(args.dir, min_size=args.min_size, as_json=args.json)
            elif cmd == "encode":
                run_encode(args.mode, args.input)
            elif cmd == "json":
                run_json(args.input, minify=args.minify, query=args.query)
            else:
                run_doctor()
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
