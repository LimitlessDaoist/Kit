"""
PDF Toolkit (`kit pdf merge|split|text`).
Powered by `pypdf` for fast merging, page range extraction, and text extraction.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from pypdf import PdfReader, PdfWriter


def parse_page_ranges(range_str: str, max_pages: int) -> List[int]:
    """Parses 1-based page specifications like '1-3,5' into 0-based page indices."""
    indices: List[int] = []
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            for p in range(start, end + 1):
                if 1 <= p <= max_pages:
                    indices.append(p - 1)
        else:
            p = int(part)
            if 1 <= p <= max_pages:
                indices.append(p - 1)
    return indices


def merge_pdfs(inputs: List[Path], output: Path) -> Path:
    writer = PdfWriter()
    total_pages = 0
    for pdf_path in inputs:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)
            total_pages += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)
    print(f"✓ Merged {len(inputs)} PDFs ({total_pages} pages) -> {output}")
    return output


def split_pdf(input_path: Path, pages_spec: str, output: Path) -> Path:
    reader = PdfReader(str(input_path))
    indices = parse_page_ranges(pages_spec, len(reader.pages))
    if not indices:
        raise ValueError(f"No valid pages matched '{pages_spec}' (document has {len(reader.pages)} pages)")

    writer = PdfWriter()
    for idx in indices:
        writer.add_page(reader.pages[idx])

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)
    print(f"✓ Extracted {len(indices)} page(s) -> {output}")
    return output


def extract_pdf_text(input_path: Path, output: Optional[Path] = None) -> str:
    reader = PdfReader(str(input_path))
    chunks = []
    for idx, page in enumerate(reader.pages, start=1):
        chunks.append(f"--- Page {idx} ---\n{page.extract_text() or ''}")
    full_text = "\n\n".join(chunks).strip()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(full_text, encoding="utf-8")
        print(f"✓ Extracted text ({len(reader.pages)} pages) -> {output}")
    else:
        print(full_text)
    return full_text
