# Project Plan: QA Automation Assignment

Status: **Approved and built 2026-10-06.** Self-healing POC: Option A (rule-based) built, Option B (LLM) documented in docs/SELF_HEALING.md.

**Decided:** 0% interest allowed; Indian number format; API validation checks marked `xfail` (known defect); SQL edge rules use the defaults in section 7; commits use your personal git identity for this repo only.

---

## 1. Requirement checklist

| # | Requirement | Where it is covered |
|---|---|---|
| F1 | Framework, not a script: feature + step + page (POM) files | `features/`, `steps/`, `pages/` |
| F2 | Environment config, no hardcoded URLs | `config/.env.<env>` loaded by `config/settings.py` |
| F3 | Resilient locators (role / label / text / data-testid) | All page objects |
| F4 | 3-5 deliberately broken locators, left broken | `pages/broken_locators.py` + `@self_healing` feature |
| F5 | Markdown on AI self-healing (detect, prompt, validate) + optional POC | `docs/SELF_HEALING.md`, `healing/` |
| A1 | Web app: dashboard, user-driven report, chart | `app/` (Flask) |
| A2 | UI tests: load, input → output vs independent expected value, chart has valid data | `features/dashboard.feature`, `features/report.feature` |
| A3 | API tests: long strings, special chars, missing fields | `features/api_posts.feature` |
| A4 | SQL: round-trip transfers, IPL streaks, schema + output screenshots | `sql/` |
| S1 | README: setup, how to run, architecture | `README.md` |
| S2 | Claude Code reflection | `README.md` section (written by you) |
| S3 | Execution results committed (report, screenshots, logs) | `reports/` |

---

## 2. Tools

| Purpose | Tool |
|---|---|
| Language | Python 3.12 |
| Browser automation | Playwright for Python (`pytest-playwright`) |
| BDD (Cucumber equivalent) | `pytest-bdd` (Gherkin `.feature` files) |
| Runner | `pytest` |
| Config | `python-dotenv` |
| Reports | `pytest-html` (self-contained HTML) + screenshots + Playwright traces |
| API tests | Playwright `APIRequestContext` |
| Web app | Flask + plain HTML/JS + Chart.js (bundled locally, no CDN at test time) |
| SQL | SQLite via Python's built-in `sqlite3` |

Everything runs inside a project virtual environment (`.venv`). No global installs.

---

## 3. Repository layout

```
emi-qa-automation/
├── app/                        # A1: the web app under test
│   ├── server.py               # Flask routes: /, /report, /api/emi, /api/schedule
│   ├── emi.py                  # EMI + amortization math (app side)
│   ├── templates/              # dashboard.html, report.html
│   └── static/                 # app.js, styles.css, chart.umd.js
├── features/                   # Gherkin scenarios
│   ├── dashboard.feature
│   ├── report.feature
│   ├── api_posts.feature
│   └── self_healing.feature    # uses the broken locators
├── steps/                      # step definitions
│   ├── test_dashboard_steps.py
│   ├── test_report_steps.py
│   ├── test_api_posts_steps.py
│   └── test_self_healing_steps.py
├── pages/                      # Page Object Model
│   ├── base_page.py
│   ├── dashboard_page.py
│   ├── report_page.py
│   └── broken_locators.py      # F4: intentionally broken
├── api/
│   └── posts_client.py         # wraps POST /posts
├── utils/
│   └── emi_oracle.py           # independent expected-value calculator (never imports app/)
├── healing/                    # optional self-healing POC
├── config/
│   ├── settings.py
│   ├── .env.local
│   └── .env.ci
├── sql/
│   ├── schema.sql, seed.sql
│   ├── scenario1_round_trip.sql
│   ├── scenario2_ipl_streaks.sql
│   └── screenshots/
├── reports/                    # committed test results
├── docs/SELF_HEALING.md
├── conftest.py                 # fixtures: settings, app server, browser page, API context, hooks
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 4. A1: The web app (I build this)

**Dashboard (`/`)**
- Inputs with sliders: Loan amount, Interest rate (% p.a.), Tenure (years).
- Result cards: Monthly EMI, Total interest, Total payment.
- Pie chart: principal vs. interest.
- Validation messages for out-of-range input.

**Report (`/report`)**
- Amortization schedule table: Year/Month, Principal paid, Interest paid, Closing balance.
- User-driven controls: Yearly/Monthly view toggle, From-year/To-year filter.
- Bar chart: principal vs. interest per year.
- Totals row.

**Testability built in:** every key element has a proper `<label>`, an ARIA role and a `data-testid`. Chart values are exposed through `data-*` attributes on the chart container, so tests can read the real numbers rather than pixels.

Proposed input ranges **[DECIDE]**:

| Field | Min | Max | Default |
|---|---|---|---|
| Loan amount | 10,000 | 2,00,00,000 | 10,00,000 |
| Interest rate | 1% | 30% | 10.5% |
| Tenure | 1 year | 30 years | 5 years |

- Allow 0% interest? (EMI = P / n, a classic edge case.) **[DECIDE]**
- Show currency as Indian format (10,00,000) like emicalculator.net? **[DECIDE]**

---

## 5. A2: UI scenarios (DRAFT: your QA input needed here)

Expected values come from `utils/emi_oracle.py`, written separately from the app.
The Examples tables also carry values you verify by hand on emicalculator.net, so there are two independent checks.

```gherkin
Feature: EMI dashboard

  Scenario: Dashboard loads with default values
    Given I open the EMI dashboard
    Then the page title is "EMI Calculator"
    And the summary cards for EMI, total interest and total payment are visible
    And the principal vs interest chart is visible

  Scenario Outline: EMI is calculated correctly
    Given I open the EMI dashboard
    When I enter loan amount <amount>, interest rate <rate> and tenure <years> years
    Then the monthly EMI shown matches the independently calculated EMI
    And the monthly EMI shown is "<expected_emi>"
    And total payment equals EMI x number of months

    Examples:
      | amount  | rate | years | expected_emi |
      | 1000000 | 10.5 | 5     | 21,494       |
      | 500000  | 8.5  | 3     | 15,784       |
      | 2500000 | 9    | 20    | 22,493       |
      | 100000  | 12   | 1     | 8,885        |

  Scenario: Chart reflects the calculated values
    Given I open the EMI dashboard
    When I enter loan amount 1000000, interest rate 10.5 and tenure 5 years
    Then the chart has 2 segments with values greater than 0
    And the chart segments add up to the total payment

  Scenario Outline: Invalid input is rejected
    Given I open the EMI dashboard
    When I enter "<value>" in the "<field>" field
    Then I see the validation message "<message>"

    Examples: (to be filled by you)
```

```gherkin
Feature: Amortization report

  Scenario: Report loads with one row per year
  Scenario: Monthly view shows tenure x 12 rows
  Scenario: Year filter limits the rows shown
  Scenario: Principal column sums to the loan amount and the final balance is 0
  Scenario: Bar chart has one positive bar pair per year
```

The four sample EMIs above are my calculations. **Please verify them on emicalculator.net.**

---

## 6. A3: API tests

**Already observed** (manual probe on 2026-10-06):

| Input | Actual response |
|---|---|
| Missing `userId` | 201 Created |
| `userId: "abc"` (wrong type) | 201 Created |
| Empty body `{}` / array `[]` | 201 Created |
| `<script>`, emoji, `\u0000` in title | 201 Created, echoed back unchanged |
| 1M and 5M character title | 201 Created |
| ~11M character title | **500** `PayloadTooLargeError` + stack trace (should be 413) |
| Malformed JSON | **500** `SyntaxError` + stack trace (should be 400) |

JSONPlaceholder is a mock: it has no validation, and it does not persist anything.
The assignment's expected outcome (4xx for invalid input) **cannot be met by this API.**

**Proposed approach:** two layers of assertions per case.
1. **Robustness (must pass):** no 5xx, no stack trace in the body, the response time is within a limit, and input is echoed back without corruption.
2. **Validation (spec expectation):** invalid input → 4xx. These fail against JSONPlaceholder and are reported as defects.

**[DECIDE]** How should the validation failures show up in the report?
- (a) Leave them as real **failures**: honest, but the suite is red.
- (b) Mark them `xfail` (expected failure) with a defect note: the suite is green, the report still shows each one as "XFAIL: known defect". **(Recommended)**

Special-character set (proposed): HTML/script tags, SQL-injection string, emoji, RTL text, null byte / control characters, unicode accents, CJK characters. **Add or remove as you like.**

---

## 7. A4: SQL

**Scenario 1: round-trip transfers**

```
transactions(txn_id, from_account, to_account, amount, txn_time)
```
Self-join: B→A after A→B, within 24 hours, amount within 10%.

**Scenario 2: IPL streaks**

```
players(player_id, player_name, team)
matches(match_id, match_date, season)
batting_scores(match_id, player_id, runs)
```
Gaps-and-islands with window functions (`ROW_NUMBER` difference) → players with 3+ consecutive 30+ scores, plus the streak start date.

**Edge cases built into the seed data. [DECIDE] the rule for each:**

| Question | My default |
|---|---|
| Is "within 10%" measured against the original amount? | Yes: `ABS(b - a) <= 0.10 * a` |
| Does exactly 10% count? | Yes (inclusive) |
| Does exactly 24h count? | Yes (inclusive) |
| Must the return transfer come after the original? | Yes |
| "Consecutive matches" = consecutive matches the **player** played (skipping matches they missed)? | Yes |
| Player with two separate streaks → two rows? | Yes |
| Exactly 30 runs counts as 30+? | Yes |

**Screenshots:** a script runs each query and saves a PNG of the output (through Playwright), plus `.txt` output. You can also re-run them in an online compiler (for example sqliteonline.com) for screenshots you take yourself.
**Bonus:** pytest tests that assert each query returns exactly the expected rows from the seed data.

---

## 8. Self-healing

**Broken locators (4)** in `pages/broken_locators.py`, each a different kind of anti-pattern:
1. Positional XPath: `/html/body/div[2]/main/section[1]/div[3]/span`
2. Positional CSS: `div.cards > div:nth-child(1) > span`
3. Stale ID that was "renamed": `#emiValueOld`
4. Auto-generated class: `.css-1x8k2qz`
5. (optional) Wrong text: `text=Calculate EMI Now`

They are used only by `features/self_healing.feature` (tag `@self_healing`). The tag is excluded from the default run, so the main suite stays clean.

**`docs/SELF_HEALING.md` covers:**
- **Detection:** catch `TimeoutError` / zero-match / multiple-match failures in a locator wrapper.
- **Context capture:** failed selector, its intent ("monthly EMI value"), the accessibility tree, the DOM snippet near the last known location.
- **Prompt approach:** ask the LLM to return a ranked list of role/label/testid locators in strict JSON, with a reason for each.
- **Validation before applying:** each candidate must match exactly 1 element, be visible, have the expected role, and the test step must pass with it. Then it is logged, **never auto-committed**: the healer writes a suggested patch for a human to approve.

**POC [DECIDE]:**
- (a) Rule-based healer (no API key): scores DOM candidates by similarity to the broken locator's intent. **(Recommended to start)**
- (b) Add an LLM mode on top of (a), using your own API key in a local `.env` (never committed).

---

## 9. Environment config

`ENV=local pytest` loads `config/.env.local`:

```
BASE_URL=http://127.0.0.1:5000
API_BASE_URL=https://jsonplaceholder.typicode.com
HEADLESS=true
BROWSER=chromium
DEFAULT_TIMEOUT_MS=10000
START_APP=true          # conftest starts the Flask app automatically
```

---

## 10. Reports committed to `reports/`

- `reports/report.html`: pytest-html, self-contained
- `reports/screenshots/`: key steps + every failure
- `reports/traces/`: Playwright trace on failure (open with `playwright show-trace`)
- `reports/console.log`: full console output of the run
- `sql/screenshots/`: SQL query outputs

---

## 11. Build order and review checkpoints

| Step | What | You review |
|---|---|---|
| 1 | Project setup, venv, config, empty framework skeleton | Structure |
| 2 | Build the web app | Use it in the browser |
| 3 | Feature files (from your scenarios) | **Your scenarios** |
| 4 | Page objects + step definitions, first green run | Locators |
| 5 | Report feature + chart checks | Results |
| 6 | API tests | Assertion approach |
| 7 | SQL schema, seed, queries, screenshots | Edge-case rules |
| 8 | Broken locators + SELF_HEALING.md + POC | Write-up |
| 9 | Full run, commit reports, README | README |
| 10 | Your Claude Code reflection, then push to **your personal GitHub** | Everything |

I keep a running `docs/CLAUDE_LOG.md` of what we did, what I got wrong and what you corrected. That gives you real material for your reflection.

---

## 12. GitHub (decided)

- The repository is uploaded by hand through the GitHub website to my personal account.
- Claude Code makes no commits and no pushes.

---

## 13. What I need from you

1. Answers to the **[DECIDE]** items (sections 4, 6, 7, 8, 12).
2. Your UI scenarios, especially invalid-input cases (section 5).
3. Verification of the four sample EMIs on emicalculator.net.
4. Any additions to the API special-character list.
