"""Independent expected-value calculator (the "test oracle").

Written separately from app/emi.py and never imports it, so a bug in the
app's math cannot hide itself by also being in the expected value.
Uses Decimal arithmetic instead of floats, and builds the schedule by
simulating each month rather than using the app's aggregation logic.
"""

from decimal import ROUND_HALF_UP, Decimal, getcontext

getcontext().prec = 40


def to_rupees(value: Decimal) -> int:
    """Round to whole rupees the way the UI displays them (half up)."""
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def expected_emi(amount, annual_rate, years) -> Decimal:
    p, months = Decimal(str(amount)), int(years) * 12
    r = Decimal(str(annual_rate)) / Decimal(1200)
    if r == 0:
        return p / months
    factor = (1 + r) ** months
    return p * r * factor / (factor - 1)


def expected_summary(amount, annual_rate, years) -> dict:
    emi = expected_emi(amount, annual_rate, years)
    total_payment = emi * int(years) * 12
    return {
        "emi": to_rupees(emi),
        "total_payment": to_rupees(total_payment),
        "total_interest": to_rupees(total_payment - Decimal(str(amount))),
    }


def expected_yearly_schedule(amount, annual_rate, years) -> list[dict]:
    emi = expected_emi(amount, annual_rate, years)
    r = Decimal(str(annual_rate)) / Decimal(1200)
    balance = Decimal(str(amount))
    rows = []
    for year in range(1, int(years) + 1):
        principal_paid = interest_paid = Decimal(0)
        for _ in range(12):
            interest = balance * r
            principal_paid += emi - interest
            interest_paid += interest
            balance -= emi - interest
        rows.append(
            {
                "year": year,
                "principal": to_rupees(principal_paid),
                "interest": to_rupees(interest_paid),
                "balance": to_rupees(max(balance, Decimal(0))),
            }
        )
    return rows


RUPEES_PATTERN = r"^₹[\d,]+$"  # how the UI shows an amount, e.g. ₹12,89,634


def parse_rupees(text: str) -> int:
    """'₹12,89,634' -> 1289634"""
    digits = text.replace("₹", "").replace(",", "").strip()
    if not digits.lstrip("-").isdigit():
        raise ValueError(f"Not a rupee amount: {text!r}")
    return int(digits)
