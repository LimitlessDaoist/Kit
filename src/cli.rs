use clap::{Args, Parser, Subcommand, ValueEnum};
use clap_complete::{generate, Shell};
use std::io;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    name = "kit",
    version,
    about = "Kit: Fast Hybrid (Rust + Python) All-in-One CLI Toolkit",
    long_about = "Kit combines native Rust speed for file/crypto/JSON tasks with Python's media, image, and PDF ecosystem (yt-dlp, ffmpeg, Pillow, pypdf)."
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Download video or audio from YouTube, Vimeo, Twitch, TikTok, X, and 1000+ sites (via yt-dlp)
    Dl(DlArgs),

    /// Convert, compress, trim, or extract audio/GIFs from local video/audio files (via ffmpeg)
    Media(MediaArgs),

    /// Resize, convert format (WebP/PNG/JPG), compress, or strip EXIF metadata from images
    Img(ImgArgs),

    /// Merge, split, extract text, or inspect PDF documents
    Pdf(PdfArgs),

    /// Generate terminal ASCII QR codes or save QR images (URLs, text, Wi-Fi)
    Qr(QrArgs),

    /// [Native Rust] Compute fast cryptographic hashes (BLAKE3, SHA256, SHA512, MD5)
    Hash(HashArgs),

    /// [Native Rust] Find duplicate files across a directory using parallel size + BLAKE3 hashing
    Dedup(DedupArgs),

    /// [Native Rust] Encode/decode Base64, Hex, URL strings, inspect JWTs, or generate UUIDs
    Encode(EncodeArgs),

    /// [Native Rust] Format, minify, validate, or query JSON files and stdin streams
    Json(JsonArgs),

    /// [Native Rust] Scan and clean heavy developer build caches (target/, node_modules/, __pycache__)
    Clean(CleanArgs),

    /// Check installed runtime dependencies (Rust, Python 3, yt-dlp, ffmpeg, Pillow, pypdf)
    Doctor,

    /// Generate shell autocompletion scripts (bash, zsh, fish, powershell)
    Completions {
        #[arg(value_enum)]
        shell: Shell,
    },
}

#[derive(Args, Debug)]
pub struct DlArgs {
    /// Video or playlist URL to download
    pub url: String,

    /// Extract audio only (mp3, m4a, flac, wav)
    #[arg(short = 'x', long)]
    pub audio_only: bool,

    /// Audio format when using --audio-only
    #[arg(long, default_value = "mp3")]
    pub audio_format: String,

    /// Maximum video resolution (e.g., 2160, 1080, 720, 480, best)
    #[arg(short, long, default_value = "1080")]
    pub quality: String,

    /// Output directory for downloaded files
    #[arg(short, long, default_value = "./downloads")]
    pub output_dir: PathBuf,

    /// Optional time clip range, e.g. "00:01:15-00:02:45"
    #[arg(long)]
    pub clip: Option<String>,

    /// Download subtitles if available
    #[arg(long)]
    pub subs: bool,

    /// Simulate and print metadata JSON without downloading
    #[arg(long)]
    pub info_only: bool,
}

#[derive(Args, Debug)]
pub struct MediaArgs {
    /// Input media file path
    pub input: PathBuf,

    /// Output file path (format inferred from extension: .mp4, .mp3, .gif, .webm)
    #[arg(short, long)]
    pub output: PathBuf,

    /// Trim start timestamp (e.g., 00:00:10)
    #[arg(long)]
    pub start: Option<String>,

    /// Trim end timestamp (e.g., 00:00:35)
    #[arg(long)]
    pub end: Option<String>,

    /// Video CRF compression level (18 = near-lossless, 23 = default, 28 = compact)
    #[arg(long, default_value_t = 23)]
    pub crf: u8,
}

#[derive(Args, Debug)]
pub struct ImgArgs {
    /// Input image file path
    pub input: PathBuf,

    /// Output image file path (or auto-derived if omitted)
    #[arg(short, long)]
    pub output: Option<PathBuf>,

    /// Target format (webp, png, jpg, ico)
    #[arg(short, long)]
    pub format: Option<String>,

    /// Resize dimensions such as "1280x720" or max width "1280"
    #[arg(short, long)]
    pub resize: Option<String>,

    /// Compression quality (1-100)
    #[arg(short, long, default_value_t = 85)]
    pub quality: u8,

    /// Strip EXIF camera/GPS metadata for privacy
    #[arg(long)]
    pub strip_exif: bool,
}

#[derive(Args, Debug)]
pub struct PdfArgs {
    #[command(subcommand)]
    pub action: PdfAction,
}

#[derive(Subcommand, Debug)]
pub enum PdfAction {
    /// Merge multiple PDF files into one
    Merge {
        /// Output merged PDF path
        #[arg(short, long)]
        output: PathBuf,
        /// Input PDF files in order
        #[arg(required = true)]
        inputs: Vec<PathBuf>,
    },
    /// Split or extract a page range (e.g., "1-5,8") from a PDF
    Split {
        /// Input PDF file
        input: PathBuf,
        /// Page range string (1-indexed, e.g., "1-3,5")
        #[arg(short, long)]
        pages: String,
        /// Output PDF file
        #[arg(short, long)]
        output: PathBuf,
    },
    /// Extract plain text from a PDF file
    Text {
        /// Input PDF file
        input: PathBuf,
        /// Optional output .txt file (prints to stdout if omitted)
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
}

#[derive(Args, Debug)]
pub struct QrArgs {
    /// Text, URL, or payload to encode as QR code
    pub payload: String,

    /// Optional image file output (.png or .svg). Renders ASCII QR in terminal if omitted.
    #[arg(short, long)]
    pub output: Option<PathBuf>,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
pub enum HashAlgo {
    Blake3,
    Sha256,
    Sha512,
    Md5,
}

#[derive(Args, Debug)]
pub struct HashArgs {
    /// File(s) to hash
    #[arg(required = true)]
    pub files: Vec<PathBuf>,

    /// Hash algorithm
    #[arg(short, long, value_enum, default_value_t = HashAlgo::Blake3)]
    pub algo: HashAlgo,

    /// Verify against an expected hex digest
    #[arg(short, long)]
    pub check: Option<String>,
}

#[derive(Args, Debug)]
pub struct DedupArgs {
    /// Directory to scan for duplicate files
    #[arg(default_value = ".")]
    pub dir: PathBuf,

    /// Minimum file size in bytes to consider
    #[arg(long, default_value_t = 1024)]
    pub min_size: u64,

    /// Output results as JSON
    #[arg(long)]
    pub json: bool,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
pub enum EncodeMode {
    Base64Enc,
    Base64Dec,
    HexEnc,
    HexDec,
    JwtDecode,
    Uuid,
}

#[derive(Args, Debug)]
pub struct EncodeArgs {
    /// Operation mode
    #[arg(value_enum)]
    pub mode: EncodeMode,

    /// Input text (optional for `uuid`)
    pub input: Option<String>,
}

#[derive(Args, Debug)]
pub struct JsonArgs {
    /// Input JSON file (use "-" for stdin)
    #[arg(default_value = "-")]
    pub input: String,

    /// Minify instead of pretty-printing
    #[arg(short, long)]
    pub minify: bool,

    /// Dot-separated key path to extract (e.g. "data.items.0.name")
    #[arg(short, long)]
    pub query: Option<String>,
}

#[derive(Args, Debug)]
pub struct CleanArgs {
    /// Root directory to scan for build/cache artifacts
    #[arg(default_value = ".")]
    pub dir: PathBuf,

    /// Actually delete matched artifact directories (dry-run by default)
    #[arg(long)]
    pub apply: bool,
}

pub fn print_completions(shell: Shell) {
    use clap::CommandFactory;
    let mut cmd = Cli::command();
    generate(shell, &mut cmd, "kit", &mut io::stdout());
}
