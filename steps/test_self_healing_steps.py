import pytest
from playwright.sync_api import Page
from pytest_bdd import parsers, scenarios, then, when

from config.settings import Settings
from healing.healer import LocatorHealer
from pages.broken_locators import LegacyDashboardPage
from pages.dashboard_page import DashboardPage

scenarios("self_healing.feature")


def key(name: str) -> str:
    """'loan amount input' -> 'loan_amount_input'"""
    return name.replace(" ", "_")


@pytest.fixture
def healer(ui_page: Page, settings: Settings, request):
    healer = LocatorHealer(ui_page, enabled=settings.self_heal,
                           report_dir=settings.reports_dir / "self_healing")
    yield healer
    healer.write_report(request.node.name)


@pytest.fixture
def legacy(ui_page: Page, settings: Settings, healer, app_server) -> LegacyDashboardPage:
    return LegacyDashboardPage(ui_page, settings, healer)


@when(parsers.parse('I type "{amount}" into the legacy "{name}" and calculate'))
def type_into_legacy(legacy: LegacyDashboardPage, dashboard: DashboardPage, amount, name):
    legacy.fill(key(name), amount)
    dashboard.calculate()


@when(parsers.parse('I set the loan amount to "{amount}" and press the legacy "{name}"'))
def press_legacy(legacy: LegacyDashboardPage, dashboard: DashboardPage, amount, name):
    dashboard.loan_amount.fill(amount)
    dashboard.calculate(lambda: legacy.click(key(name)))


@when(parsers.parse('I click the legacy "{name}"'))
def click_legacy(legacy: LegacyDashboardPage, name):
    legacy.click(key(name))


@then(parsers.parse('the legacy "{name}" shows "{expected}"'))
def legacy_shows(legacy: LegacyDashboardPage, name, expected):
    assert legacy.text_of(key(name)) == expected
