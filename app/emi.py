"""EMI and amortization calculations used by the web app.

The test suite deliberately does NOT import this module. Tests compute their
expected values with utils/emi_oracle.py, which is written independently.
"""

import math
import re
from collections.abc import Callable
from dataclasses import dataclass

# Number formats: ASCII digits only ([0-9], not \d, which also matches other scripts).
# A leading minus is accepted so that a negative value gets the clearer range message.
WHOLE_NUMBER = re.compile(r"^-?[0-9]+$")
DECIMAL_NUMBER = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
# plain 1000000 | Indian 10,00,000 | international 1,000,000, with optional decimals
AMOUNT = re.compile(r"^-?([0-9]+|[0-9]{1,2}(,[0-9]{2})*,[0-9]{3}|[0-9]{1,3}(,[0-9]{3})+)(\.[0-9]+)?$")


def _indian_grouping(value: float) -> str:
    """20000000 -> '2,00,00,000'"""
    digits = str(int(value))
    head, groups = digits[:-3], [digits[-3:]]
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(groups)


@dataclass(frozen=True)
class FieldRule:
    """One input field: its format, its range, and its messages.

    Every validation message follows one standard, "<Field> <rule>", with the
    field label as shown on screen, no examples and no full stop. The range
    message is built from the same bounds that are checked, so they cannot drift.
    """

    label: str
    kind: str  # what a valid value is, e.g. "a whole number"
    pattern: re.Pattern
    low: float
    high: float
    show: Callable[[float], str] = lambda v: f"{v:g}"
    unit: str = ""

    def parse(self, raw) -> tuple[float | None, str | None]:
        """Return (value, None) when valid, or (None, message) when not."""
        text = "" if raw is None else str(raw).strip()
        if not text:
            return None, f"{self.label} is required"
        if not self.pattern.match(text):
            return None, f"{self.label} must be {self.kind}"
        value = float(text.replace(",", ""))
        if not self.low <= value <= self.high:
            return None, (f"{self.label} must be between {self.show(self.low)} "
                          f"and {self.show(self.high)}{self.unit}")
        return value, None


LOAN_RULES = {
    "amount": FieldRule("Loan amount", "a number in Indian or international format", AMOUNT,
                        10_000, 20_000_000, show=lambda v: f"₹{_indian_grouping(v)}"),
    "rate": FieldRule("Interest rate", "a number", DECIMAL_NUMBER, 0, 30, show=lambda v: f"{v:g}%"),
    "years": FieldRule("Loan tenure", "a whole number", WHOLE_NUMBER, 1, 30, unit=" years"),
}
YEAR_FILTER_LABELS = {"from_year": "From year", "to_year": "To year"}
YEAR_ORDER_MESSAGE = "From year must not be after To year"  # key "year_order"
VIEW_MESSAGE = "View must be yearly or monthly"


def year_filter_rule(param: str, years: int) -> FieldRule:
    return FieldRule(YEAR_FILTER_LABELS[param], "a whole number", WHOLE_NUMBER, 1, years)


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Invalid input")
        self.errors = errors


@dataclass
class LoanInput:
    amount: float
    rate: float
    years: int


def parse_loan_input(amount, rate, years) -> LoanInput:
    values, errors = {}, {}
    for name, raw in (("amount", amount), ("rate", rate), ("years", years)):
        values[name], error = LOAN_RULES[name].parse(raw)
        if error:
            errors[name] = error
    if errors:
        raise ValidationError(errors)
    return LoanInput(values["amount"], values["rate"], int(values["years"]))


def monthly_emi(loan: LoanInput) -> float:
    months = loan.years * 12
    monthly_rate = loan.rate / 12 / 100
    if monthly_rate == 0:
        return loan.amount / months
    growth = (1 + monthly_rate) ** months
    return loan.amount * monthly_rate * growth / (growth - 1)


def summary(loan: LoanInput) -> dict:
    """Loan summary in whole rupees, rounded once here so every consumer shows the same numbers.

    Total interest is total payment minus the rounded loan amount, so principal +
    interest always equals the total payment exactly (cards and chart slices agree).
    """
    total_payment = _to_rupees(monthly_emi(loan) * loan.years * 12)
    return {
        "amount": loan.amount,
        "rate": loan.rate,
        "years": loan.years,
        "emi": _to_rupees(monthly_emi(loan)),
        "total_interest": total_payment - _to_rupees(loan.amount),
        "total_payment": total_payment,
    }


def _exact_monthly_rows(loan: LoanInput) -> list[dict]:
    emi = monthly_emi(loan)
    monthly_rate = loan.rate / 12 / 100
    balance = loan.amount
    rows = []
    for month in range(1, loan.years * 12 + 1):
        interest = balance * monthly_rate
        principal = emi - interest
        balance = max(balance - principal, 0.0)
        rows.append(
            {"year": (month - 1) // 12 + 1, "month": month, "principal": principal, "interest": interest}
        )
    return rows


def _to_rupees(value: float) -> int:
    return math.floor(value + 0.5)  # half up, like the UI


def _round_rows(rows: list[dict], amount: float) -> list[dict]:
    """Round each row to whole rupees so that the rows always add up exactly.

    Rounding every row on its own makes the column sums drift from the rounded
    totals (by up to ₹35 on a 10-year monthly schedule). Instead, round the running
    total and give each row the difference: rows then sum exactly to the rounded
    total, and each row is still within ₹1 of its exact value. Payment is
    principal + interest and balance is loan minus principal paid so far, so every
    row also adds up across and down.
    """
    paid_principal = paid_interest = 0.0
    shown_principal = shown_interest = 0
    loan = _to_rupees(amount)
    result = []
    for row in rows:
        paid_principal += row["principal"]
        paid_interest += row["interest"]
        principal = _to_rupees(paid_principal) - shown_principal
        interest = _to_rupees(paid_interest) - shown_interest
        shown_principal += principal
        shown_interest += interest
        result.append(
            {**row, "principal": principal, "interest": interest,
             "payment": principal + interest, "balance": loan - shown_principal}
        )
    return result


def monthly_schedule(loan: LoanInput) -> list[dict]:
    return _round_rows(_exact_monthly_rows(loan), loan.amount)


def yearly_schedule(monthly: list[dict]) -> list[dict]:
    """Each year is the sum of its rounded months, so the yearly and monthly views always agree."""
    years: dict[int, dict] = {}
    for row in monthly:
        year = years.setdefault(row["year"], {"year": row["year"], "principal": 0, "interest": 0, "payment": 0})
        for key in ("principal", "interest", "payment"):
            year[key] += row[key]
        year["balance"] = row["balance"]
    return list(years.values())
