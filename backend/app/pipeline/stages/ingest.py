from app.extraction.text_layer import extract_text_from_pdf_bytes
from app.pipeline.context import RunContext
from app.schemas import StageOutcome


async def run(ctx: RunContext) -> StageOutcome:
    doc = ctx.document
    mime = doc.mime or "application/pdf"
    pdf_bytes = doc.content or b""
    size_bytes = len(pdf_bytes)

    if mime in {"image/png", "image/jpeg"}:
        page_count = 1
        has_text_layer = False
        text_chars = 0
        summary = "Image upload, vision path"
    else:
        # PDF
        text, has_text_layer, _ = extract_text_from_pdf_bytes(pdf_bytes)
        text_chars = len(text)
        # Determine page count from pdfplumber or pypdf
        import io

        import pdfplumber

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)
        except Exception:
            page_count = 1

        if has_text_layer:
            summary = f"PDF, {page_count} page(s), text layer found"
        else:
            summary = f"PDF, {page_count} page(s), no text layer (scanned)"

    # Update document record
    doc.page_count = page_count
    doc.has_text_layer = has_text_layer
    ctx.has_text_layer = has_text_layer

    output = {
        "sha256": doc.sha256,
        "filename": doc.filename,
        "mime": mime,
        "size_bytes": size_bytes,
        "page_count": page_count,
        "has_text_layer": has_text_layer,
        "text_chars": text_chars,
    }

    ctx.stage_outputs["ingest"] = output
    return StageOutcome(
        status="PASSED",
        summary=summary,
        output=output,
        checks=[],
    )
