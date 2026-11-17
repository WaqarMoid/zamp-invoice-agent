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
