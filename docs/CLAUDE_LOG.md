# Claude Code working log

A factual record of how Claude Code was used on this project: what it did, what it
got wrong, and what was corrected. Raw material for the README reflection.

## Process

| # | What happened | Outcome |
|---|---|---|
| 1 | Claude started scaffolding (in TypeScript/Node) before I had confirmed the plan or the language. I stopped it. | Agreed to plan first. Claude wrote `PLAN.md`, I answered the open decisions, then it built. The Node scaffold was deleted. |
| 2 | I only know Python + Playwright. | Switched to Python: `pytest-bdd` as the Cucumber equivalent (same Gherkin `.feature` files). |
| 3 | Decisions I made: 0% interest allowed, Indian number format, API validation checks as `xfail` known defects, SQL edge rules (inclusive 10% / 24h, return strictly after, consecutive = matches the player batted in), rule-based healer with the LLM approach documented. | Recorded in `PLAN.md`; each one is visible in the code or the feature files. |

## My QA review of Claude's tests

| # | What I found | Change |
|---|---|---|
| 1 | Title length tests covered only the upper boundary (255, 256) and extreme values. Boundary value analysis needs the lower boundary too. | Added 0 (empty, invalid) and 1 (shortest valid), plus 254 (just below the max). Length -1 is not possible for text, so 0 is the lowest boundary. |
| 2 | The "no server error" check also ran for valid lengths, which is redundant: a 201 already proves there was no server error. | Valid lengths (1, 254, 255) are checked once: accepted and stored intact. Robustness is checked only for invalid lengths. |
| 3 | The validation check accepted any 4xx. A user also needs to know *why* the input was rejected. | Invalid lengths must return 4xx **and** a message that names the title and explains the length problem. The 255 limit is documented as an assumption, since JSONPlaceholder has no spec. |

| 4 | Claude's design split every invalid input into a separate "doesn't crash" test and a "is rejected" test. That is redundant: a negative test's failure reason already shows whether the server crashed (500) or accepted the input (201). | Reorganised A3 into three categories: **positive** (valid input accepted), **negative** (invalid input rejected with 4xx + clear message, without crashing) and **stress** (the ~11 MB body above the server limit). Each negative test checks "no crash" first, so the failure reason names the worst problem. Tags `@positive`, `@negative`, `@stress` run each category on its own. |
| 5 | The special-character Examples tables listed only labels ("emoji", "a null byte"); the real values were hidden in a Python dictionary in the step file, so a reader of the feature file could not see the test data. | The Examples tables now show the actual titles (`type` + `title` columns). Invisible characters are written as `\uXXXX` codes and converted by the step. The Python dictionary was removed: the feature file is the single source of test data. |
| 6 | SQL scenario 1 required the return to be *strictly after* the original. The question only says "within a 24-hour window", so two transfers at the same second were wrongly excluded. Claude had used strict `>` to avoid reporting the same pair twice, which was the wrong fix. | Same-second transfers now count; the tie is broken by `txn_id`, so the pair is reported once. |
| 7 | Asked what happens with overlapping transfers (A→B, A→C, B→A; A→B, B→A, B→A, A→B; a return more than 24h after the first transfer). Running them showed the query reports every qualifying pair, reuses transactions across pairs, and measures the 24h window per pair. | Chose to report every pair (detection use case) and documented it. Added all three cases to the seed data and tests. |
| 8 | Asked whether the app was perfect and the calculations correct. Probing edge cases found a real bug and several smaller issues in Claude's app (next table, #9 to #11). | Wrote failing tests first, then fixed the app: all new tests failed before the fix and pass after it. |
| 9 | Found by hand that `1000,000` was accepted and calculated as ₹10,00,000, although it is neither Indian nor international format. Claude had recommended leaving this "lenient" input and documented it as intended. The same leniency turned an interest rate of `10,5` into 105. | Strict formats: amount accepts plain, Indian or international grouping; rate plain numbers; tenure whole numbers (`5.0` rejected). Clear format messages. 12 test cases failed before the fix and pass after. |
| 10 | Error messages were inconsistent: some had examples ("like 10.5"), some mixed two problems in one message ("must be a whole number between 1 and 30 years" for both `2.5` and `31`), one used "cannot" instead of "must". | One standard for every message: `<Field> <rule>` (required / format / range / relation), field names as shown on screen, no examples. Messages are generated from the patterns in code, and format and range problems now get separate messages. |
| 13 | A second code review after the simplification found 9 more issues, including one the simplification introduced: the SQL screenshot retry had been removed while a failed screenshot now fails the whole run. Others: no message when the server fails, pie slice ₹1 off the Total interest card for decimal amounts, wrong default port for https, only the first year-filter error reported, duplicate yearly data, and the browser-error check running in only two scenarios. | Tests first (all failed before), then fixes. Summary values are rounded once on the server; server failures show a message; every UI scenario is checked for browser errors (a mutation with an injected JavaScript error is now caught). |

## Where Claude was wrong (and how it was caught)

| # | Mistake | How it was caught | Fix |
|---|---|---|---|
| 1 | Guessed an expected EMI of ₹55,973 for ₹2 crore at 0.05% / 30 years. | Ran the independent oracle before trusting the table: ₹55,974. | Corrected the Examples row. This is why expected values are double-checked. |
| 2 | Assumed Playwright treats any selector starting with `/` as XPath. It only auto-detects `//` and `..`. | The "broken" XPath failed with a CSS **parse error**, not "element not found": it was broken for the wrong reason. | Added the `xpath=` prefix. Now it fails with a timeout, like a real stale locator. |
| 3 | Report hook read `page` from `item.funcargs`. pytest-bdd requests step fixtures lazily, so they never appear there. | No screenshots were produced after the first run. | The `ui_page` fixture stores the page in `item.stash`; the hook reads it from there. |
| 4 | Put a shared step ("the monthly EMI shown is…") in one feature's step file. | `StepDefinitionNotFoundError` in the self-healing feature. | Moved shared steps to `steps/conftest.py`. |
| 5 | First `xfail` design would mark *any* exception as the known defect, so a network outage would look like an "expected failure". | Reviewed what `xfail` actually swallows. | `xfail(..., strict=True, raises=AssertionError)`: only a failed assertion counts. `strict` turns an unexpected pass into a failure. |
| 6 | `run_tests.sh` ran three pytest sessions with the same `--output` folder. pytest-playwright empties that folder at the start of each session, so the healed run deleted the traces of the failing run. | `reports/artifacts/` was missing after a full run. | Each session gets its own `--output` folder. |
| 7 | Started lines in a feature description with `@positive` / `@negative`. Gherkin reads any line beginning with `@` as a tag, so the file failed to parse. | Collection error "A tag may not contain whitespace". | Reworded the description lines. |
| 8 | The app's `/api/schedule` crashed with **500** on a non-numeric year filter (`from_year=abc`): the same kind of defect reported against JSONPlaceholder (JP-02). | Edge-case probing after I asked whether the app was perfect. The UI could not send it (dropdowns), so no UI test could catch it. | Year filters and the view are validated and rejected with 400 + a clear message. New app API tests (`emi_api.feature`). |
| 9 | Claude wrote the report tests with a **rounding tolerance**, so rows that did not add up to the totals row still passed. The tests hid a visible inconsistency instead of reporting it (up to ₹35 on monthly schedules). | Checking 240 loan combinations: 116 yearly and more monthly schedules did not add up. | Tests made exact. The app rounds running totals so rows always add up. A second check over 336 loans found 2 more mismatches at exactly ₹0.50 (0% interest, odd amount); yearly rows are now built from the rounded months. |
| 10 | Out-of-range years gave a misleading message ("From year cannot be after To year" for Year 10 on a 5-year loan); an unknown `view` was silently treated as yearly; no tab icon (404). | Same probing. The favicon could not be caught by browser tests: headless Chrome never requests it. | Clear messages; unknown view rejected; icon added and checked at the HTTP level. |
| 11 | Wrote junk code twice (a nonsensical regex expression; a `"amount" if False else ""` entry in a set). | Read back the code before running it. | Rewritten cleanly. |
| 12 | Code review of the whole project (after I asked for a review and simplification) found more defects in Claude's own code: the year filter still crashed (500) on Unicode digits such as `²` because `str.isdigit()` accepts them; the "strict" number formats accepted Arabic-Indic digits (`\d` matches every script); a slow, older response could overwrite a newer result; a non-JSON reply left the page stuck "loading"; the report link kept pointing at the last valid loan after an error; `run_tests.sh` ignored failures of the healer and SQL runs. | One validation rule object per field (format, range and message built from the same bounds); ASCII-only digit patterns; only the latest response may update the page; errors are reset on failure; the broken-locator scenarios became strict expected failures (`xfail`, timeout only), so every run's exit code counts. A new UI test covers the report link, and a mutation check showed a locator broken for the wrong reason now fails the run. |

## Traps avoided by checking instead of assuming

| # | Trap | What was done |
|---|---|---|
| 1 | The assignment expects JSONPlaceholder to reject invalid posts with 4xx. | Probed the API by hand first: it accepts everything (201) and returns **500 + stack trace** for malformed JSON and bodies over ~10 MB. Tests were designed around the real behavior; the gaps are reported as defects JP-01 / JP-02. |
| 2 | "Total payment = EMI × months" is false on screen: the EMI is rounded (₹21,494 × 60 = ₹12,89,640, but the true total is ₹12,89,634). | Assert total payment = principal + total interest, and compare each value with the oracle. |
| 3 | All 30 UI tests passed on the first run, which can mean the tests check nothing. | Mutation check: changed the app's EMI formula (`/100` → `/100.5`); 9 tests failed; reverted. |
| 4 | Expected values computed with the same code as the app prove nothing. | `utils/emi_oracle.py` is written separately with `Decimal` math and never imports `app/`. |
| 5 | `get_by_label("Loan amount")` would also match the "Loan amount slider". | `exact=True` on label locators. |
| 6 | Floating-point "within 10%" can fall a hair either side of the boundary. | Money stored as integer cents; the condition is integer math: `ABS(back - sent) * 10 <= sent`. |
| 7 | Headless Chromium failed the very first SQL screenshot once ("Unable to capture screenshot"). | Re-ran 3 times (all passed); added one retry around the capture. |

## What worked well

- Turning the requirements into a checklist (`PLAN.md`) before writing code
- Generating the app, the framework skeleton and the seed data quickly, with edge cases built in on purpose
- Explaining unfamiliar parts: pytest-bdd hooks, gaps-and-islands window functions, Playwright's `aria_snapshot`
- Debugging from evidence (printing what the hook sees) instead of guessing
