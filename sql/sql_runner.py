"""Load the SQL schema + seed into SQLite and run the scenario queries.

    python -m sql.sql_runner        # writes sql/results/*.txt and sql/screenshots/*.png
"""

import html
import sqlite3
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent
SCENARIOS = {
    "scenario1_round_trip": "Scenario 1: Round-trip transfers within 24 hours (within 10%)",
    "scenario2_ipl_streaks": "Scenario 2: IPL 2024 players with 30+ runs in 3+ consecutive matches",
}


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.executescript((SQL_DIR / "schema.sql").read_text())
    db.executescript((SQL_DIR / "seed.sql").read_text())
    return db


def run(db: sqlite3.Connection, name: str) -> tuple[list[str], list[tuple]]:
    cursor = db.execute((SQL_DIR / f"{name}.sql").read_text())
    return [c[0] for c in cursor.description], cursor.fetchall()


def as_text(columns, rows) -> str:
    """Format query results as a plain-text table, like a SQL client prints them."""
    cells = [list(columns)] + [[str(value) for value in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(columns))]
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def table_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(width) for value, width in zip(values, widths)) + " |"

    lines = [border, table_row(cells[0]), border, *(table_row(row) for row in cells[1:]), border]
    return "\n".join(lines + [f"({len(rows)} rows)"])


def as_html(title, query, columns, rows, version) -> str:
    head = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>" for r in rows
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
      body {{ font-family: system-ui, sans-serif; margin: 24px; color: #1f2933; }}
      pre {{ background: #f6f7f9; border: 1px solid #d9dee4; padding: 12px; font-size: 12px; }}
      table {{ border-collapse: collapse; font-size: 13px; }}
      th, td {{ border: 1px solid #d9dee4; padding: 6px 10px; text-align: left; }}
      th {{ background: #e8f4f2; }}
      .meta {{ color: #616e7c; font-size: 12px; }}
    </style></head><body>
      <h2>{html.escape(title)}</h2>
      <p class="meta">SQLite {version} · {len(rows)} rows</p>
      <h3>Query</h3><pre>{html.escape(query)}</pre>
      <h3>Result</h3><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
    </body></html>"""


def main() -> None:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    (SQL_DIR / "results").mkdir(exist_ok=True)
    (SQL_DIR / "screenshots").mkdir(exist_ok=True)
    db = connect()
    version = db.execute("SELECT sqlite_version()").fetchone()[0]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 800})
        for name, title in SCENARIOS.items():
            columns, rows = run(db, name)
            text = as_text(columns, rows)
            (SQL_DIR / "results" / f"{name}.txt").write_text(f"{title}\n\n{text}\n")
            print(f"{title}\n{text}\n")
            query = (SQL_DIR / f"{name}.sql").read_text()
            page.set_content(as_html(title, query, columns, rows, version), wait_until="load")
            page.evaluate("document.fonts.ready")  # capture only once fonts are ready
            target = str(SQL_DIR / "screenshots" / f"{name}.png")
            try:
                page.screenshot(path=target, full_page=True)
            except PlaywrightError:
                # headless Chromium has failed a first capture once ("Unable to capture
                # screenshot"); retry once so a flake does not fail the whole run
                page.wait_for_timeout(500)
                page.screenshot(path=target, full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
