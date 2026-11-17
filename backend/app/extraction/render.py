import io
import logging

import pymupdf
from PIL import Image

logger = logging.getLogger("kestrel-ap.extraction.render")

MAX_VISION_PAGES = 5
MAX_IMAGE_DIM = 2400


def render_pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[bytes]:
    """
    Render PDF pages to PNG byte chunks using PyMuPDF per doc 06 §6.2.
    Processes at most MAX_VISION_PAGES.
    """
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    num_pages = min(len(doc), MAX_VISION_PAGES)
    images: list[bytes] = []

    for i in range(num_pages):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)

    doc.close()
    return images


def prepare_image_bytes(image_bytes: bytes) -> bytes:
    """
    Prepare an uploaded image (PNG/JPEG) for the vision path.
    Downscales if the longest side exceeds MAX_IMAGE_DIM.
    """
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    longest = max(width, height)

    if longest > MAX_IMAGE_DIM:
        scale = MAX_IMAGE_DIM / longest
        new_w = int(width * scale)
        new_h = int(height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        out_buf = io.BytesIO()
        img.save(out_buf, format=img.format or "PNG")
        return out_buf.getvalue()

    return image_bytes
