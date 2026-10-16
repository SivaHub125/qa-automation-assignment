"""Capture curated evidence screenshots into reports/evidence/ (run after the test suites).

    python -m tools.capture_evidence

Screens of the app (dashboard, validation, report views) plus the top of each HTML
test report, so a reviewer can see the results without opening anything.
"""

import threading

from playwright.sync_api import Page, sync_playwright
from werkzeug.serving import make_server

from app.server import app
from config.settings import load_settings

SETTINGS = load_settings()
EVIDENCE = SETTINGS.reports_dir / "evidence"


def settle(page: Page, testid: str) -> None:
    page.wait_for_function(
        "id => ['ready', 'error'].includes(document.querySelector(`[data-testid=${id}]`)?.dataset.state)",
        arg=testid,
    )


def calculate(page: Page) -> None:
    with page.expect_response(lambda r: "/api/emi" in r.url):
        page.get_by_role("button", name="Calculate").click()
    settle(page, "summary-cards")


def apply_filters(page: Page) -> None:
    with page.expect_response(lambda r: "/api/schedule" in r.url):
        page.get_by_role("button", name="Apply filters").click()
    settle(page, "schedule-table")


def capture_app(page: Page) -> None:
    base = SETTINGS.base_url
    page.goto(f"{base}/")
    settle(page, "summary-cards")
    page.screenshot(path=EVIDENCE / "01-dashboard.png", full_page=True)

    page.get_by_label("Loan amount", exact=True).fill("1000,000")
    page.get_by_label("Interest rate (% p.a.)", exact=True).fill("35")
    page.get_by_label("Loan tenure (years)", exact=True).fill("5.0")
    calculate(page)
    page.screenshot(path=EVIDENCE / "02-dashboard-validation-errors.png", full_page=True)

    page.goto(f"{base}/report?amount=2500000&rate=9&years=20")
    settle(page, "schedule-table")
    page.screenshot(path=EVIDENCE / "03-report-yearly.png", full_page=True)

    page.get_by_role("radio", name="Monthly").check()
    page.get_by_label("From year").select_option(label="Year 2")
    page.get_by_label("To year").select_option(label="Year 2")
    apply_filters(page)
    page.screenshot(path=EVIDENCE / "04-report-monthly-year-2.png", full_page=True)

    page.get_by_role("radio", name="Yearly").check()
    page.get_by_label("From year").select_option(label="Year 4")
    page.get_by_label("To year").select_option(label="Year 2")
    apply_filters(page)
    page.screenshot(path=EVIDENCE / "05-report-filter-error.png")


def capture_reports(page: Page) -> None:
    for name, report in (
        ("06-test-report.png", "test-report.html"),
        ("07-self-healing-off-report.png", "self-healing-broken.html"),
        ("08-self-healing-on-report.png", "self-healing-healed.html"),
    ):
        path = SETTINGS.reports_dir / report
        if path.exists():
            page.goto(path.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            page.get_by_text("Hide all details").click()  # show the summary, not the first trace
            page.screenshot(path=EVIDENCE / name, full_page=True)


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    server = make_server(SETTINGS.app_host, SETTINGS.app_port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="en-IN")
            capture_app(page)
            capture_reports(page)
            browser.close()
    finally:
        server.shutdown()
    for shot in sorted(EVIDENCE.iterdir()):
        print(shot.relative_to(SETTINGS.reports_dir.parent))


if __name__ == "__main__":
    main()
