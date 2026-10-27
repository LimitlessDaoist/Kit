use crate::cli::{HashAlgo, HashArgs};
use anyhow::{bail, Context, Result};
use md5::Md5;
use sha2::{Digest, Sha256, Sha512};
use std::fs::File;
use std::io::{BufReader, Read};
use std::path::Path;

pub fn hash_file(path: &Path, algo: HashAlgo) -> Result<String> {
    let file = File::open(path).with_context(|| format!("Cannot open {}", path.display()))?;
    let mut reader = BufReader::with_capacity(64 * 1024, file);
    let mut buffer = [0u8; 64 * 1024];

    match algo {
        HashAlgo::Blake3 => {
            let mut hasher = blake3::Hasher::new();
            loop {
                let n = reader.read(&mut buffer)?;
                if n == 0 {
                    break;
                }
                hasher.update(&buffer[..n]);
            }
            Ok(hasher.finalize().to_hex().to_string())
        }
        HashAlgo::Sha256 => {
            let mut hasher = Sha256::new();
            loop {
                let n = reader.read(&mut buffer)?;
                if n == 0 {
                    break;
                }
                hasher.update(&buffer[..n]);
            }
            Ok(hex::encode(hasher.finalize()))
        }
        HashAlgo::Sha512 => {
            let mut hasher = Sha512::new();
            loop {
                let n = reader.read(&mut buffer)?;
                if n == 0 {
                    break;
                }
                hasher.update(&buffer[..n]);
            }
            Ok(hex::encode(hasher.finalize()))
        }
        HashAlgo::Md5 => {
            let mut hasher = Md5::new();
            loop {
                let n = reader.read(&mut buffer)?;
                if n == 0 {
                    break;
                }
                hasher.update(&buffer[..n]);
            }
            Ok(hex::encode(hasher.finalize()))
        }
    }
}

pub fn run(args: HashArgs) -> Result<()> {
    for path in &args.files {
        let digest = hash_file(path, args.algo)?;
        println!("{}  {}", digest, path.display());

        if let Some(expected) = &args.check {
            if digest.eq_ignore_ascii_case(expected.trim()) {
                println!("✓ Checksum verified for {}", path.display());
            } else {
                bail!(
                    "Checksum mismatch for {}: expected {}, got {}",
                    path.display(),
                    expected,
                    digest
                );
            }
        }
    }
    Ok(())
}
