use crate::cli::JsonArgs;
use anyhow::{Context, Result};
use serde_json::Value;
use std::fs;
use std::io::{self, Read};

pub fn run(args: JsonArgs) -> Result<()> {
    let raw = if args.input == "-" {
        let mut buf = String::new();
        io::stdin().read_to_string(&mut buf)?;
        buf
    } else {
        fs::read_to_string(&args.input)
            .with_context(|| format!("Failed to read JSON file: {}", args.input))?
    };

    let mut value: Value = serde_json::from_str(&raw).context("Invalid JSON input")?;

    if let Some(query) = &args.query {
        for key in query.split('.') {
            if key.is_empty() {
                continue;
            }
            if let Ok(idx) = key.parse::<usize>() {
                value = value
                    .get(idx)
                    .cloned()
                    .with_context(|| format!("Array index `{}` not found", idx))?;
            } else {
                value = value
                    .get(key)
                    .cloned()
                    .with_context(|| format!("Key `{}` not found", key))?;
            }
        }
    }

    if args.minify {
        println!("{}", serde_json::to_string(&value)?);
    } else {
        println!("{}", serde_json::to_string_pretty(&value)?);
    }
    Ok(())
}
