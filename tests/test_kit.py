import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pypdf import PdfWriter

from kit_py.cli import main as cli_main
from kit_py.image_tools import process_image
from kit_py.media_dl import build_yt_dlp_options
from kit_py.native_fallback import run_dedup, run_encode, run_hash, run_json
from kit_py.pdf_tools import extract_pdf_text, merge_pdfs, split_pdf
from kit_py.qr_tools import render_qr


class TestKitToolkit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_yt_dlp_options_builder(self):
        opts = build_yt_dlp_options(
            output_dir=self.root / "dl",
            quality="720",
            audio_only=True,
            audio_format="mp3",
            clip="00:00:10-00:00:25",
            subs=True,
        )
        self.assertEqual(opts["format"], "bestaudio/best")
        self.assertTrue(opts["writesubtitles"])
        self.assertIn("external_downloader_args", opts)
        self.assertEqual(opts["postprocessors"][0]["preferredcodec"], "mp3")

    def test_image_resize_and_convert(self):
        src = self.root / "sample.png"
        img = Image.new("RGBA", (400, 200), color=(20, 120, 220, 255))
        img.save(src)

        out = self.root / "converted.jpg"
        process_image(src, output_path=out, target_format="jpg", resize_spec="200", strip_exif=True)
        self.assertTrue(out.exists())
        with Image.open(out) as res:
            self.assertEqual(res.size, (200, 100))
            self.assertEqual(res.mode, "RGB")

    def test_pdf_merge_and_split(self):
        pdf1 = self.root / "a.pdf"
        pdf2 = self.root / "b.pdf"
        for p in (pdf1, pdf2):
            w = PdfWriter()
            w.add_blank_page(width=200, height=200)
            w.add_blank_page(width=200, height=200)
            with open(p, "wb") as f:
                w.write(f)

        merged = self.root / "merged.pdf"
        merge_pdfs([pdf1, pdf2], merged)
        self.assertTrue(merged.exists())

        split_out = self.root / "split.pdf"
        split_pdf(merged, "1-2,4", split_out)
        self.assertTrue(split_out.exists())

        txt = extract_pdf_text(split_out)
        self.assertIn("Page 3", txt)

    def test_qr_generator(self):
        png_out = self.root / "qr.png"
        ascii_qr = render_qr("https://example.com", output=png_out)
        self.assertTrue(png_out.exists())
        self.assertIn("██", ascii_qr)

    def test_hash_dedup_encode_json(self):
        f1 = self.root / "one.txt"
        f2 = self.root / "two.txt"
        f1.write_text("identical payload" * 100, encoding="utf-8")
        f2.write_text("identical payload" * 100, encoding="utf-8")

        digests = run_hash([f1], algo="sha256")
        self.assertEqual(len(digests[str(f1)]), 64)

        dups = run_dedup(self.root, min_size=10, as_json=True)
        self.assertEqual(len(dups), 1)

        b64 = run_encode("base64-enc", "hello-kit")
        dec = run_encode("base64-dec", b64)
        self.assertEqual(dec, "hello-kit")

        jfile = self.root / "data.json"
        jfile.write_text(json.dumps({"project": {"name": "kit", "fast": True}}), encoding="utf-8")
        q = run_json(str(jfile), minify=True, query="project.name")
        self.assertEqual(q, '"kit"')

    def test_cli_entrypoint(self):
        qr_path = self.root / "cli_qr.png"
        rc = cli_main(["qr", "https://kit.local", "-o", str(qr_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(qr_path.exists())


if __name__ == "__main__":
    unittest.main()
