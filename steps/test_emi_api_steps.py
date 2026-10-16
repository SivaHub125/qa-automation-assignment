from decimal import Decimal

import pytest
from pytest_bdd import parsers, scenarios, then, when

from api.emi_app_client import EmiAppClient
from config.settings import Settings
from utils.emi_oracle import to_rupees

scenarios("emi_api.feature")


@pytest.fixture(scope="session")
def app_api(new_api_context, settings: Settings, app_server) -> EmiAppClient:
    return EmiAppClient(new_api_context(settings.base_url))


# ---- When ---------------------------------------------------------------
@when(parsers.parse('I request the EMI for loan "{amount}" at "{rate}" for "{years}" years'))
def request_emi(ctx, app_api: EmiAppClient, amount, rate, years):
    ctx["result"] = app_api.emi(amount=amount, rate=rate, years=years)


@when(parsers.parse('I request the "{view}" schedule for loan "{amount}" at "{rate}" for "{years}" years '
                    'from year "{from_year}" to year "{to_year}"'))
def request_schedule(ctx, app_api: EmiAppClient, view, amount, rate, years, from_year, to_year):
    ctx["loan_amount"] = int(amount)
    ctx["result"] = app_api.schedule(amount=amount, rate=rate, years=years, view=view,
                                     from_year=from_year, to_year=to_year)


@when(parsers.parse('I request the path "{path}"'))
def request_path(ctx, app_api: EmiAppClient, path):
    ctx["result"] = app_api.get(path)


# ---- Then ---------------------------------------------------------------
@then(parsers.parse('the error message is "{message}"'))
def error_message(ctx, message):
    errors = (ctx["result"].json or {}).get("errors", {})
    assert message in errors.values(), errors


@then(parsers.parse("the monthly EMI returned rounds to {rupees:d} rupees"))
def emi_rounds_to(ctx, rupees):
    assert to_rupees(Decimal(str(ctx["result"].json["emi"]))) == rupees


@then("the principal, interest and payment columns add up exactly to the totals")
def columns_add_up(ctx):
    body = ctx["result"].json
    for key in ("principal", "interest", "payment"):
        assert sum(r[key] for r in body["rows"]) == body["totals"][key], key


@then("every row's payment equals its principal plus its interest")
def row_adds_up(ctx):
    for row in ctx["result"].json["rows"]:
        assert row["payment"] == row["principal"] + row["interest"], row


@then("the principal total equals the loan amount")
def principal_total(ctx):
    assert ctx["result"].json["totals"]["principal"] == ctx["loan_amount"]


@then("each row's balance equals the previous balance minus the row's principal")
def balances_chain(ctx):
    balance = ctx["loan_amount"]
    for row in ctx["result"].json["rows"]:
        balance -= row["principal"]
        assert row["balance"] == balance, row
    assert balance == 0


@then(parsers.parse("the response has {count:d} rows and no separate yearly list"))
def rows_sent_once(ctx, count):
    body = ctx["result"].json
    assert len(body["rows"]) == count and "yearly" not in body, sorted(body)
