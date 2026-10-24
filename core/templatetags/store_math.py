"""Template filters for price/discount math used by the storefront."""
from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def minus(value, arg):
    """Return value - arg (Decimal-safe)."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (TypeError, ValueError, ArithmeticError):
        return Decimal("0")


@register.filter
def times(value, arg):
    """Return (value / arg) * 100 rounded to an integer percentage."""
    try:
        divisor = Decimal(str(arg))
        if not divisor:
            return 0
        result = (Decimal(str(value)) / divisor) * Decimal("100")
        return int(result.to_integral_value(rounding="ROUND_HALF_UP"))
    except (TypeError, ValueError, ArithmeticError, ZeroDivisionError):
        return 0
