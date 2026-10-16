"""INTENTIONALLY BROKEN locators for the AI self-healing exercise.

Do not "fix" these by hand: they are left broken on purpose. Each one is a
classic anti-pattern that breaks when the DOM changes. They are used only by
features/self_healing.feature (tag @self_healing, excluded from the default run).

    pytest -m self_healing                   # 5 xfailed: the locators are broken (expected failures)
    SELF_HEAL=true pytest -m self_healing    # healer repairs them at runtime and reports suggestions

See docs/SELF_HEALING.md for the design.
"""

from dataclasses import dataclass

from playwright.sync_api import Locator

from config.settings import Settings
from healing.healer import LocatorHealer
from pages.base_page import BasePage
from utils.emi_oracle import RUPEES_PATTERN


@dataclass(frozen=True)
class LocatorSpec:
    key: str
    selector: str            # the broken selector, exactly as a legacy test might have it
    intent: str              # what the element is, in plain words (input for the healer / LLM)
    anti_pattern: str        # why this selector is brittle
    role: str | None = None  # expected ARIA role: a healed candidate must match it
    value_pattern: str | None = None  # expected text shape: a healed candidate must match it


BROKEN_LOCATORS = {
    spec.key: spec
    for spec in [
        LocatorSpec(
            key="loan_amount_input",
            selector=".css-1x8k2qz > input",
            intent="Loan amount text input",
            anti_pattern="Auto-generated CSS-in-JS class name; changes on every build",
            role="textbox",
        ),
        LocatorSpec(
            key="calculate_button",
            selector="#btnCalculateEMI",
            intent="Calculate button",
            anti_pattern="Stale ID: the element was renamed and no longer has this id",
            role="button",
        ),
        LocatorSpec(
            key="emi_value",
            selector="xpath=/html/body/div[2]/main/section[1]/div[3]/span",
            intent="Monthly EMI value",
            anti_pattern="Absolute positional XPath; breaks when any parent is added or moved",
            value_pattern=RUPEES_PATTERN,
        ),
        LocatorSpec(
            key="total_interest_value",
            selector="div.cards-grid > div:nth-child(2) > span.amount",
            intent="Total interest value",
            anti_pattern="Positional CSS chain (nth-child) tied to an old layout",
            value_pattern=RUPEES_PATTERN,
        ),
        LocatorSpec(
            key="report_link",
            selector="text=View Full Report Now",
            intent="View amortization report link",
            anti_pattern="Hard-coded visible text that has since changed",
            role="link",
        ),
    ]
}


class LegacyDashboardPage(BasePage):
    """A 'legacy' page object that still uses the broken locators above."""

    path = "/"
    state_testid = "summary-cards"
    BROKEN_ACTION_TIMEOUT_MS = 3000  # fail fast when a locator is broken

    def __init__(self, page, settings: Settings, healer: LocatorHealer):
        super().__init__(page, settings)
        self.healer = healer

    def element(self, key: str) -> Locator:
        return self.healer.find(BROKEN_LOCATORS[key])

    def fill(self, key: str, value: str) -> None:
        self.element(key).fill(value, timeout=self.BROKEN_ACTION_TIMEOUT_MS)

    def click(self, key: str) -> None:
        self.element(key).click(timeout=self.BROKEN_ACTION_TIMEOUT_MS)

    def text_of(self, key: str) -> str:
        return self.element(key).inner_text(timeout=self.BROKEN_ACTION_TIMEOUT_MS)
