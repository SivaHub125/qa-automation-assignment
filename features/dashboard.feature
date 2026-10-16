@ui
Feature: EMI calculator dashboard
  As a borrower
  I want to see my monthly EMI and the cost of my loan
  So that I can plan my repayments

  Background:
    Given I open the EMI dashboard

  @smoke
  Scenario: Dashboard loads with the default loan
    Then the page title is "EMI Calculator"
    And the "EMI Calculator" heading is visible
    And the summary cards for monthly EMI, total interest and total payment show amounts
    And the principal vs interest chart is visible
    And the page loaded without browser errors

  # QA: expected_emi values must be verified by hand on https://emicalculator.net/
  # The step also checks every value against utils/emi_oracle.py (independent calculation).
  Scenario Outline: EMI is calculated correctly for <amount> at <rate>% over <years> years
    When I enter loan amount "<amount>", interest rate "<rate>" and tenure "<years>" years
    Then the monthly EMI, total interest and total payment match the independent calculation
    And the monthly EMI shown is "<expected_emi>"
    And the total payment equals the loan amount plus the total interest

    Examples:
      | amount  | rate | years | expected_emi |
      | 1000000 | 10.5 | 5     | ₹21,494      |
      | 500000  | 8.5  | 3     | ₹15,784      |
      | 2500000 | 9    | 20    | ₹22,493      |
      | 100000  | 12   | 1     | ₹8,885       |
      | 120000  | 0    | 1     | ₹10,000      |
      | 10000   | 30   | 30    | ₹250         |
      | 20000000| 0.05 | 30    | ₹55,974      |

  # Accepted loan amount formats: plain digits, Indian grouping, international grouping, decimals
  Scenario Outline: Loan amount written as <format> is accepted
    When I enter loan amount "<amount>", interest rate "10.5" and tenure "5" years
    Then the monthly EMI shown is "₹21,494"

    Examples:
      | format                 | amount     |
      | Indian grouping        | 10,00,000  |
      | international grouping | 1,000,000  |
      | decimals               | 1000000.00 |

  Scenario: Chart reflects the calculated values
    When I enter loan amount "1000000", interest rate "10.5" and tenure "5" years
    Then the chart shows 2 segments labelled "Principal amount" and "Total interest"
    And every chart segment has a value greater than 0
    And the chart segments add up to the total payment shown
    And the chart has been drawn on the page

  # QA: add or change invalid-input cases here
  Scenario Outline: Invalid <field> "<value>" is rejected
    When I enter "<value>" in the "<field>" field
    Then I see the validation message "<message>" for "<field>"
    And no EMI result is shown

    Examples:
      | field         | value     | message                                                        |
      | Loan amount   |           | Loan amount is required                                        |
      | Loan amount   | abc       | Loan amount must be a number in Indian or international format |
      | Loan amount   | 1000,000  | Loan amount must be a number in Indian or international format |
      | Loan amount   | 100,0000  | Loan amount must be a number in Indian or international format |
      | Loan amount   | 1,0,0,000 | Loan amount must be a number in Indian or international format |
      | Loan amount   | 1e6       | Loan amount must be a number in Indian or international format |
      | Loan amount   | 10 00 000 | Loan amount must be a number in Indian or international format |
      | Loan amount   | 9999      | Loan amount must be between ₹10,000 and ₹2,00,00,000           |
      | Loan amount   | 20000001  | Loan amount must be between ₹10,000 and ₹2,00,00,000           |
      | Loan amount   | -500000   | Loan amount must be between ₹10,000 and ₹2,00,00,000           |
      | Interest rate | 30.01     | Interest rate must be between 0% and 30%                       |
      | Interest rate | -1        | Interest rate must be between 0% and 30%                       |
      | Interest rate | 10%       | Interest rate must be a number                                 |
      | Interest rate | 10,5      | Interest rate must be a number                                 |
      | Interest rate | 1e1       | Interest rate must be a number                                 |
      | Loan tenure   | 0         | Loan tenure must be between 1 and 30 years                     |
      | Loan tenure   | 31        | Loan tenure must be between 1 and 30 years                     |
      | Loan tenure   | 2.5       | Loan tenure must be a whole number                             |
      | Loan tenure   | 5.0       | Loan tenure must be a whole number                             |
      | Loan tenure   | 1e1       | Loan tenure must be a whole number                             |
      | Loan tenure   | 1,5       | Loan tenure must be a whole number                             |

  # A decimal amount where rounding the slices separately used to make the interest
  # slice ₹1 smaller than the Total interest card
  Scenario: Chart slices match the summary cards for a decimal amount
    When I enter loan amount "1000000.50", interest rate "7" and tenure "1" years
    Then the chart slices equal the principal and the total interest shown

  @allow_http_errors
  Scenario: A server failure is shown to the user
    Given the calculation service is failing
    When I enter loan amount "1000000", interest rate "10.5" and tenure "5" years
    Then I see the page message "Something went wrong, please try again"
    And no EMI result is shown

  Scenario: No report is offered for invalid input
    When I enter "abc" in the "Loan amount" field
    Then the amortization report link is disabled

  Scenario: Navigating from the dashboard to the report keeps the loan details
    When I enter loan amount "2500000", interest rate "9" and tenure "20" years
    And I open the amortization report from the dashboard
    Then the "Amortization report" heading is visible
    And the report shows the loan "₹25,00,000" at "9%" for "20" years
