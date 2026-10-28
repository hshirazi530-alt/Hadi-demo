"""Iranian mobile validation for the checkout and consultation forms.

Only the nine digits following the fixed +989 prefix are entered in the new
forms. Older integrations may still submit 09..., 989... or +989... . Stored
numbers use the legacy domestic form (09...) to remain compatible with reports
and integrations. Existing database rows are never rewritten.
"""
import re

from django.core.exceptions import ValidationError

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_ERROR = "شمارهٔ همراه معتبر نیست؛ پس از +989 دقیقاً ۹ رقم وارد کنید."


def normalize_iranian_mobile(value):
    value = str(value or "").translate(_DIGITS).strip()
    # Permit ordinary visual separators, but never silently strip letters or
    # accept a second country code or an additional phone extension.
    if not re.fullmatch(r"[+0-9\s()\-]+", value):
        raise ValidationError(_ERROR)
    compact = re.sub(r"[\s()\-]", "", value)
    if re.fullmatch(r"[0-9]{9}", compact):
        suffix = compact
    elif re.fullmatch(r"09[0-9]{9}", compact):
        suffix = compact[2:]
    elif re.fullmatch(r"(?:\+98|0098|98)9[0-9]{9}", compact):
        suffix = compact[-9:]
    else:
        raise ValidationError(_ERROR)
    return "09" + suffix
