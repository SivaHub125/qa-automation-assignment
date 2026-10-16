@api
Feature: JSONPlaceholder post creation with boundary and invalid data
  POST /posts must accept valid posts, reject invalid ones with a 4xx status and a
  clear error message, and never crash (5xx), whatever it is sent.

  Test categories (run one with: pytest -m positive | negative | stress)
    Positive: valid input is accepted (201) and stored exactly as sent
    Negative: invalid input is rejected with 4xx + a clear message, without crashing
    Stress:   a large payload above the server's own size limit gets 413 + a message, without crashing

  JSONPlaceholder is a mock API with no validation, so the negative and stress
  scenarios fail against it. They are tagged as known defects (strict xfail), and the
  failure reason in the report shows what really happened:
    JP-01  accepted with 201, no validation
    JP-02  crashed with 500 and exposed a stack trace

  Title length assumption: JSONPlaceholder documents no limit, so a valid title is
  assumed to be 1 to 255 characters (a common VARCHAR(255) limit).

  # =============================================================================
  # POSITIVE: valid input is accepted and stored exactly as sent
  # =============================================================================

  @positive
  Scenario: A valid post is created
    When I create a post with title "Boundary testing", body "Checking the baseline" and userId 1
    Then the response status is 201
    And the response echoes the title, body and userId that were sent
    And the response contains a new post id

  # Boundary values inside the valid range (1 to 255)
  @positive
  Scenario Outline: A title of <length> characters is accepted
    When I create a post with a title of <length> characters
    Then the response status is 201
    And the response echoes a title of exactly <length> characters

    Examples:
      | length |
      | 1      |
      | 254    |
      | 255    |

  # Valid text that must be stored literally (never interpreted or altered).
  # In the tables, \\ is one backslash (Gherkin escaping) and \uXXXX is an invisible
  # character written as its Unicode code, e.g. \u0000 = null byte.
  @positive
  Scenario Outline: A title with <type> is stored exactly as sent
    When I create a post with the title "<title>"
    Then the response status is 201
    And the response echoes the title exactly as sent

    Examples:
      | type                   | title                          |
      | SQL injection text     | '; DROP TABLE posts; --        |
      | emoji                  | Loan approved 🎉🏠💰           |
      | right-to-left text     | مرحبا بالعالم שלום             |
      | CJK characters         | ローン計算 贷款 대출            |
      | accented letters       | Crème brûlée à São Paulo       |
      | quotes and backslashes | He said "hi" \\ path\\to\\file |

  # =============================================================================
  # NEGATIVE: invalid input is rejected with 4xx and a clear message, without crashing
  # =============================================================================

  # Boundary values outside the valid range: 0 (below), 256 (above), extreme values
  @negative @known_defect_no_validation
  Scenario Outline: A title of <length> characters is rejected
    When I create a post with a title of <length> characters
    Then the server does not crash
    And the request is rejected with a client error
    And the error message explains that the title length is invalid

    Examples:
      | length  |
      | 0       |
      | 256     |
      | 10000   |
      | 1000000 |

  @negative @known_defect_no_validation
  Scenario Outline: A title with <type> is rejected
    When I create a post with the title "<title>"
    Then the server does not crash
    And the request is rejected with a client error
    And the error message mentions "title"

    Examples:
      | type               | title                         |
      | HTML script tag    | <script>alert('xss')</script> |
      | null byte          | before\u0000after             |
      | control characters | bell\u0007 escape\u001b       |

  @negative @known_defect_no_validation
  Scenario Outline: A post without the required "<field>" field is rejected
    When I create an otherwise valid post without the "<field>" field
    Then the server does not crash
    And the request is rejected with a client error
    And the error message mentions "<field>"

    Examples:
      | field  |
      | userId |
      | title  |
      | body   |

  @negative @known_defect_no_validation
  Scenario: An empty JSON object is rejected
    When I create a post with an empty JSON object
    Then the server does not crash
    And the request is rejected with a client error
    And the error message mentions "required"

  @negative @known_defect_no_validation
  Scenario: A non-numeric userId is rejected
    When I create a post with title "Wrong type", body "userId is text" and userId "abc"
    Then the server does not crash
    And the request is rejected with a client error
    And the error message mentions "userId"

  @negative @known_defect_server_error
  Scenario: A malformed JSON body is rejected
    When I send a malformed JSON body
    Then the server does not crash
    And the request is rejected with a client error
    And the error message mentions "JSON"

  # =============================================================================
  # STRESS (large payload): a body above the server's own size limit (~10 MB)
  # =============================================================================

  @stress @known_defect_server_error
  Scenario: A body of about 11 MB is rejected as too large
    When I create a post with a title of 11000000 characters
    Then the server does not crash
    And the response status is 413
    And the error message mentions "large"
