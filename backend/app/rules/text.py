import re

import rapidfuzz

STOPWORDS = {"the", "of", "for", "per", "and", "with", "a", "an"}


def normalize_invoice_number(s: str | None) -> str | None:
    """
    Normalize invoice number per doc 07 §7.4.0:
    1. uppercase
    2. split into tokens with regex [A-Z]+|[0-9]+ (splits non-alphanumeric and letter/digit boundaries)
    3. for numeric tokens: strip leading zeros ('0089'->'89', '0'->'0'); if token is exactly 4 digits
       and starts with '20' replace with last two digits ('2026'->'26')
    4. join with '-'
    """
    if not s:
        return None
    s_upper = s.upper()
    tokens = re.findall(r"[A-Z]+|[0-9]+", s_upper)
    if not tokens:
        return None
    norm_tokens = []
    for tok in tokens:
        if tok.isdigit():
            if len(tok) == 4 and tok.startswith("20"):
                norm_tokens.append(tok[2:])
            else:
                norm_tokens.append(str(int(tok)))
        else:
            norm_tokens.append(tok)
    return "-".join(norm_tokens)


def normalize_po_number(s: str | None) -> str | None:
    """Normalize PO number using the same tokenizer as invoice numbers."""
    return normalize_invoice_number(s)


def clean_desc(s: str) -> str:
    """Clean line item description for fuzzy matching."""
    if not s:
        return ""
    text = s.lower().replace("&", "and")
    # collapse 5 ply / 5-ply to 5ply
    text = re.sub(r"(\d+)\s*[-]\s*ply\b", r"\1ply", text)
    text = re.sub(r"(\d+)\s+ply\b", r"\1ply", text)
    text = text.replace("-", "")
    # strip punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    words = [w for w in text.split() if w not in STOPWORDS]
    return " ".join(words)


def desc_similarity(a: str, b: str) -> float:
    """
    Compute similarity between two line item descriptions using rapidfuzz token_set_ratio.
    Returns float in range [0.0, 1.0].
    """
    c_a = clean_desc(a)
    c_b = clean_desc(b)
    if not c_a or not c_b:
        return 0.0
    score = rapidfuzz.fuzz.token_set_ratio(c_a, c_b)
    return float(score / 100.0)
