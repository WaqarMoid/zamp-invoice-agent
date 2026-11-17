import json
from pathlib import Path

from app.rules.gstin import get_state_code, is_valid_gstin, normalize_gstin

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "seed_data"

# Load the 7 seed GSTINs: 1 buyer + 6 vendors
with open(SEED_DIR / "buyer.json", encoding="utf-8") as f:
    buyer_gstin = json.load(f)["buyer"]["gstin"]

with open(SEED_DIR / "vendors.json", encoding="utf-8") as f:
    vendors_gstins = [v["gstin"] for v in json.load(f)]

SEED_GSTINS = [buyer_gstin] + vendors_gstins


def test_seed_gstins_all_valid():
    assert len(SEED_GSTINS) == 7
    for gstin in SEED_GSTINS:
        assert is_valid_gstin(gstin), f"Expected {gstin} to be valid"


def test_flip_last_char_invalid():
    for gstin in SEED_GSTINS:
        last_char = gstin[-1]
        flipped_char = "0" if last_char != "0" else "1"
        corrupted = gstin[:-1] + flipped_char
        assert not is_valid_gstin(corrupted), f"Expected corrupted {corrupted} to be invalid"


def test_lowercase_normalized():
    lower = "29aaack4521m1zd"
    assert is_valid_gstin(lower)
    assert normalize_gstin(lower) == "29AAACK4521M1ZD"


def test_14_char_invalid():
    assert not is_valid_gstin("29AAACK4521M1Z")
    assert not is_valid_gstin("29AAACK4521M1ZDA")


def test_state_code():
    assert get_state_code("29AAACK4521M1ZD") == "29"
    assert get_state_code("36AAJFD3349K1Z6") == "36"
    assert get_state_code("27AADCB8810Q1Z7") == "27"
