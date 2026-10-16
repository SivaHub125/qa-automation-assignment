"""Root fixtures and hooks shared by all test layers (UI, API, SQL)."""

import base64
import functools
import threading
import time
import urllib.request

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from werkzeug.serving import make_server

from config.settings import Settings, load_settings

try:
    import pytest_html
except ImportError:  # report plugin is optional
    pytest_html = None

# Known defects are tagged in .feature files and turned into strict xfail markers.
# strict=True: if the API is ever fixed, the test XPASSes, fails, and tells us to update it.
KNOWN_DEFECTS = {
    "known_defect_no_validation": (
        "DEFECT JP-01: JSONPlaceholder performs no input validation and returns 201 "
        "for invalid posts instead of a 4xx error"
    ),
    "known_defect_server_error": (
        "DEFECT JP-02: JSONPlaceholder returns 500 with a stack trace for malformed or "
        "oversized bodies instead of 400 / 413"
    ),
}


@functools.cache
def current_settings() -> Settings:
    """Settings for this test session, read from config/.env.<ENV> once."""
    return load_settings()


@pytest.hookimpl(trylast=True)  # after pytest-base-url has added its (empty) "Base URL" row
def pytest_configure(config):
    """Show the environment under test in the HTML report header."""
    try:
        from pytest_metadata.plugin import metadata_key
    except ImportError:
        return
    settings = current_settings()
    metadata = config.stash[metadata_key]
    metadata.pop("Base URL", None)
    metadata.update(
        {"ENV": settings.env, "App URL": settings.base_url, "API URL": settings.api_base_url,
         "Self-healing": "on" if settings.self_heal else "off"}
    )


def pytest_bdd_apply_tag(tag, function):
    if tag in KNOWN_DEFECTS:
        # raises=AssertionError: only a failed assertion counts as the known defect;
        # a network error or a bug in the test itself still shows up as a real failure.
        pytest.mark.xfail(reason=KNOWN_DEFECTS[tag], strict=True, raises=AssertionError)(function)
        return True
    if tag == "self_healing" and not current_settings().self_heal:
        # The locators are broken on purpose, so without the healer these scenarios are
        # expected to fail, and only by timing out on a missing element. A locator that is
        # broken for another reason (e.g. invalid selector syntax), or that starts working,
        # fails the run.
        pytest.mark.xfail(reason="Locators are intentionally broken; run with SELF_HEAL=true to heal them",
                          strict=True, raises=PlaywrightTimeoutError)(function)
    return None  # default handling: the tag also becomes a pytest marker


@pytest.fixture(scope="session")
def settings() -> Settings:
    return current_settings()


@pytest.fixture(scope="session")
def app_server(settings: Settings):
    """Start the Flask app in a background thread for the test session (if START_APP=true)."""
    if not settings.start_app:
        yield settings.base_url
        return

    from app.server import app

    server = make_server(settings.app_host, settings.app_port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while True:
        try:
            urllib.request.urlopen(f"{settings.base_url}/health", timeout=1)
            break
        except OSError:
            if time.time() > deadline:
                raise RuntimeError(f"App did not start on {settings.base_url}")
            time.sleep(0.2)
    yield settings.base_url
    server.shutdown()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, settings: Settings):
    return {**browser_type_launch_args, "headless": settings.headless, "slow_mo": settings.slow_mo_ms}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1280, "height": 900}, "locale": "en-IN"}


# pytest-bdd requests step fixtures lazily, so they never appear in item.funcargs.
# UI fixtures register the page here so the report hook below can screenshot it.
PAGE_KEY = pytest.StashKey()


ERRORS_KEY = pytest.StashKey()


def _is_browser_error(response) -> bool:
    """A 400 from the app's API is a normal validation answer; anything else >= 400 is an error."""
    return response.status >= 500 or (response.status >= 400 and "/api/" not in response.url)


@pytest.fixture
def ui_page(page, request, settings: Settings):
    request.node.stash[PAGE_KEY] = (page, settings)
    # Record problems a user never sees but a reviewer would: uncaught JavaScript errors
    # (including failed async handlers), requests that never completed, and HTTP errors
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"JavaScript error: {e}"))
    page.on("requestfailed", lambda r: errors.append(f"request failed: {r.url} ({r.failure})"))
    page.on("response", lambda r: _is_browser_error(r) and errors.append(f"HTTP {r.status} {r.url}"))
    request.node.stash[ERRORS_KEY] = errors
    yield page
    # Checked after every UI scenario, not only where a step asks for it. Scenarios that
    # trigger server errors on purpose are tagged @allow_http_errors.
    if errors and request.node.get_closest_marker("allow_http_errors") is None:
        pytest.fail(f"Browser errors during the scenario: {errors}", pytrace=False)


@pytest.fixture
def browser_errors(ui_page, request) -> list[str]:
    return request.node.stash[ERRORS_KEY]


@pytest.fixture
def ctx() -> dict:
    """Per-scenario scratch space for passing data between steps."""
    return {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach a final-state screenshot of every UI scenario (pass or fail) to the HTML report."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    if PAGE_KEY not in item.stash:
        return
    page, settings = item.stash[PAGE_KEY]
    try:
        png = page.screenshot(full_page=True)
    except Exception:  # page already closed, etc.
        return
    folder = settings.reports_dir / "screenshots"
    folder.mkdir(parents=True, exist_ok=True)
    status = "xfailed" if hasattr(report, "wasxfail") else "FAILED" if report.failed else "passed"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in item.name)[:120]
    (folder / f"{status}__{safe}.png").write_bytes(png)
    if pytest_html is not None:
        extras = getattr(report, "extras", [])
        extras.append(pytest_html.extras.png(base64.b64encode(png).decode(), name="Final state"))
        report.extras = extras
