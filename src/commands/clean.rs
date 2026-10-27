use crate::cli::CleanArgs;
use anyhow::Result;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

const ARTIFACT_DIRS: &[&str] = &[
    "node_modules",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "dist",
];

fn dir_size(path: &Path) -> u64 {
    WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter_map(|e| e.metadata().ok())
        .filter(|m| m.is_file())
        .map(|m| m.len())
        .sum()
}

pub fn run(args: CleanArgs) -> Result<()> {
    let mut total_bytes: u64 = 0;
    let mut found = Vec::new();

    let mut it = WalkDir::new(&args.dir).into_iter();
    while let Some(Ok(entry)) = it.next() {
        if entry.file_type().is_dir() {
            let name = entry.file_name().to_string_lossy();
            if ARTIFACT_DIRS.contains(&name.as_ref()) {
                let p = entry.path().to_path_buf();
                let sz = dir_size(&p);
                total_bytes += sz;
                found.push((p, sz));
                it.skip_current_dir();
            }
        }
    }

    if found.is_empty() {
        println!("No build cache directories found under {}", args.dir.display());
        return Ok(());
    }

    for (path, sz) in &found {
        let mb = (*sz as f64) / (1024.0 * 1024.0);
        if args.apply {
            fs::remove_dir_all(path)?;
            println!("Removed {:>8.2} MB  {}", mb, path.display());
        } else {
            println!("[Dry Run] {:>8.2} MB  {}", mb, path.display());
        }
    }

    let total_mb = (total_bytes as f64) / (1024.0 * 1024.0);
    if args.apply {
        println!("\nReclaimed {:.2} MB across {} directories.", total_mb, found.len());
    } else {
        println!(
            "\nTotal reclaimable: {:.2} MB across {} directories (pass --apply to delete).",
            total_mb,
            found.len()
        );
    }
    Ok(())
}
