import pytest

from app.facts import find_amount, find_orders


def test_order_numbers_are_found_once_in_order():
    assert find_orders("Order NW-10482 and again nw-10482, also AB-123456 and X-1") == ["NW-10482", "AB-123456"]
    assert find_orders("no order here") == []


@pytest.mark.parametrize("text, amount", [
    ("refund of $850", 850), ("it cost £1,299.50", 1299.5), ("349 pounds", 349), ("about 20 dollars", 20),
    ("$50 and $200 and 75 pounds", 200), ("six desks in 3 days", None),
])
def test_amounts(text, amount):
    assert find_amount(text) == amount
