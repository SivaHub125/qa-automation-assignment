import re

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

from pages.dashboard_page import DashboardPage
from utils.emi_oracle import RUPEES_PATTERN, expected_summary

scenarios("dashboard.feature")

RUPEES = re.compile(RUPEES_PATTERN)


# ---- Given --------------------------------------------------------------
@given("the calculation service is failing")
def calculation_service_failing(ui_page: Page):
    # an HTML error page instead of JSON, as a crashed server or a proxy would return
    ui_page.route("**/api/emi?*", lambda route: route.fulfill(
        status=502, content_type="text/html", body="<html><h1>502 Bad Gateway</h1></html>"))


# ---- When ---------------------------------------------------------------
@when(parsers.parse('I enter loan amount "{amount}", interest rate "{rate}" and tenure "{years}" years'))
def enter_loan(dashboard: DashboardPage, ctx, amount, rate, years):
    ctx["loan"] = {"amount": amount.replace(",", ""), "rate": rate, "years": years}
    dashboard.enter_loan(amount, rate, years)


@when(parsers.re(r'I enter "(?P<value>[^"]*)" in the "(?P<field>[^"]+)" field'))
def enter_single_value(dashboard: DashboardPage, value, field):
    dashboard.enter_value(field, value)


@when("I open the amortization report from the dashboard")
def open_report_from_dashboard(dashboard: DashboardPage, report):
    dashboard.open_report()
    report.wait_until_settled()


# ---- Then ---------------------------------------------------------------
@then(parsers.parse('the page title is "{title}"'))
def page_title(page: Page, title):
    expect(page).to_have_title(title)


@then("the summary cards for monthly EMI, total interest and total payment show amounts")
def summary_cards_show_amounts(dashboard: DashboardPage):
    for value in (dashboard.emi_value, dashboard.total_interest_value, dashboard.total_payment_value):
        expect(value).to_be_visible()
        expect(value).to_have_text(RUPEES)


@then("the principal vs interest chart is visible")
def chart_visible(dashboard: DashboardPage):
    expect(dashboard.breakup_chart).to_be_visible()
    expect(dashboard.breakup_chart_canvas).to_be_visible()


@then("the monthly EMI, total interest and total payment match the independent calculation")
def summary_matches_oracle(dashboard: DashboardPage, ctx):
    loan = ctx["loan"]
    expected = expected_summary(loan["amount"], loan["rate"], loan["years"])
    assert dashboard.displayed_summary() == expected


@then("the total payment equals the loan amount plus the total interest")
def payment_is_principal_plus_interest(dashboard: DashboardPage, ctx):
    shown = dashboard.displayed_summary()
    assert shown["total_payment"] == int(float(ctx["loan"]["amount"])) + shown["total_interest"]


@then(parsers.parse('the chart shows {count:d} segments labelled "{first}" and "{second}"'))
def chart_segments(dashboard: DashboardPage, ctx, count, first, second):
    data = dashboard.chart_data()
    ctx["chart"] = data
    assert data["type"] == "pie"
    assert data["labels"] == [first, second]
    assert len(data["values"]) == count


@then("every chart segment has a value greater than 0")
def chart_values_positive(ctx):
    values = ctx["chart"]["values"]
    assert values and all(isinstance(v, (int, float)) and v > 0 for v in values), values


@then("the chart segments add up to the total payment shown")
def chart_sums_to_total(dashboard: DashboardPage, ctx):
    shown = dashboard.displayed_summary()
    assert sum(ctx["chart"]["values"]) == shown["total_payment"]


@then("the chart has been drawn on the page")
def chart_drawn(ctx):
    # A blank canvas has 0 non-transparent pixels; a drawn pie has thousands.
    assert ctx["chart"]["paintedPixels"] > 1000, ctx["chart"]["paintedPixels"]


@then(parsers.re(r'I see the validation message "(?P<message>[^"]+)" for "(?P<field>[^"]+)"'))
def validation_message(dashboard: DashboardPage, message, field):
    expect(dashboard.field_error(field)).to_have_text(message)
    expect(dashboard.field(field)).to_have_attribute("aria-invalid", "true")


@then("no EMI result is shown")
def no_result(dashboard: DashboardPage):
    expect(dashboard.emi_value).to_have_text("—")


@then(parsers.parse('the report shows the loan "{amount}" at "{rate}" for "{years}" years'))
def report_shows_loan(report, amount, rate, years):
    expect(report.loan_details).to_contain_text(f"Loan {amount} at {rate} for {years} years")


@then("the amortization report link is disabled")
def report_link_disabled(dashboard: DashboardPage):
    assert dashboard.report_link_text.get_attribute("href") is None
    expect(dashboard.report_link).to_have_count(0)


@then("the chart slices equal the principal and the total interest shown")
def chart_matches_cards(dashboard: DashboardPage):
    shown = dashboard.displayed_summary()
    principal, interest = dashboard.chart_data()["values"]
    assert interest == shown["total_interest"], (interest, shown)
    assert principal + interest == shown["total_payment"], (principal, interest, shown)


@then(parsers.parse('I see the page message "{message}"'))
def page_message(dashboard: DashboardPage, message):
    expect(dashboard.request_error).to_have_text(message)
