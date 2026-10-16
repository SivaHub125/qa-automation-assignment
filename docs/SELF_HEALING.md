# Self-healing locators with AI

This document covers the self-healing exercise:

- **The broken locators** left in the test code on purpose
- **How to heal them with AI** (Option B): detection, the prompt, and validation before applying a fix
- **The working POC** (Option A): a rule-based healer that runs today with no API key

---

## 1. The broken locators

They live in [`pages/broken_locators.py`](../pages/broken_locators.py) and are used only by
[`features/self_healing.feature`](../features/self_healing.feature) (tag `@self_healing`, excluded from the default run).

| Key | Broken selector | Anti-pattern | Why it breaks |
|---|---|---|---|
| `loan_amount_input` | `.css-1x8k2qz > input` | Auto-generated CSS-in-JS class | Class hash changes on every build |
| `calculate_button` | `#btnCalculateEMI` | Stale ID | Element renamed; ID no longer exists |
| `emi_value` | `xpath=/html/body/div[2]/main/section[1]/div[3]/span` | Absolute positional XPath | Any new wrapper or reordered parent breaks it |
| `total_interest_value` | `div.cards-grid > div:nth-child(2) > span.amount` | Positional CSS chain | Tied to an old layout and card order |
| `report_link` | `text=View Full Report Now` | Hard-coded outdated text | Copy changed to "View amortization report" |

Each spec also records the element's **intent** in plain words ("Monthly EMI value"), its expected
**role**, and the expected **text shape**. Healing depends on these: a selector string alone says
*where* an element used to be. The intent says *what* it is.

```bash
pytest -m self_healing --html=reports/self-healing-broken.html                  # 5 xfailed: locators are broken
SELF_HEAL=true pytest -m self_healing --html=reports/self-healing-healed.html   # 5 passed: healed at runtime
```

---

## 2. Healing with AI (Option B: design)

```
 test step ──► locator lookup ──► 1 match? ──yes──► continue
                                     │ no
                                     ▼
                           ┌─── 1. DETECT ────┐   0 or >1 matches / TimeoutError
                           │ 2. CAPTURE       │   a11y snapshot + DOM excerpt + intent
                           │ 3. ASK THE LLM   │   strict JSON: ranked candidate locators
                           │ 4. VALIDATE      │   unique, visible, same role/text, step passes
                           │ 5. REPORT        │   suggestion + evidence, human approves
                           └──────────────────┘
```

### 2.1 Detection

Wrap every locator lookup in the page objects (`LocatorHealer.find` in this repo):

| Signal | Meaning |
|---|---|
| `locator.count() == 0` | Element missing: the selector is stale |
| `locator.count() > 1` | Selector is ambiguous: Playwright strict mode would fail |
| `TimeoutError` on an action | Element never became actionable |
| Run history: a locator that passed in the last N runs now fails | Strong hint of a DOM change, not an app bug |

Only locator problems are healed. If the element *is* found but the **value is wrong**
(for example the EMI shows the wrong amount), that is an application defect. It must fail the test,
never be "healed".

### 2.2 Context capture

Send the model only what it needs. That keeps the prompt small and avoids leaking data:

1. The **broken selector**, plus the **intent**, **expected role** and **expected text shape** from the `LocatorSpec`
2. Playwright's **accessibility snapshot** of the page: `page.locator("body").aria_snapshot()`
   gives roles, names and structure in compact YAML
3. A trimmed **DOM excerpt**: elements with `data-testid`, `id`, labels and roles. Strip scripts,
   styles and long text. Mask any user data before sending
4. The **last known good** locator and DOM excerpt from a passing run, if stored

### 2.3 Prompt

```text
SYSTEM:
You repair broken Playwright (Python) locators. Prefer, in this order:
get_by_role(role, name=...), get_by_label(...), get_by_test_id(...), get_by_text(...).
Never return positional CSS (nth-child), absolute XPath, or generated class names.
Answer with JSON only, matching the schema. If no element clearly matches the intent,
return an empty list rather than guessing.

USER:
Broken locator: "xpath=/html/body/div[2]/main/section[1]/div[3]/span"
Intent: "Monthly EMI value"
Expected role: none. Expected text shape: ^₹[\d,]+$
Failure: 0 elements matched.

Accessibility snapshot:
<aria_snapshot YAML>

DOM excerpt:
<trimmed HTML>

Schema:
{"candidates": [{"locator": "page.get_by_test_id(\"emi-value\")",
                 "strategy": "role|label|test_id|text",
                 "confidence": 0.0-1.0,
                 "reason": "one sentence"}]}
Return at most 3 candidates, best first.
```

Rules that make the answer usable:
- **Structured output:** a JSON schema / tool call so the response can be parsed, not scraped from prose
- **Allow-list of strategies:** the response is rejected if a locator is not one of the four `get_by_*` calls.
  Parse it instead of running `eval()` on model output
- **Temperature 0** for repeatable suggestions
- **Cache** by (selector, DOM hash) so the same failure is not sent to the model twice

### 2.4 Validation before applying a fix

A model suggestion is a *hypothesis*. Each candidate must pass all of these, in order:

1. **Parses** into an allowed `get_by_*` call
2. **Unique:** `count() == 1`
3. **Visible** and, for inputs and buttons, **enabled**
4. **Same kind of element:** role matches the expected role; text matches the expected shape
5. **Not a different element with a similar name:** for example the "Monthly EMI" *heading*
   instead of the EMI *value*. Checks 4 and the text shape catch this
6. **The step passes** with the healed locator, and the **rest of the scenario passes** too
7. **Re-run** the scenario a second time with the healed locator to rule out flakiness

### 2.5 Applying the fix: a human stays in charge

- At runtime the healed locator is used **only for that run**, so the run can continue and collect results
- The healer writes a **suggestion report** (broken selector, replacement, evidence). It never edits source files
- The run is marked **"passed with healing"** in the report. It is not a clean pass, so the debt stays visible
- A person reviews the suggestion and updates the page object in a normal code review
- **Guardrails:** cap healed locators per run. If many break at once, it is probably a broken
  deployment, not drift, so fail fast and do not heal

### 2.6 How Option B plugs into this repo

`healing/healer.py` already has the detect → capture → validate → report pipeline.
Option B only replaces the ranking step (`_score` + `_strategies`) with a model call:

1. Put the API key in `config/.env.secrets` (gitignored), for example `ANTHROPIC_API_KEY=...`
2. In `_heal`, send the prompt above with `page.locator("body").aria_snapshot()` instead of ranking DOM candidates locally
3. Map each returned candidate onto the allow-listed `get_by_*` call and pass it through the same `_validate`
4. Fall back to the rule-based ranking when the model is unavailable or returns nothing valid

---

## 3. The working POC (Option A: rule-based, no API key)

[`healing/healer.py`](../healing/healer.py) implements the same pipeline without a model:

| Step | How the POC does it |
|---|---|
| Detect | `count() == 1` check before using the selector |
| Capture | One `page.evaluate` collects visible elements: tag, role, accessible name, label, test id, id, text |
| Rank | Score = overlap of intent words with the candidate's name/label/test id (×3) + overlap with words left in the broken selector (×1) + string similarity (×2) + role match (±2) − text-shape mismatch (3) |
| Validate | For the top 5 candidates, build `get_by_role` → `get_by_label` → `get_by_test_id` → `get_by_text` and accept the first that is unique, visible, the same DOM node as the candidate, the right role and the right text shape |
| Report | `reports/self_healing/healing-log.jsonl` (every lookup) and `healing-report.md` (latest suggestion per locator, with evidence) |

Results from the committed run ([`reports/self_healing/healing-report.md`](../reports/self_healing/healing-report.md)):

| Broken | Healed to |
|---|---|
| `.css-1x8k2qz > input` | `page.get_by_role("textbox", name="Loan amount", exact=True)` |
| `#btnCalculateEMI` | `page.get_by_role("button", name="Calculate", exact=True)` |
| `xpath=/html/body/div[2]/...` | `page.get_by_test_id("emi-value")` |
| `div.cards-grid > div:nth-child(2) > span.amount` | `page.get_by_test_id("total-interest-value")` |
| `text=View Full Report Now` | `page.get_by_role("link", name="View amortization report", exact=True)` |

**Limits of the rule-based approach,** and why an LLM helps:
- It depends on words overlapping. "Pay" vs. "Calculate" would not match, while a model understands synonyms and page context
- The weights are hand-tuned for this app
- It cannot reason about layout ("the value under the Monthly EMI heading")

Option A is still useful as the **fallback** and as the **validation layer** for Option B. The model proposes; deterministic checks decide.
