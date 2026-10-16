@ui
Feature: Amortization report
  As a borrower
  I want a year-by-year breakdown of my repayments
  So that I can see how much principal and interest I pay over time

  @smoke
  Scenario: Report loads with one row per year
    Given I open the amortization report for loan "1000000" at "10.5" for "5" years
    Then the "Amortization report" heading is visible
    And the schedule table shows 5 rows
    And every row matches the independently calculated schedule
    And the page loaded without browser errors

  Scenario: Schedule totals are consistent
    Given I open the amortization report for loan "1000000" at "10.5" for "5" years
    Then the principal column adds up to the loan amount
    And the closing balance of the last row is 0
    And the totals row matches the sum of the rows

  Scenario: Monthly rows add up exactly to the totals row
    Given I open the amortization report for loan "250000" at "7" for "10" years
    When I switch to the "Monthly" view
    Then the schedule table shows 120 rows
    And the totals row matches the sum of the rows

  Scenario: Monthly view shows one row per month
    Given I open the amortization report for loan "500000" at "8.5" for "3" years
    When I switch to the "Monthly" view
    Then the schedule table shows 36 rows
    And the first row is "Month 1 (Year 1)"

  Scenario Outline: Year filter limits the rows shown
    Given I open the amortization report for loan "2500000" at "9" for "20" years
    When I filter the report from year <from> to year <to>
    Then the schedule table shows <rows> rows
    And the first row is "Year <from>"

    Examples:
      | from | to | rows |
      | 1    | 1  | 1    |
      | 5    | 10 | 6    |
      | 18   | 20 | 3    |

  @allow_http_errors
  Scenario: A server failure on the report is shown to the user
    Given the schedule service is failing
    And I open the amortization report for loan "1000000" at "10.5" for "5" years
    Then the loan details show "Something went wrong, please try again"

  Scenario: From year after To year is rejected
    Given I open the amortization report for loan "1000000" at "10.5" for "5" years
    When I filter the report from year 4 to year 2
    Then I see the report filter message "From year must not be after To year"

  Scenario: Bar chart shows positive principal and interest for every year
    Given I open the amortization report for loan "1000000" at "10.5" for "5" years
    Then the yearly chart has a bar for each of the 5 years
    And every principal and interest bar in the chart is greater than 0
    And the chart values match the schedule table
