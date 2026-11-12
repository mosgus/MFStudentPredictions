import io

from PIL import Image
from pypdf import PdfWriter


def pngs_to_pdf(pngs: list[bytes]) -> bytes:
    """Convert a list of PNG bytes to a single PDF with one image per page."""
    writer = PdfWriter()

    for png_bytes in pngs:
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="PDF")
        buffer.seek(0)
        page_writer = PdfWriter(clone_from=buffer)
        writer.append(page_writer)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()
