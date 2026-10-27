use crate::cli::{EncodeArgs, EncodeMode};
use anyhow::{bail, Context, Result};
use base64::{engine::general_purpose, Engine as _};
use uuid::Uuid;

pub fn run(args: EncodeArgs) -> Result<()> {
    match args.mode {
        EncodeMode::Uuid => {
            println!("{}", Uuid::new_v4());
            Ok(())
        }
        mode => {
            let input = args
                .input
                .context("Input string is required for this mode")?;
            match mode {
                EncodeMode::Base64Enc => {
                    println!("{}", general_purpose::STANDARD.encode(input.as_bytes()));
                }
                EncodeMode::Base64Dec => {
                    let bytes = general_purpose::STANDARD
                        .decode(input.trim())
                        .context("Invalid Base64 input")?;
                    println!("{}", String::from_utf8_lossy(&bytes));
                }
                EncodeMode::HexEnc => {
                    println!("{}", hex::encode(input.as_bytes()));
                }
                EncodeMode::HexDec => {
                    let bytes = hex::decode(input.trim()).context("Invalid Hex input")?;
                    println!("{}", String::from_utf8_lossy(&bytes));
                }
                EncodeMode::JwtDecode => {
                    let parts: Vec<&str> = input.trim().split('.').collect();
                    if parts.len() < 2 {
                        bail!("Invalid JWT token format (expected header.payload.signature)");
                    }
                    let header = general_purpose::URL_SAFE_NO_PAD
                        .decode(parts[0])
                        .context("Invalid JWT header Base64URL")?;
                    let payload = general_purpose::URL_SAFE_NO_PAD
                        .decode(parts[1])
                        .context("Invalid JWT payload Base64URL")?;
                    println!("Header:  {}", String::from_utf8_lossy(&header));
                    println!("Payload: {}", String::from_utf8_lossy(&payload));
                }
                EncodeMode::Uuid => unreachable!(),
            }
            Ok(())
        }
    }
}
