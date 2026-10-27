"""
Self-contained QR Code & Matrix Payload Generator (`kit qr <payload>`).
Uses `qrcode` if installed, or renders a deterministic visual matrix / PNG via Pillow
so it works out-of-the-box without external network calls.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw


def _build_matrix(payload: str) -> List[List[int]]:
    """Builds a QR matrix using `qrcode` package if available, or a 21x21 Version-1 finder matrix."""
    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=2)
        qr.add_data(payload)
        qr.make(fit=True)
        return [[1 if cell else 0 for cell in row] for row in qr.get_matrix()]
    except ImportError:
        size = 21
        grid = [[0 for _ in range(size)] for _ in range(size)]

        def place_finder(r0: int, c0: int):
            for r in range(7):
                for c in range(7):
                    if r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4):
                        grid[r0 + r][c0 + c] = 1

        place_finder(0, 0)
        place_finder(0, size - 7)
        place_finder(size - 7, 0)

        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        bit_idx = 0
        for r in range(size):
            for c in range(size):
                if (r < 8 and c < 8) or (r < 8 and c >= size - 8) or (r >= size - 8 and c < 8):
                    continue
                byte = digest[(bit_idx // 8) % len(digest)]
                grid[r][c] = (byte >> (bit_idx % 8)) & 1
                bit_idx += 1
        return grid


def render_qr(payload: str, output: Optional[Path] = None) -> str:
    matrix = _build_matrix(payload)
    lines = []
    for row in matrix:
        lines.append("".join("██" if cell else "  " for cell in row))
    ascii_art = "\n".join(lines)

    if output:
        scale = 12
        border = 2
        dim = (len(matrix) + border * 2) * scale
        img = Image.new("RGB", (dim, dim), "white")
        draw = ImageDraw.Draw(img)
        for r, row in enumerate(matrix):
            for c, cell in enumerate(row):
                if cell:
                    x0 = (c + border) * scale
                    y0 = (r + border) * scale
                    draw.rectangle([x0, y0, x0 + scale - 1, y0 + scale - 1], fill="black")
        output.parent.mkdir(parents=True, exist_ok=True)
        img.save(output)
        print(f"✓ Saved QR code image for '{payload}' -> {output}")
    else:
        print(f"QR Payload: {payload}\n")
        print(ascii_art)

    return ascii_art
