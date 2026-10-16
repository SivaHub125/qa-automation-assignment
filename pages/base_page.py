from collections.abc import Callable

from playwright.sync_api import Page

from config.settings import Settings


class BasePage:
    """Shared behaviour for all page objects. URLs come from Settings, never literals.

    The app marks its result area with data-state="loading" | "ready" | "error" while
    it fetches data. Pages name that element in `state_testid`, and every open or
    submit waits for it to settle instead of sleeping.
    """

    path = "/"
    state_testid = ""

    def __init__(self, page: Page, settings: Settings):
        if not self.state_testid:
            raise TypeError(f"{type(self).__name__} must set state_testid (the element with data-state)")
        self.page = page
        self.settings = settings
        self.page.set_default_timeout(settings.default_timeout_ms)

    def open(self, query: str = ""):
        url = f"{self.settings.base_url}{self.path}"
        self.page.goto(f"{url}?{query}" if query else url)
        self.wait_until_settled()
        return self

    def wait_until_settled(self) -> None:
        self.page.wait_for_function(
            "id => ['ready', 'error'].includes(document.querySelector(`[data-testid=${id}]`)?.dataset.state)",
            arg=self.state_testid,
        )

    def submit(self, click: Callable[[], None], api_path: str) -> None:
        """Run a click that triggers an API call, then wait for the page to show the result."""
        with self.page.expect_response(lambda r: api_path in r.url):
            click()
        self.wait_until_settled()
