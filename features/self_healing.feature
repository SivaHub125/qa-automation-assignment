@ui @self_healing
Feature: Self-healing of broken locators
  Each scenario uses ONE intentionally broken locator from pages/broken_locators.py.

  Without healing (default) every scenario fails by timing out on the missing element.
  These are reported as expected failures (xfail): proof that the locators are broken.
  A locator that fails for any other reason, or starts working, fails the run.
  With SELF_HEAL=true the rule-based healer finds a validated replacement at runtime
  and writes it to reports/self_healing/ for a human to review.

  Background:
    Given I open the EMI dashboard

  Scenario: Legacy loan amount input (auto-generated CSS class)
    When I type "2500000" into the legacy "loan amount input" and calculate
    Then the monthly EMI shown is "₹53,735"

  Scenario: Legacy calculate button (stale id)
    When I set the loan amount to "500000" and press the legacy "calculate button"
    Then the monthly EMI shown is "₹10,747"

  Scenario: Legacy monthly EMI value (absolute XPath)
    Then the legacy "emi value" shows "₹21,494"

  Scenario: Legacy total interest value (positional CSS)
    Then the legacy "total interest value" shows "₹2,89,634"

  Scenario: Legacy report link (outdated text)
    When I click the legacy "report link"
    Then the "Amortization report" heading is visible
