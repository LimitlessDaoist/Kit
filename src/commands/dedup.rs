use crate::cli::{DedupArgs, HashAlgo};
use crate::commands::hash::hash_file;
use anyhow::Result;
use rayon::prelude::*;
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use walkdir::WalkDir;

#[derive(Serialize)]
struct DuplicateGroup {
    hash: String,
    size_bytes: u64,
    files: Vec<String>,
}

pub fn run(args: DedupArgs) -> Result<()> {
    let mut size_map: HashMap<u64, Vec<PathBuf>> = HashMap::new();

    for entry in WalkDir::new(&args.dir).into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            if let Ok(meta) = entry.metadata() {
                if meta.len() >= args.min_size {
                    size_map
                        .entry(meta.len())
                        .or_default()
                        .push(entry.into_path());
                }
            }
        }
    }

    let candidates: Vec<(u64, Vec<PathBuf>)> = size_map
        .into_iter()
        .filter(|(_, paths)| paths.len() > 1)
        .collect();

    let groups: Vec<DuplicateGroup> = candidates
        .par_iter()
        .flat_map(|(size, paths)| {
            let mut by_hash: HashMap<String, Vec<String>> = HashMap::new();
            for p in paths {
                if let Ok(digest) = hash_file(p, HashAlgo::Blake3) {
                    by_hash
                        .entry(digest)
                        .or_default()
                        .push(p.display().to_string());
                }
            }
            by_hash
                .into_iter()
                .filter(|(_, list)| list.len() > 1)
                .map(|(hash, files)| DuplicateGroup {
                    hash,
                    size_bytes: *size,
                    files,
                })
                .collect::<Vec<_>>()
        })
        .collect();

    if args.json {
        println!("{}", serde_json::to_string_pretty(&groups)?);
    } else if groups.is_empty() {
        println!("No duplicate files found (min_size = {} bytes).", args.min_size);
    } else {
        println!("Found {} duplicate group(s):", groups.len());
        for g in &groups {
            println!("\n• BLAKE3 {} ({} bytes each):", &g.hash[..16], g.size_bytes);
            for f in &g.files {
                println!("    - {}", f);
            }
        }
    }
    Ok(())
}
