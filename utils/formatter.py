from __future__ import annotations


def format_price(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    sign = _sign(value) if signed else ""
    return f"{sign}${abs(value):,.2f}"


def format_change(value: float | None) -> str:
    if value is None:
        return "N/A"
    return format_price(value, signed=True)


def format_percent(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    sign = _sign(value) if signed else ""
    return f"{sign}{abs(value):.1f}%"


def format_thb(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    sign = _sign(value) if signed else ""
    return f"{sign}{abs(value):,.0f} THB"


def format_shares(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value < 1:
        return f"{value:.4f} sh"
    return f"{value:,.2f} sh"


def format_supports(values: list[float]) -> str:
    if not values:
        return "N/A"
    return " / ".join(_trim_number(value) for value in values)


def _sign(value: float) -> str:
    return "+" if value >= 0 else "-"


def _trim_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")
