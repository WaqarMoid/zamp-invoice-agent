from decimal import Decimal

from app.rules.money import format_rupees, from_paise, parse_money, to_paise


def test_parse_money():
    assert parse_money("1,29,682.00") == Decimal("129682.00")
    assert parse_money("Rs. 45,675") == Decimal("45675.00")
    assert parse_money("₹ 1,18,000") == Decimal("118000.00")
    assert parse_money(129682) == Decimal("129682.00")
    assert parse_money(129682.5) == Decimal("129682.50")


def test_paise_round_trip():
    original = Decimal("129682.75")
    paise = to_paise(original)
    assert paise == 12968275
    back = from_paise(paise)
    assert back == original


def test_round_half_up_point_005():
    # In round-half-up, 10.005 becomes 10.01 and 10.004 becomes 10.00
    assert parse_money("10.005") == Decimal("10.01")
    assert parse_money("10.004") == Decimal("10.00")
    assert format_rupees(Decimal("10.005")) == "10.01"
