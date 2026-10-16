"""Page-object fixtures and steps shared across UI feature files."""

import pytest
from playwright.sync_api import Page, Playwright, expect
from pytest_bdd import given, parsers, then

from api.api_result import ApiResult
from config.settings import Settings
from pages.dashboard_page import DashboardPage
from pages.report_page import ReportPage


@pytest.fixture
def dashboard(ui_page: Page, settings: Settings, app_server) -> DashboardPage:
    return DashboardPage(ui_page, settings)


@pytest.fixture
def report(ui_page: Page, settings: Settings, app_server) -> ReportPage:
    return ReportPage(ui_page, settings)


@pytest.fixture(scope="session")
def new_api_context(playwright: Playwright):
    """Factory for API request contexts; all are disposed at the end of the session."""
    contexts = []

    def make(base_url: str):
        contexts.append(playwright.request.new_context(base_url=base_url))
        return contexts[-1]

    yield make
    for context in contexts:
        context.dispose()


@given("I open the EMI dashboard")
def open_dashboard(dashboard: DashboardPage):
    dashboard.open()


@given(parsers.parse('I open the amortization report for loan "{amount}" at "{rate}" for "{years}" years'))
def open_report_for_loan(report: ReportPage, amount, rate, years, ctx):
    ctx["loan"] = {"amount": amount, "rate": rate, "years": int(years)}
    report.open_for_loan(amount, rate, years)


@then(parsers.parse('the "{name}" heading is visible'))
def heading_visible(page: Page, name):
    expect(page.get_by_role("heading", name=name, level=1)).to_be_visible()


@then(parsers.parse('the monthly EMI shown is "{expected_emi}"'))
def emi_shown(dashboard: DashboardPage, expected_emi):
    expect(dashboard.emi_value).to_have_text(expected_emi)


@then("the page loaded without browser errors")
def no_browser_errors(browser_errors):
    assert not browser_errors, browser_errors


# ---- API steps shared by the JSONPlaceholder and app API features --------
@then(parsers.parse("the response status is {status:d}"))
def status_is(ctx, status):
    result: ApiResult = ctx["result"]
    assert result.status == status, f"expected HTTP {status}, got {result.status}: {result.text[:200]}"


# In negative scenarios this runs first, so the failure reason in the report names
# the worst problem: a crash (JP-02) before missing validation (JP-01).
@then("the server does not crash")
def server_does_not_crash(ctx):
    result: ApiResult = ctx["result"]
    assert result.status < 500, f"server crashed with HTTP {result.status}: {result.text[:200]}"
    assert not result.exposes_stack_trace, f"server exposed a stack trace: {result.text[:300]}"
