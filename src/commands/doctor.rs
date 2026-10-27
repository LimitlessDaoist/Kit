use anyhow::Result;
use std::process::Command;

fn check_cmd(cmd: &str, arg: &str) -> (bool, String) {
    match Command::new(cmd).arg(arg).output() {
        Ok(out) if out.status.success() => {
            let text = String::from_utf8_lossy(&out.stdout);
            let first_line = text.lines().next().unwrap_or("installed").trim().to_string();
            (true, first_line)
        }
        _ => (false, "not found".to_string()),
    }
}

pub fn run() -> Result<()> {
    println!("Kit Environment Doctor");
    println!("======================");

    for (label, bin, flag) in [
        ("Rust / Cargo", "cargo", "--version"),
        ("Python 3", "python3", "--version"),
        ("FFmpeg", "ffmpeg", "-version"),
        ("yt-dlp", "yt-dlp", "--version"),
        ("Git", "git", "--version"),
    ] {
        let (ok, ver) = check_cmd(bin, flag);
        let mark = if ok { "✓" } else { "✗" };
        println!("  {} {:<15} {}", mark, label, ver);
    }
    Ok(())
}
