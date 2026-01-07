import pytest

from utils.phone_utils import validate_and_normalize_phone


def test_validate_and_normalize_phone_valid():
    # Test valid Brazilian numbers
    assert validate_and_normalize_phone("11999999999") == "+5511999999999"
    assert validate_and_normalize_phone("+5511999999999") == "+5511999999999"
    assert validate_and_normalize_phone("11 99999-9999") == "+5511999999999"
    assert validate_and_normalize_phone("(11) 99999-9999") == "+5511999999999"


def test_validate_and_normalize_phone_invalid():
    # Test invalid numbers
    with pytest.raises(ValueError, match="Invalid phone number"):
        validate_and_normalize_phone("123")

    with pytest.raises(ValueError, match="Invalid phone number"):
        validate_and_normalize_phone("0000000000")


def test_validate_and_normalize_phone_empty():
    assert not validate_and_normalize_phone("")
    assert validate_and_normalize_phone(None) is None


def test_validate_and_normalize_phone_international():
    # Test US number
    assert (
        validate_and_normalize_phone("+14155552671", region="US")
        == "+14155552671"
    )
    # Even with BR region, international numbers with + should work
    assert validate_and_normalize_phone("+14155552671") == "+14155552671"


def test_validate_and_normalize_phone_number_parse_exception():
    ABC = "ABC"
    with pytest.raises(
        ValueError, match=f"Could not parse phone number: {ABC}"
    ):
        validate_and_normalize_phone(ABC)
