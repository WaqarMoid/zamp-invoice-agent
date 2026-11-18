import time

from app.config import get_settings
from app.extraction.cache import get_cached_extraction, store_cached_extraction
from app.extraction.gemini import GeminiExtractor
from app.extraction.render import render_pdf_to_images
from app.extraction.text_layer import extract_text_from_pdf_bytes
from app.pipeline.context import RunContext
from app.schemas import StageOutcome


async def run(ctx: RunContext) -> StageOutcome:
    settings = get_settings()
    doc = ctx.document
    pdf_bytes = doc.content or b""
    sha256 = doc.sha256
    model_id = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"

    t0 = time.perf_counter()

    # 1. Check cache if enabled
    if ctx.use_cache and settings.EXTRACTION_CACHE:
        cached_result = get_cached_extraction(ctx.session, sha256)
        if cached_result:
            extracted_inv, method, cached_model = cached_result
            latency_ms = int((time.perf_counter() - t0) * 1000)
            ctx.extraction = extracted_inv
            ctx.extraction_method = method
            ctx.run.extraction_method = method
            ctx.run.use_cache = True

            k_fields = sum(1 for _, v in extracted_inv if v is not None)
            m_lines = len(extracted_inv.line_items)

            output = {
                "method": method,
                "model": cached_model,
                "cached": True,
                "latency_ms": latency_ms,
                "extraction": extracted_inv.model_dump(mode="json"),
            }
            ctx.stage_outputs["extract"] = output
            return StageOutcome(
                status="PASSED",
                summary=f"Read {k_fields} fields and {m_lines} line items via {method} (cached)",
                output=output,
                checks=[],
            )

    # 2. Extractor resolution (mock in tests or live Gemini)
    extractor = ctx.extractor
    if not extractor:
        extractor = GeminiExtractor(model=model_id, api_key=settings.GEMINI_API_KEY)

    # 3. Route: text vs vision
    if ctx.has_text_layer:
        text, _, _ = extract_text_from_pdf_bytes(pdf_bytes)
        extracted_inv = extractor.extract_from_text(text)
        method = "text"
    else:
        images = render_pdf_to_images(pdf_bytes, dpi=200)
        extracted_inv = extractor.extract_from_images(images)
        method = "vision"

    latency_ms = int((time.perf_counter() - t0) * 1000)

    # 4. Store in cache
    if ctx.use_cache and settings.EXTRACTION_CACHE:
        store_cached_extraction(ctx.session, sha256, method, model_id, extracted_inv)
        ctx.session.flush()

    ctx.extraction = extracted_inv
    ctx.extraction_method = method
    ctx.run.extraction_method = method
    ctx.run.use_cache = False

    k_fields = sum(1 for _, v in extracted_inv if v is not None)
    m_lines = len(extracted_inv.line_items)

    output = {
        "method": method,
        "model": model_id,
        "cached": False,
        "latency_ms": latency_ms,
        "extraction": extracted_inv.model_dump(mode="json"),
    }
    ctx.stage_outputs["extract"] = output

    return StageOutcome(
        status="PASSED",
        summary=f"Read {k_fields} fields and {m_lines} line items via {method}",
        output=output,
        checks=[],
    )
