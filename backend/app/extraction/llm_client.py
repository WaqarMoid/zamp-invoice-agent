from typing import Protocol

from app.schemas import ExtractedInvoice


class Extractor(Protocol):
    name: str
    model: str

    def extract_from_text(self, text: str) -> ExtractedInvoice:
        """Extract invoice fields from text layer string."""
        ...

    def extract_from_images(self, images: list[bytes]) -> ExtractedInvoice:
        """Extract invoice fields from list of image byte chunks."""
        ...
