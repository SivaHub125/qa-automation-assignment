"""Rule-based self-healing locator POC (Option A: no AI model, no API key).

Flow for every locator lookup:
  1. DETECT    run the original selector; exactly one match means healthy, return it.
  2. CAPTURE   collect visible, meaningful elements from the live DOM with their
               role, accessible name, label, data-testid, id and text.
  3. RANK      score each candidate against the locator's intent and the tokens
               left in the broken selector (ids, classes, text).
  4. VALIDATE  for the best candidates, build resilient Playwright locators
               (role+name > label > test id > text) and accept the first one that
               is unique, visible, is the same element, has the expected role
               and text shape.
  5. REPORT    record the result in reports/self_healing/. Source files are never
               edited: a human reviews the suggested replacement and applies it.

The LLM version (Option B) replaces step 3 with a model call; see docs/SELF_HEALING.md.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from playwright.sync_api import Locator, Page

COLLECT_CANDIDATES_JS = """
() => {
  const implicitRole = (el) => {
    const tag = el.tagName.toLowerCase();
    if (el.getAttribute('role')) return el.getAttribute('role');
    if (tag === 'button') return 'button';
    if (tag === 'a' && el.hasAttribute('href')) return 'link';
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (/^h[1-6]$/.test(tag)) return 'heading';
    if (tag === 'input') {
      const type = (el.getAttribute('type') || 'text').toLowerCase();
      return { range: 'slider', checkbox: 'checkbox', radio: 'radio', submit: 'button',
               button: 'button' }[type] || 'textbox';
    }
    return null;
  };
  const textOf = (ids) => ids.split(/\\s+/).map(id => document.getElementById(id)?.innerText || '')
                              .join(' ').trim();
  const accessibleName = (el) =>
    el.getAttribute('aria-label') ||
    (el.getAttribute('aria-labelledby') && textOf(el.getAttribute('aria-labelledby'))) ||
    (el.labels && el.labels[0] && el.labels[0].innerText.trim()) ||
    (['button', 'a'].includes(el.tagName.toLowerCase()) ? el.innerText.trim() : '') || '';
  const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);

  const selector = 'input, button, a, select, textarea, [data-testid], [role], h1, h2, h3, p, span, td';
  window.__healCandidates = [...document.querySelectorAll(selector)].filter(visible);
  return window.__healCandidates.map((el, index) => ({
    index,
    tag: el.tagName.toLowerCase(),
    role: implicitRole(el),
    name: accessibleName(el).slice(0, 80),
    label: (el.labels && el.labels[0] && el.labels[0].innerText.trim()) || '',
    testid: el.getAttribute('data-testid') || '',
    id: el.id || '',
    text: (el.innerText || el.value || '').trim().slice(0, 80),
  }));
}
"""

# Words in selectors that carry no meaning about *which* element is wanted.
NOISE = {
    "html", "body", "div", "span", "main", "section", "nth", "child", "css", "text",
    "class", "now", "old", "new",
}
ABBREVIATIONS = {"btn": "button", "lnk": "link", "txt": "text", "amt": "amount"}


def tokens(value: str) -> set[str]:
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value or "")  # split camelCase
    words = re.findall(r"[a-zA-Z]{3,}", value.lower())
    return {ABBREVIATIONS.get(w, w) for w in words} - NOISE


@dataclass
class HealingRecord:
    key: str
    broken_selector: str
    anti_pattern: str
    intent: str
    status: str                       # healthy | healed | not_healed | disabled
    healed_locator: str | None = None
    score: float | None = None
    candidates_considered: int = 0
    validation: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)

    @classmethod
    def for_spec(cls, spec, status: str, **details) -> "HealingRecord":
        return cls(spec.key, spec.selector, spec.anti_pattern, spec.intent, status, **details)


class LocatorHealer:
    def __init__(self, page: Page, enabled: bool, report_dir: Path, top_n: int = 5):
        self.page = page
        self.enabled = enabled
        self.report_dir = report_dir
        self.top_n = top_n
        self.records: list[HealingRecord] = []

    # ---- 1. detect ------------------------------------------------------
    def find(self, spec) -> Locator:
        original = self.page.locator(spec.selector)
        if original.count() == 1:
            self.records.append(HealingRecord.for_spec(spec, "healthy"))
            return original
        if not self.enabled:
            self.records.append(HealingRecord.for_spec(spec, "disabled"))
            return original  # left broken: the test fails exactly as it would without healing
        return self._heal(spec, original)

    # ---- 2-4. capture, rank, validate -------------------------------------
    def _heal(self, spec, original: Locator) -> Locator:
        candidates = self.page.evaluate(COLLECT_CANDIDATES_JS)
        intent, from_selector = tokens(spec.intent), tokens(spec.selector)
        scored = sorted(
            ((self._score(spec, intent, from_selector, c), c) for c in candidates),
            key=lambda pair: pair[0], reverse=True,
        )
        record = HealingRecord.for_spec(spec, "not_healed", candidates_considered=len(candidates))
        self.records.append(record)
        for score, candidate in scored[: self.top_n]:
            for code, locator in self._strategies(candidate):
                ok, notes = self._validate(spec, candidate, locator)
                if ok:
                    record.status, record.healed_locator = "healed", code
                    record.score, record.validation = round(score, 2), notes
                    return locator
                record.rejected.append(f"{code}: {'; '.join(notes)}")
        return original

    def _score(self, spec, intent: set[str], from_selector: set[str], c: dict) -> float:
        cand = tokens(" ".join([c["testid"], c["id"], c["name"], c["label"]]))
        score = 3 * len(intent & cand) / max(len(intent), 1)
        score += 1 * len(from_selector & cand) / max(len(from_selector), 1)
        score += 2 * SequenceMatcher(None, spec.intent.lower(), (c["name"] or c["testid"]).lower()).ratio()
        if spec.role:
            score += 2 if c["role"] == spec.role else -2
        if spec.value_pattern and not re.search(spec.value_pattern, c["text"]):
            score -= 3
        return score

    def _strategies(self, c: dict):
        """Resilient locator options for one candidate, most user-facing first."""
        page = self.page
        if c["role"] and c["name"]:
            yield (f'page.get_by_role("{c["role"]}", name="{c["name"]}", exact=True)',
                   page.get_by_role(c["role"], name=c["name"], exact=True))
        if c["label"]:
            yield (f'page.get_by_label("{c["label"]}", exact=True)',
                   page.get_by_label(c["label"], exact=True))
        if c["testid"]:
            yield (f'page.get_by_test_id("{c["testid"]}")', page.get_by_test_id(c["testid"]))
        if c["text"] and c["tag"] in {"a", "button"}:
            yield (f'page.get_by_text("{c["text"]}", exact=True)', page.get_by_text(c["text"], exact=True))

    def _validate(self, spec, c: dict, locator: Locator) -> tuple[bool, list[str]]:
        notes = []
        count = locator.count()
        if count != 1:
            return False, [f"matches {count} elements, need exactly 1"]
        notes.append("unique (1 match)")
        if not locator.is_visible():
            return False, notes + ["not visible"]
        notes.append("visible")
        same = locator.evaluate("(el, i) => el === window.__healCandidates[i]", c["index"])
        if not same:
            return False, notes + ["resolves to a different element than the ranked candidate"]
        notes.append("same element as ranked candidate")
        if spec.role and c["role"] != spec.role:
            return False, notes + [f"role {c['role']!r} != expected {spec.role!r}"]
        if spec.role:
            notes.append(f"role is {spec.role}")
        if spec.value_pattern:
            text = locator.inner_text()
            if not re.search(spec.value_pattern, text):
                return False, notes + [f"text {text!r} does not match {spec.value_pattern}"]
            notes.append(f"text {text!r} matches expected shape")
        return True, notes

    # ---- 5. report --------------------------------------------------------
    def write_report(self, scenario: str) -> None:
        if not self.records:
            return
        self.report_dir.mkdir(parents=True, exist_ok=True)
        log = self.report_dir / "healing-log.jsonl"
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with log.open("a", encoding="utf-8") as fh:
            for r in self.records:
                fh.write(json.dumps({"time": stamp, "scenario": scenario, **asdict(r)}, ensure_ascii=False) + "\n")
        write_summary(self.report_dir)


def write_summary(report_dir: Path) -> None:
    """Rebuild healing-report.md: the latest result per locator, as suggestions for a human."""
    latest: dict[str, dict] = {}
    for line in (report_dir / "healing-log.jsonl").read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        latest[entry["key"]] = entry
    lines = [
        "# Self-healing report",
        "",
        "Generated by `healing/healer.py`. **Nothing was changed in the source code.**",
        "Review each suggestion, then replace the selector in `pages/broken_locators.py` by hand.",
        "",
        "| Locator | Status | Broken selector | Anti-pattern | Suggested replacement | Score |",
        "|---|---|---|---|---|---|",
    ]
    for e in latest.values():
        lines.append(
            f"| `{e['key']}` | {e['status']} | `{e['broken_selector']}` | {e['anti_pattern']} | "
            f"{'`' + e['healed_locator'] + '`' if e['healed_locator'] else '-'} | {e['score'] or '-'} |"
        )
    lines += ["", "## Validation evidence", ""]
    for e in latest.values():
        lines.append(f"- **{e['key']}** ({e['status']}): " + (", ".join(e["validation"]) or "n/a"))
        for rejected in e["rejected"]:
            lines.append(f"  - rejected: {rejected}")
    (report_dir / "healing-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
