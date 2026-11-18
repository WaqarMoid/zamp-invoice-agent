import re
from datetime import date

from dateutil import parser


def parse_date(val: str | date | None) -> date | None:
    """
    Parse date from various string formats per doc 04 §4.3:
    - '2026-11-12' (ISO)
    - '12/11/2026' (DD/MM/YYYY)
    - '12-11-2026'
    - '12 Nov 2026'
    - '12-Nov-26'
    - 'Nov 12, 2026'
    - '10-Nov-26'
    - '15 Nov 2026'
    """
    if val is None:
        return None
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s:
        return None

    # Check ISO format YYYY-MM-DD first so yearfirst is preserved
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            return date.fromisoformat(s)
        except ValueError:
            pass

    try:
        dt = parser.parse(s, dayfirst=True)
        return dt.date()
    except Exception as e:
        raise ValueError(f"Could not parse date from string '{s}': {e}") from e


def extract_date_from_text(text: str | None) -> date | None:
    """
    Extract a date from arbitrary free-form text (e.g. 'Ref Order dated 2026-04-14').
    Returns None if no date could be found.
    """
    if not text:
        return None

    # Check for ISO format pattern YYYY-MM-DD
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1))
        except ValueError:
            pass

    # Check for DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
    if dmy_match:
        try:
            return parser.parse(dmy_match.group(1), dayfirst=True).date()
        except Exception:
            pass

    # Fallback to dateutil fuzzy parse
    try:
        dt = parser.parse(text, dayfirst=True, fuzzy=True)
        return dt.date()
    except Exception:
        return None
