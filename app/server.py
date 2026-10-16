"""Flask server for the EMI Insights web app (the application under test).

Run manually:  python -m app.server   (then open http://127.0.0.1:5000)
"""

import os

from flask import Flask, jsonify, render_template, request, send_from_directory

from app import emi

app = Flask(__name__)


@app.get("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@app.get("/report")
def report():
    return render_template("report.html", active="report")


@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


@app.get("/health")
def health():
    return {"status": "ok"}


def _loan_from_request() -> emi.LoanInput:
    args = request.args
    return emi.parse_loan_input(args.get("amount"), args.get("rate"), args.get("years"))


def _year_filters(loan: emi.LoanInput) -> tuple[int, int]:
    """From/To year (default: the whole tenure). Every problem is reported, each under its own key."""
    years, errors = {"from_year": 1, "to_year": loan.years}, {}
    for name in years:
        raw = request.args.get(name, "")
        if raw.strip():
            value, error = emi.year_filter_rule(name, loan.years).parse(raw)
            if error:
                errors[name] = error
            else:
                years[name] = int(value)
    if not errors and years["from_year"] > years["to_year"]:
        errors["year_order"] = emi.YEAR_ORDER_MESSAGE
    if errors:
        raise emi.ValidationError(errors)
    return years["from_year"], years["to_year"]


@app.errorhandler(emi.ValidationError)
def validation_error(error: emi.ValidationError):
    return jsonify({"errors": error.errors}), 400


@app.get("/api/emi")
def api_emi():
    return jsonify(emi.summary(_loan_from_request()))


@app.get("/api/schedule")
def api_schedule():
    loan = _loan_from_request()
    view = request.args.get("view", "yearly")
    if view not in ("yearly", "monthly"):
        raise emi.ValidationError({"view": emi.VIEW_MESSAGE})
    from_year, to_year = _year_filters(loan)

    def in_range(row: dict) -> bool:
        return from_year <= row["year"] <= to_year

    monthly = emi.monthly_schedule(loan)
    yearly = [year for year in emi.yearly_schedule(monthly) if in_range(year)]
    rows = [month for month in monthly if in_range(month)] if view == "monthly" else yearly
    body = {
        "summary": emi.summary(loan),
        "view": view,
        "from_year": from_year,
        "to_year": to_year,
        "rows": rows,
        "totals": {key: sum(r[key] for r in rows) for key in ("principal", "interest", "payment")},
    }
    if view == "monthly":
        body["yearly"] = yearly  # the chart is always yearly; in yearly view it is the same as rows
    return jsonify(body)


if __name__ == "__main__":
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("APP_PORT", "5000")))
