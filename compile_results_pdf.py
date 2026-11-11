"""Compile the PNG charts in results/ into a single PDF, one image per page."""

import io
import re
from pathlib import Path

from PIL import Image
from pypdf import PdfWriter

RESULTS_DIR = Path(__file__).parent / "results"
DATE_SUFFIX = re.compile(r"_(\d{4}-\d{2}-\d{2})\.png$")


def main():
    all_pngs = sorted(RESULTS_DIR.glob("*.png"))
    if not all_pngs:
        print(f"No PNG files found in {RESULTS_DIR}")
        return

    dated = [(m.group(1), p) for p in all_pngs if (m := DATE_SUFFIX.search(p.name))]
    if dated:
        latest_date = max(date for date, _ in dated)
        png_paths = [p for date, p in dated if date == latest_date]
        output_pdf = RESULTS_DIR / f"results_{latest_date}.pdf"
    else:
        # No dated filenames (e.g. older charts) -- fall back to compiling everything found.
        png_paths = all_pngs
        output_pdf = RESULTS_DIR / "results.pdf"

    writer = PdfWriter()
    for png_path in png_paths:
        image = Image.open(png_path).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="PDF")
        buffer.seek(0)
        page_writer = PdfWriter(clone_from=buffer)
        writer.append(page_writer)
        print(f"Added {png_path.name}")

    with open(output_pdf, "wb") as f:
        writer.write(f)
    print(f"Wrote {output_pdf}")


if __name__ == "__main__":
    main()
