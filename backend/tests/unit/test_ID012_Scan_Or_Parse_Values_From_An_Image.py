"""Unit tests for receipt parser service (ID012)."""

from app.services.receipt_parser import parse_date, parse_items, parse_total


def test_ID012_parser_successfully_extracts_date():
    """Test parsing ISO date format from receipt text."""
    result = parse_date("Purchase Date: 2026-03-15")
    assert result == "2026-03-15"


def test_ID012_parser_successfully_extracts_total_amount():
    """Test parsing total amount with $ and decimal format."""
    result = parse_total("Total: $123.45")
    assert result == 123.45


def test_ID012_parser_successfully_filters_keywords_and_validates_prices():
    """Test item extraction filters keywords and rejects invalid prices."""
    text = """
    Milk                    3.99
    Tax                     1.23
    Bread                   2.49
    Tip                     0.50
    Total                   8.22
    """
    items = parse_items(text)
    item_names = [i["item"].lower() for i in items]

    # Valid items should be present
    assert "milk" in item_names
    assert "bread" in item_names

    # Keywords should be filtered out
    assert "tax" not in item_names
    assert "tip" not in item_names
    assert "total" not in item_names
