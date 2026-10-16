from playwright.sync_api import Locator

from pages.base_page import BasePage
from utils.emi_oracle import parse_rupees


class DashboardPage(BasePage):
    """EMI calculator dashboard.

    Locator strategy: label text for inputs, role + accessible name for
    buttons/links, data-testid only where there is no stable accessible name
    (result values, chart container). No positional CSS/XPath.
    """

    path = "/"
    state_testid = "summary-cards"
    # field name used in steps -> (label on screen, id used by the field's error element)
    FIELDS = {
        "Loan amount": ("Loan amount", "amount"),
        "Interest rate": ("Interest rate (% p.a.)", "rate"),
        "Loan tenure": ("Loan tenure (years)", "years"),
    }

    # ---- locators -------------------------------------------------------
    def field(self, name: str) -> Locator:
        # exact=True so the "Loan amount slider" range input is not matched too
        return self.page.get_by_label(self.FIELDS[name][0], exact=True)

    def field_error(self, name: str) -> Locator:
        return self.page.get_by_test_id(f"{self.FIELDS[name][1]}-error")

    @property
    def loan_amount(self) -> Locator:
        return self.field("Loan amount")

    @property
    def calculate_button(self) -> Locator:
        return self.page.get_by_role("button", name="Calculate")

    @property
    def emi_value(self) -> Locator:
        return self.page.get_by_test_id("emi-value")

    @property
    def total_interest_value(self) -> Locator:
        return self.page.get_by_test_id("total-interest-value")

    @property
    def total_payment_value(self) -> Locator:
        return self.page.get_by_test_id("total-payment-value")

    @property
    def breakup_chart(self) -> Locator:
        return self.page.get_by_test_id("breakup-chart")

    @property
    def breakup_chart_canvas(self) -> Locator:
        return self.page.get_by_role("img", name="Principal vs interest chart")

    @property
    def report_link(self) -> Locator:
        return self.page.get_by_role("link", name="View amortization report")

    @property
    def request_error(self) -> Locator:
        return self.page.get_by_test_id("request-error")

    @property
    def report_link_text(self) -> Locator:
        # also finds the element when it has no href (then it is no longer a "link" role)
        return self.page.get_by_text("View amortization report", exact=True)

    # ---- actions --------------------------------------------------------
    def calculate(self, click=None) -> None:
        """Press Calculate (or run another click that triggers it) and wait for the result."""
        self.submit(click or self.calculate_button.click, "/api/emi")

    def enter_loan(self, amount, rate, years) -> None:
        for name, value in (("Loan amount", amount), ("Interest rate", rate), ("Loan tenure", years)):
            self.field(name).fill(str(value))
        self.calculate()

    def enter_value(self, name: str, value: str) -> None:
        self.field(name).fill(value)
        self.calculate()

    def open_report(self) -> None:
        self.report_link.click()

    # ---- reads ----------------------------------------------------------
    def displayed_summary(self) -> dict:
        return {
            "emi": parse_rupees(self.emi_value.inner_text()),
            "total_interest": parse_rupees(self.total_interest_value.inner_text()),
            "total_payment": parse_rupees(self.total_payment_value.inner_text()),
        }

    def chart_data(self) -> dict:
        """Read the data the Chart.js instance is actually drawing, plus whether pixels were painted."""
        return self.breakup_chart_canvas.evaluate(
            """canvas => {
                const chart = Chart.getChart(canvas);
                const { width, height } = canvas;
                const pixels = canvas.getContext('2d').getImageData(0, 0, width, height).data;
                let painted = 0;
                for (let i = 3; i < pixels.length; i += 4) if (pixels[i] > 0) painted++;
                return {
                    type: chart.config.type,
                    labels: chart.data.labels,
                    values: chart.data.datasets[0].data,
                    paintedPixels: painted,
                };
            }"""
        )
