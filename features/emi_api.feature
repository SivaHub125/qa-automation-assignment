@app_api
Feature: EMI Insights JSON API (the app's own backend)
  The dashboard and report pages call these endpoints. Valid requests are
  calculated; invalid ones are rejected with 400 and a clear message, and the
  server never crashes (5xx).

  @positive
  Scenario: The EMI endpoint calculates a valid loan
    When I request the EMI for loan "1000000" at "10.5" for "5" years
    Then the server does not crash
    And the response status is 200
    And the monthly EMI returned rounds to 21494 rupees

  # Headless browsers never request a tab icon, so this is checked at the HTTP level
  @positive
  Scenario: The app serves a tab icon
    When I request the path "/favicon.ico"
    Then the response status is 200

  @negative
  Scenario Outline: The schedule rejects the year filter <from_year> to <to_year>
    When I request the "yearly" schedule for loan "1000000" at "10.5" for "5" years from year "<from_year>" to year "<to_year>"
    Then the server does not crash
    And the response status is 400
    And the error message is "<message>"

    Examples:
      | from_year | to_year | message                             |
      | abc       | 5       | From year must be a whole number    |
      | 1         | xyz     | To year must be a whole number      |
      | 2.5       | 4       | From year must be a whole number    |
      | 0         | 5       | From year must be between 1 and 5   |
      | 1         | 6       | To year must be between 1 and 5     |
      | 10        | 10      | From year must be between 1 and 5   |
      | 4         | 2       | From year must not be after To year |

  @negative
  Scenario: Both invalid year filters are reported together
    When I request the "yearly" schedule for loan "1000000" at "10.5" for "5" years from year "abc" to year "xyz"
    Then the server does not crash
    And the response status is 400
    And the error message is "From year must be a whole number"
    And the error message is "To year must be a whole number"

  @positive
  Scenario: The yearly schedule is sent only once
    When I request the "yearly" schedule for loan "1000000" at "10.5" for "5" years from year "1" to year "5"
    Then the response status is 200
    And the response has 5 rows and no separate yearly list

  @negative
  Scenario: The schedule rejects an unknown view
    When I request the "weekly" schedule for loan "1000000" at "10.5" for "5" years from year "1" to year "5"
    Then the server does not crash
    And the response status is 400
    And the error message is "View must be yearly or monthly"

  # Every displayed amount is rounded to whole rupees. The rows must still add up
  # exactly to the totals row. These loans used to be off by up to ₹35.
  @positive
  Scenario Outline: <view> schedule rows add up exactly to the totals for <amount> at <rate>% over <years> years
    When I request the "<view>" schedule for loan "<amount>" at "<rate>" for "<years>" years from year "1" to year "<years>"
    Then the response status is 200
    And the principal, interest and payment columns add up exactly to the totals
    And every row's payment equals its principal plus its interest
    And the principal total equals the loan amount
    And each row's balance equals the previous balance minus the row's principal

    Examples:
      | view    | amount  | rate | years |
      | yearly  | 250000  | 7    | 5     |
      | monthly | 250000  | 7    | 10    |
      | monthly | 250000  | 7    | 3     |
      | yearly  | 1000000 | 10.5 | 5     |
      | monthly | 2500000 | 9    | 20    |
