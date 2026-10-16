from playwright.sync_api import Locator

from pages.base_page import BasePage
from utils.emi_oracle import parse_rupees


class ReportPage(BasePage):
    """Amortization report: filters, schedule table and yearly bar chart."""

    path = "/report"
    state_testid = "schedule-table"

    # ---- locators -------------------------------------------------------
    def view_option(self, name: str) -> Locator:
        return self.page.get_by_role("radio", name=name)

    @property
    def from_year(self) -> Locator:
        return self.page.get_by_label("From year")

    @property
    def to_year(self) -> Locator:
        return self.page.get_by_label("To year")

    @property
    def apply_button(self) -> Locator:
        return self.page.get_by_role("button", name="Apply filters")

    @property
    def filter_error(self) -> Locator:
        return self.page.get_by_test_id("filter-error")

    @property
    def loan_details(self) -> Locator:
        return self.page.get_by_test_id("loan-details")

    @property
    def schedule_table(self) -> Locator:
        return self.page.get_by_role("table", name="Amortization schedule")

    @property
    def body_rows(self) -> Locator:
        # rows that have a row header inside <tbody>; the totals row lives in <tfoot>
        return self.schedule_table.locator("tbody").get_by_role("row")

    @property
    def yearly_chart_canvas(self) -> Locator:
        return self.page.get_by_role("img", name="Yearly principal and interest chart")

    # ---- actions --------------------------------------------------------
    def open_for_loan(self, amount, rate, years) -> "ReportPage":
        return self.open(f"amount={amount}&rate={rate}&years={years}")

    def apply_filters(self, view: str | None = None, from_year=None, to_year=None) -> None:
        if view:
            self.view_option(view).check()
        if from_year is not None:
            self.from_year.select_option(label=f"Year {from_year}")
        if to_year is not None:
            self.to_year.select_option(label=f"Year {to_year}")
        self.submit(self.apply_button.click, "/api/schedule")

    # ---- reads ----------------------------------------------------------
    def rows(self) -> list[dict]:
        # one browser call for the whole table instead of two per row
        table = self.body_rows.evaluate_all("rows => rows.map(r => [...r.cells].map(c => c.innerText))")
        result = []
        for period, principal, interest, payment, balance in table:
            result.append({
                "period": period,
                "principal": parse_rupees(principal),
                "interest": parse_rupees(interest),
                "payment": parse_rupees(payment),
                "balance": parse_rupees(balance),
            })
        return result

    def totals(self) -> dict:
        return {
            "principal": parse_rupees(self.page.get_by_test_id("total-principal").inner_text()),
            "interest": parse_rupees(self.page.get_by_test_id("total-interest").inner_text()),
            "payment": parse_rupees(self.page.get_by_test_id("total-paid").inner_text()),
        }

    def chart_data(self) -> dict:
        return self.yearly_chart_canvas.evaluate(
            """canvas => {
                const chart = Chart.getChart(canvas);
                return {
                    type: chart.config.type,
                    labels: chart.data.labels,
                    datasets: chart.data.datasets.map(d => ({ label: d.label, values: d.data })),
                    bars: chart.getDatasetMeta(0).data.map(bar => bar.height),
                };
            }"""
        )
