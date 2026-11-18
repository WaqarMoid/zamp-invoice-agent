import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

TWO_PLACES = Decimal("0.01")


def quantize_money(amount: Decimal | float | int | str) -> Decimal:
    """Quantize to 2 decimal places using ROUND_HALF_UP."""
    if isinstance(amount, Decimal):
        dec = amount
    else:
        dec = Decimal(str(amount))
    return dec.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def parse_money(val: Any) -> Decimal:
    """
    Parse a money string or number into a Decimal quantized to 2 decimal places.
    Accepts:
      - '1,29,682.00'
      - 'Rs. 45,675'
      - '₹ 1,18,000'
      - 129682 or 129682.50
    """
    if val is None:
        raise ValueError("Cannot parse None as money")
    if isinstance(val, (int, float, Decimal)):
        return quantize_money(val)

    s = str(val).strip()
    # Strip currency prefixes (Rs., Rs, INR, ₹)
    s = re.sub(r"^(?:rs\.?|inr|₹)\s*", "", s, flags=re.IGNORECASE)
    # Strip trailing currency symbols
    s = re.sub(r"\s*(?:rs\.?|inr|₹)$", "", s, flags=re.IGNORECASE)
    # Remove commas and whitespace
    s = re.sub(r"[,\s]", "", s)
    if not s:
        raise ValueError(f"Cannot parse empty money string from '{val}'")
    return quantize_money(s)


def to_paise(val: Decimal | float | int | str) -> int:
    """Convert rupee value to integer paise."""
    dec = quantize_money(val)
    paise_dec = (dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise_dec)


def from_paise(paise: int | None) -> Decimal:
    """Convert integer paise back to Decimal rupees with 2 decimal places."""
    if paise is None:
        return Decimal("0.00")
    return (Decimal(paise) / Decimal(100)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def format_rupees(val: Decimal | float | int | None) -> str:
    """Format rupee Decimal as decimal string with 2 dp, e.g. '129682.00'."""
    if val is None:
        return "0.00"
    dec = quantize_money(val)
    return str(dec)


format_money = format_rupees
