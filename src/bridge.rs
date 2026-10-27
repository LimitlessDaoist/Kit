use crate::cli::{DlArgs, ImgArgs, MediaArgs, PdfAction, PdfArgs, QrArgs};
use anyhow::{bail, Context, Result};
use std::env;
use std::process::Command;

/// Locates the Python interpreter and runs `python3 -m kit_py.cli <subcommand> ...`
fn run_python_tool(args: &[String]) -> Result<()> {
    let python_bin = env::var("KIT_PYTHON").unwrap_or_else(|_| "python3".to_string());

    let mut cmd = Command::new(&python_bin);
    cmd.arg("-m").arg("kit_py.cli").args(args);

    // Automatically include repository `./python` directory if running from source checkout
    if let Ok(current_dir) = env::current_dir() {
        let local_py = current_dir.join("python");
        if local_py.exists() {
            let existing = env::var("PYTHONPATH").unwrap_or_default();
            let combined = if existing.is_empty() {
                local_py.display().to_string()
            } else {
                format!("{}:{}", local_py.display(), existing)
            };
            cmd.env("PYTHONPATH", combined);
        }
    }

    let status = cmd
        .status()
        .with_context(|| format!("Failed to invoke Python engine via `{}`", python_bin))?;

    if !status.success() {
        bail!("Python tool exited with status: {}", status);
    }
    Ok(())
}

pub fn dispatch_dl(cmd: DlArgs) -> Result<()> {
    let mut args = vec![
        "dl".to_string(),
        cmd.url,
        "--quality".to_string(),
        cmd.quality,
        "--output-dir".to_string(),
        cmd.output_dir.display().to_string(),
        "--audio-format".to_string(),
        cmd.audio_format,
    ];
    if cmd.audio_only {
        args.push("--audio-only".to_string());
    }
    if let Some(clip) = cmd.clip {
        args.push("--clip".to_string());
        args.push(clip);
    }
    if cmd.subs {
        args.push("--subs".to_string());
    }
    if cmd.info_only {
        args.push("--info-only".to_string());
    }
    run_python_tool(&args)
}

pub fn dispatch_media(cmd: MediaArgs) -> Result<()> {
    let mut args = vec![
        "media".to_string(),
        cmd.input.display().to_string(),
        "--output".to_string(),
        cmd.output.display().to_string(),
        "--crf".to_string(),
        cmd.crf.to_string(),
    ];
    if let Some(start) = cmd.start {
        args.push("--start".to_string());
        args.push(start);
    }
    if let Some(end) = cmd.end {
        args.push("--end".to_string());
        args.push(end);
    }
    run_python_tool(&args)
}

pub fn dispatch_img(cmd: ImgArgs) -> Result<()> {
    let mut args = vec![
        "img".to_string(),
        cmd.input.display().to_string(),
        "--quality".to_string(),
        cmd.quality.to_string(),
    ];
    if let Some(out) = cmd.output {
        args.push("--output".to_string());
        args.push(out.display().to_string());
    }
    if let Some(fmt) = cmd.format {
        args.push("--format".to_string());
        args.push(fmt);
    }
    if let Some(resize) = cmd.resize {
        args.push("--resize".to_string());
        args.push(resize);
    }
    if cmd.strip_exif {
        args.push("--strip-exif".to_string());
    }
    run_python_tool(&args)
}

pub fn dispatch_pdf(cmd: PdfArgs) -> Result<()> {
    let mut args = vec!["pdf".to_string()];
    match cmd.action {
        PdfAction::Merge { output, inputs } => {
            args.push("merge".to_string());
            args.push("--output".to_string());
            args.push(output.display().to_string());
            for input in inputs {
                args.push(input.display().to_string());
            }
        }
        PdfAction::Split {
            input,
            pages,
            output,
        } => {
            args.push("split".to_string());
            args.push(input.display().to_string());
            args.push("--pages".to_string());
            args.push(pages);
            args.push("--output".to_string());
            args.push(output.display().to_string());
        }
        PdfAction::Text { input, output } => {
            args.push("text".to_string());
            args.push(input.display().to_string());
            if let Some(out) = output {
                args.push("--output".to_string());
                args.push(out.display().to_string());
            }
        }
    }
    run_python_tool(&args)
}

pub fn dispatch_qr(cmd: QrArgs) -> Result<()> {
    let mut args = vec!["qr".to_string(), cmd.payload];
    if let Some(out) = cmd.output {
        args.push("--output".to_string());
        args.push(out.display().to_string());
    }
    run_python_tool(&args)
}
