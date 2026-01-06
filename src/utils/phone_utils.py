import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


def validate_and_normalize_phone(phone: str, region: str = "BR") -> str:
    """
    Validates a phone number and returns it in E.164 format.
    Raises ValueError if the phone number is invalid.
    """
    if not phone:
        return phone

    try:
        parsed_number = phonenumbers.parse(phone, region)
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError(f"Invalid phone number: {phone}")

        return phonenumbers.format_number(
            parsed_number, PhoneNumberFormat.E164
        )
    except NumberParseException as e:
        raise ValueError(f"Could not parse phone number: {phone}") from e
