mod bridge;
mod cli;
mod commands;

use anyhow::Result;
use clap::Parser;
use cli::{Cli, Commands};

fn main() -> Result<()> {
    let args = Cli::parse();

    match args.command {
        // --- Native Rust Commands (Zero-overhead instant execution) ---
        Commands::Hash(cmd) => commands::hash::run(cmd),
        Commands::Dedup(cmd) => commands::dedup::run(cmd),
        Commands::Encode(cmd) => commands::encode::run(cmd),
        Commands::Json(cmd) => commands::json_fmt::run(cmd),
        Commands::Clean(cmd) => commands::clean::run(cmd),
        Commands::Doctor => commands::doctor::run(),
        Commands::Completions { shell } => {
            cli::print_completions(shell);
            Ok(())
        }

        // --- Python-Bridged Rich Ecosystem Commands (yt-dlp, ffmpeg, Pillow, pypdf) ---
        Commands::Dl(cmd) => bridge::dispatch_dl(cmd),
        Commands::Media(cmd) => bridge::dispatch_media(cmd),
        Commands::Img(cmd) => bridge::dispatch_img(cmd),
        Commands::Pdf(cmd) => bridge::dispatch_pdf(cmd),
        Commands::Qr(cmd) => bridge::dispatch_qr(cmd),
    }
}
