import re

from django.core.exceptions import ValidationError


PHONE_DIGITS_PATTERN = re.compile(r"\D+")


def digits_only(value: str) -> str:
    return PHONE_DIGITS_PATTERN.sub("", value or "")


def phone_digits(value: str) -> str:
    digits = digits_only(value)
    if len(digits) == 10:
        digits = f"7{digits}"
    elif digits.startswith("8") and len(digits) == 11:
        digits = f"7{digits[1:]}"
    if len(digits) != 11 or not digits.startswith("7"):
        raise ValidationError("Введите телефон в формате +7 999 999 99 99.")
    return digits


def normalize_phone(value: str) -> str:
    digits = phone_digits(value)
    return f"+{digits}"


def format_phone(value: str) -> str:
    digits = phone_digits(value)[1:]
    return f"+7 {digits[:3]} {digits[3:6]} {digits[6:8]} {digits[8:10]}"


def phone_lookup_values(value: str) -> tuple[str, str]:
    canonical = normalize_phone(value)
    return canonical, format_phone(canonical)
