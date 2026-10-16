from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

from pages.report_page import ReportPage
from utils.emi_oracle import expected_yearly_schedule

scenarios("report.feature")

# ---- Given --------------------------------------------------------------
@given("the schedule service is failing")
def schedule_service_failing(ui_page: Page):
    ui_page.route("**/api/schedule?*", lambda route: route.fulfill(
        status=502, content_type="text/html", body="<html><h1>502 Bad Gateway</h1></html>"))


# ---- When ---------------------------------------------------------------
@when(parsers.parse('I switch to the "{view}" view'))
def switch_view(report: ReportPage, view):
    report.apply_filters(view=view)


@when(parsers.parse("I filter the report from year {from_year:d} to year {to_year:d}"))
def filter_years(report: ReportPage, from_year, to_year):
    report.apply_filters(from_year=from_year, to_year=to_year)


# ---- Then ---------------------------------------------------------------
@then(parsers.parse("the schedule table shows {count:d} rows"))
def row_count(report: ReportPage, count):
    expect(report.body_rows).to_have_count(count)


@then(parsers.parse('the first row is "{period}"'))
def first_row(report: ReportPage, period):
    expect(report.body_rows.first.get_by_role("rowheader")).to_have_text(period)


@then("every row matches the independently calculated schedule")
def rows_match_oracle(report: ReportPage, ctx):
    loan = ctx["loan"]
    expected = expected_yearly_schedule(loan["amount"], loan["rate"], loan["years"])
    actual = report.rows()
    assert len(actual) == len(expected)
    for shown, exp in zip(actual, expected):
        assert shown["period"] == f"Year {exp['year']}"
        for key in ("principal", "interest", "balance"):
            assert abs(shown[key] - exp[key]) <= 1, (exp["year"], key, shown[key], exp[key])


@then("the principal column adds up to the loan amount")
def principal_sums_to_loan(report: ReportPage, ctx):
    rows = report.rows()
    assert sum(r["principal"] for r in rows) == int(ctx["loan"]["amount"])


@then("the closing balance of the last row is 0")
def last_balance_zero(report: ReportPage):
    assert report.rows()[-1]["balance"] == 0


@then("the totals row matches the sum of the rows")
def totals_match_rows(report: ReportPage, ctx):
    rows, totals = report.rows(), report.totals()
    assert totals["principal"] == int(ctx["loan"]["amount"])
    for key in ("principal", "interest", "payment"):
        assert sum(r[key] for r in rows) == totals[key], key


@then(parsers.parse('I see the report filter message "{message}"'))
def filter_message(report: ReportPage, message):
    expect(report.filter_error).to_have_text(message)


@then(parsers.parse("the yearly chart has a bar for each of the {years:d} years"))
def chart_has_bars(report: ReportPage, ctx, years):
    expect(report.yearly_chart_canvas).to_be_visible()
    data = report.chart_data()
    ctx["chart"] = data
    assert data["type"] == "bar"
    assert data["labels"] == [f"Year {y}" for y in range(1, years + 1)]
    assert [d["label"] for d in data["datasets"]] == ["Principal", "Interest"]


@then("every principal and interest bar in the chart is greater than 0")
def bars_positive(ctx):
    for dataset in ctx["chart"]["datasets"]:
        assert all(v > 0 for v in dataset["values"]), dataset
    # rendered bar heights in pixels, not just the data: proves the bars were drawn
    assert all(h > 0 for h in ctx["chart"]["bars"]), ctx["chart"]["bars"]


@then("the chart values match the schedule table")
def chart_matches_table(report: ReportPage, ctx):
    rows = report.rows()
    principal, interest = (d["values"] for d in ctx["chart"]["datasets"])
    assert principal == [r["principal"] for r in rows]
    assert interest == [r["interest"] for r in rows]


@then(parsers.parse('the loan details show "{message}"'))
def loan_details_show(report: ReportPage, message):
    expect(report.loan_details).to_have_text(message)
