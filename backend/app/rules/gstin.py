import re

CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_REGEX = re.compile(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def normalize_gstin(s: str | None) -> str | None:
    """Strip whitespace and uppercase."""
    if not s:
        return None
    cleaned = "".join(s.split()).upper()
    return cleaned if cleaned else None


def calculate_gstin_checksum(first14: str) -> str:
    """Calculate the 15th checksum character for the first 14 GSTIN characters."""
    if len(first14) != 14:
        raise ValueError(f"Expected 14 characters, got {len(first14)}")
    s = 0
    for i, c in enumerate(first14):
        p = CH.index(c) * (1 if i % 2 == 0 else 2)
        s += p // 36 + p % 36
    return CH[(36 - s % 36) % 36]


def is_valid_gstin(s: str | None) -> bool:
    """Validate GSTIN format and 15th character checksum."""
    norm = normalize_gstin(s)
    if not norm or len(norm) != 15:
        return False
    if not GSTIN_REGEX.match(norm):
        return False
    expected_check = calculate_gstin_checksum(norm[:14])
    return norm[14] == expected_check


def get_state_code(gstin: str | None) -> str | None:
    """Extract 2-digit state code from GSTIN."""
    norm = normalize_gstin(gstin)
    if not norm or len(norm) < 2:
        return None
    return norm[:2]
