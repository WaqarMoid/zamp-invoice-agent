import io
import logging

import pdfplumber

logger = logging.getLogger("kestrel-ap.extraction.text_layer")

PAGE_BREAK = "\n\n--- PAGE BREAK ---\n\n"
MAX_PAGES = 5
MAX_CHARS = 30000


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> tuple[str, bool, list[str]]:
    """
    Extract text using pdfplumber with layout=True per doc 06 §6.2.
    Returns:
      (extracted_text, has_text_layer, warnings)
    """
    warnings: list[str] = []
    page_texts: list[str] = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            if total_pages > MAX_PAGES:
                warnings.append(f"PDF has {total_pages} pages; only first {MAX_PAGES} processed.")

            pages_to_process = pdf.pages[:MAX_PAGES]
            for page in pages_to_process:
                txt = page.extract_text(layout=True) or ""
                page_texts.append(txt)

        joined_text = PAGE_BREAK.join(page_texts).strip()

        has_text_layer = len("".join(page_texts).strip()) >= 40

        if len(joined_text) > MAX_CHARS:
            warnings.append(f"Text truncated from {len(joined_text)} to {MAX_CHARS} chars.")
            joined_text = joined_text[:MAX_CHARS]

        return joined_text, has_text_layer, warnings

    except Exception as e:
        logger.warning("Failed to extract text layer from PDF: %s", e)
        return "", False, [f"Failed to read PDF text: {e}"]
