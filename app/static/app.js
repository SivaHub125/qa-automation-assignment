/* EMI Insights front end: calls the Flask JSON API and renders results. */
const EmiApp = (() => {
  const inr = new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 0,
  });
  const money = (value) => inr.format(Math.round(value));
  const COLORS = { principal: "#2a9d8f", interest: "#e76f51" };
  const DEFAULTS = { amount: "1000000", rate: "10.5", years: "5" };
  const REQUEST_FAILED = "Something went wrong, please try again";
  const YEAR_FILTER_ERRORS = ["from_year", "to_year", "year_order"];

  // A non-JSON reply (server error page, network failure) is turned into a normal
  // error result, so the page never stays stuck in its "loading" state.
  async function getJson(url) {
    try {
      const response = await fetch(url);
      return { ok: response.ok, body: await response.json() };
    } catch {
      return { ok: false, body: { errors: { request: REQUEST_FAILED } } };
    }
  }

  // Only the newest request may update the page: a slow, older response is ignored.
  function latestOnly(handler) {
    let latest = 0;
    return async (...args) => {
      const id = ++latest;
      return handler(() => id === latest, ...args);
    };
  }

  function loanQuery(values) {
    return new URLSearchParams(values).toString();
  }

  /* ---------------- Dashboard ---------------- */
  function initDashboard() {
    const form = document.getElementById("loan-form");
    const fields = ["amount", "rate", "years"];
    const cards = document.querySelector("[data-testid=summary-cards]");
    const canvas = document.querySelector("[data-testid=breakup-chart] canvas");
    const reportLink = document.getElementById("report-link");
    const requestError = document.querySelector("[data-testid=request-error]");
    // data-testid of each summary card -> field of the /api/emi response
    const CARDS = { "emi-value": "emi", "total-interest-value": "total_interest", "total-payment-value": "total_payment" };

    const chart = new Chart(canvas, {
      type: "pie",
      data: {
        labels: ["Principal amount", "Total interest"],
        datasets: [{ data: [0, 0], backgroundColor: [COLORS.principal, COLORS.interest] }],
      },
      options: { animation: false, plugins: { legend: { position: "bottom" } } },
    });

    // Keep each slider and its text box in sync.
    document.querySelectorAll("input[type=range][data-syncs]").forEach((slider) => {
      const box = document.getElementById(slider.dataset.syncs);
      slider.addEventListener("input", () => { box.value = slider.value; });
      slider.addEventListener("change", (event) => calculate(event));
      box.addEventListener("input", () => {
        const n = Number(box.value.replace(/,/g, ""));
        if (!Number.isNaN(n)) slider.value = n;
      });
    });

    function showErrors(errors) {
      fields.forEach((f) => {
        document.getElementById(`${f}-error`).textContent = errors[f] || "";
        document.getElementById(f).setAttribute("aria-invalid", errors[f] ? "true" : "false");
      });
    }

    const calculate = latestOnly(async (isLatest, event) => {
      if (event) event.preventDefault();
      cards.dataset.state = "loading";
      const values = Object.fromEntries(fields.map((f) => [f, document.getElementById(f).value]));
      const { ok, body } = await getJson(`/api/emi?${loanQuery(values)}`);
      if (!isLatest()) return;

      const errors = ok ? {} : body.errors || {};
      showErrors(errors);
      requestError.textContent = errors.request || "";
      Object.entries(CARDS).forEach(([testid, key]) => {
        document.querySelector(`[data-testid=${testid}]`).textContent = ok ? money(body[key]) : "—";
      });
      // whole rupees from the server: principal + interest = total payment exactly
      chart.data.datasets[0].data = ok ? [body.total_payment - body.total_interest, body.total_interest] : [0, 0];
      chart.update();
      // The report link always matches what is on screen: no report for invalid input
      if (ok) reportLink.href = `/report?${loanQuery(values)}`;
      else reportLink.removeAttribute("href");
      cards.dataset.state = ok ? "ready" : "error";
    });

    form.addEventListener("submit", calculate);
    calculate();
  }

  /* ---------------- Report ---------------- */
  function initReport() {
    const params = new URLSearchParams(window.location.search);
    const loan = Object.fromEntries(
      Object.entries(DEFAULTS).map(([k, v]) => [k, params.get(k) ?? v])
    );
    const form = document.getElementById("filter-form");
    const fromSelect = document.getElementById("from-year");
    const toSelect = document.getElementById("to-year");
    const tbody = document.querySelector("[data-testid=schedule-table] tbody");
    const filterError = document.querySelector("[data-testid=filter-error]");
    const loanLine = document.querySelector("[data-testid=loan-details]");
    const table = document.querySelector("[data-testid=schedule-table]");

    const chart = new Chart(document.querySelector("[data-testid=yearly-chart] canvas"), {
      type: "bar",
      data: {
        labels: [],
        datasets: [
          { label: "Principal", data: [], backgroundColor: COLORS.principal },
          { label: "Interest", data: [], backgroundColor: COLORS.interest },
        ],
      },
      options: {
        animation: false,
        responsive: true,
        scales: { x: { stacked: true }, y: { stacked: true } },
      },
    });

    function fillYearOptions(years) {
      if (fromSelect.options.length) return;
      for (let y = 1; y <= years; y += 1) {
        fromSelect.add(new Option(`Year ${y}`, y));
        toSelect.add(new Option(`Year ${y}`, y));
      }
      toSelect.value = String(years);
    }

    function cell(tag, text) {
      const element = document.createElement(tag);
      element.textContent = text;
      return element;
    }

    function tableRow(row, view) {
      const period = cell("th", view === "monthly" ? `Month ${row.month} (Year ${row.year})` : `Year ${row.year}`);
      period.scope = "row";
      const tr = document.createElement("tr");
      tr.append(period, ...[row.principal, row.interest, row.payment, row.balance].map((v) => cell("td", money(v))));
      return tr;
    }

    function render(body) {
      const s = body.summary;
      loanLine.textContent =
        `Loan ${money(s.amount)} at ${s.rate}% for ${s.years} years · EMI ${money(s.emi)}`;

      tbody.replaceChildren(...body.rows.map((row) => tableRow(row, body.view)));
      document.querySelector("[data-testid=total-principal]").textContent = money(body.totals.principal);
      document.querySelector("[data-testid=total-interest]").textContent = money(body.totals.interest);
      document.querySelector("[data-testid=total-paid]").textContent = money(body.totals.payment);

      const yearly = body.yearly ?? body.rows;  // sent separately only for the monthly view
      chart.data.labels = yearly.map((year) => `Year ${year.year}`);
      chart.data.datasets[0].data = yearly.map((year) => year.principal);
      chart.data.datasets[1].data = yearly.map((year) => year.interest);
      chart.update();
    }

    const load = latestOnly(async (isLatest, event) => {
      if (event) event.preventDefault();
      table.dataset.state = "loading";
      const query = {
        ...loan,
        view: form.querySelector("input[name=view]:checked").value,
        // empty before the first load: the server then uses the whole tenure
        from_year: fromSelect.value,
        to_year: toSelect.value,
      };
      const { ok, body } = await getJson(`/api/schedule?${loanQuery(query)}`);
      if (!isLatest()) return;
      if (!ok) {
        const errors = body.errors || {};
        const filterMessages = YEAR_FILTER_ERRORS.filter((key) => errors[key]).map((key) => errors[key]);
        filterError.textContent = filterMessages.join("\n");
        if (!filterMessages.length) loanLine.textContent = Object.values(errors).join("\n");
        table.dataset.state = "error";
        return;
      }
      filterError.textContent = "";
      fillYearOptions(body.summary.years);
      render(body);
      table.dataset.state = "ready";
    });

    form.addEventListener("submit", load);
    load();
  }

  return { initDashboard, initReport };
})();
