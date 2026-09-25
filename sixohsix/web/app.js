const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const pct = (x) => (x == null ? "–" : `${Math.round(x * 100)}%`);
const TIMING = { over_time: "Spread over time", point_in_time: "All at once" };
const RUNNER = { agent: "AI agent", baseline: "Keyword rules" };
const METRICS = [
  ["overall", "Overall", "Average of the three accuracy scores, scaled down by any citations that don't exist."],
  ["obligation_f1", "Found the right promises", "How well the promises found match the answer key (F1 over promise types)."],
  ["timing_accuracy", "Right timing", "Share of matched promises booked at the right time: spread over time or all at once."],
  ["consideration_correct", "Right pricing calls", "Whether variable pricing and the royalty exception were called correctly."],
  ["grounding", "Real citations", "Share of cited clause ids that actually exist in the contract."],
];

const state = { cases: [], detail: null, runner: "agent", citedOnly: true };

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

const WHY = { Extra: "The answer key has no separate promise of this type.", Missed: "The answer key expects this promise." };
const verdict = (ok, why) => `<span class="mark ${ok ? "match" : "miss"}" title="${ok ? "Matches the answer key." : WHY[why] ?? ""}">${ok ? "✓ Correct" : `✗ ${why}`}</span>`;

function chips(ids) {
  const known = new Set(state.detail.case.clauses.map((c) => c.id));
  return ids
    .map((id) =>
      known.has(id)
        ? `<button class="chip" data-clause="${esc(id)}">${esc(id)}</button>`
        : `<span class="chip halluc" title="Not in this contract">${esc(id)}</span>`,
    )
    .join("");
}

// Pair predicted obligations with reference ones by kind, consuming each reference once.
function matchObligations(pred, ref) {
  const pool = ref.map((r) => ({ ...r, used: false }));
  const rows = pred.map((o) => {
    const same = pool.filter((r) => !r.used && r.kind === o.kind);
    const hit = same.find((r) => r.timing === o.timing) || same[0];
    if (hit) hit.used = true;
    return { o, kindOk: !!hit, timingOk: !!hit && hit.timing === o.timing };
  });
  return { rows, missed: pool.filter((r) => !r.used) };
}

function cited(analysis) {
  return new Set(analysis ? [...analysis.obligations.flatMap((o) => o.clauses), ...analysis.consideration.clauses] : []);
}

function renderList() {
  $("#case-list").innerHTML = state.cases
    .map(
      (c) => `<li><button data-case="${esc(c.id)}" aria-current="${state.detail?.case.id === c.id}">
        <span class="case-title">${esc(c.title)}</span>
        <span class="case-why" title="${esc(c.why_hard)}">${esc(c.why_hard)}</span>
        <span class="chips">
          <span class="score-chip">AI <b>${pct(c.overall.agent)}</b></span>
          <span class="score-chip">Rules <b>${pct(c.overall.baseline)}</b></span>
        </span>
      </button></li>`,
    )
    .join("");
}

function renderContract() {
  const c = state.detail.case;
  $("#contract-head").innerHTML = `<h2>${esc(c.title)}</h2>
    <p><strong>${esc(c.reporting_entity)}</strong> sells to ${esc(c.customer)} · ${esc(c.contract_type)}</p>
    <p class="why"><b>The tricky part:</b> ${esc(c.why_hard)}</p>`;
  $("#clauses").innerHTML = c.clauses
    .map(
      (cl) => `<li class="clause" id="clause-${esc(cl.id)}">
        <div class="clause-head"><span class="id-badge">${esc(cl.id)}</span><h3>${esc(cl.heading)}</h3><span class="cited-tag">cited</span></div>
        <p>${esc(cl.text)}</p>
      </li>`,
    )
    .join("");
}

function applyFilter() {
  const ids = cited(state.detail.results[state.runner]?.analysis);
  const only = state.citedOnly && ids.size > 0;
  document.querySelectorAll(".clause").forEach((el) => {
    const hit = ids.has(el.id.slice("clause-".length));
    el.classList.toggle("cited", hit);
    el.hidden = only && !hit;
  });
  const total = state.detail.case.clauses.length;
  $("#filter").innerHTML = ids.size
    ? `<span>${only ? `Showing the ${ids.size} clauses the ${RUNNER[state.runner]} cited, out of ${total}.` : `Showing all ${total} clauses. Cited ones have a blue edge.`}</span>
       <button class="link" id="toggle-filter">${only ? "Show full contract" : "Show cited only"}</button>`
    : `<span>Showing all ${total} clauses.</span>`;
}

function row(title, timing, mark, body) {
  const sub = timing ? `<small>Revenue counts: ${timing.toLowerCase()}</small>` : "";
  return `<details class="item"><summary><span class="item-title">${title}${sub}</span>${mark}</summary><div class="item-body">${body}</div></details>`;
}

function renderAnalysis() {
  const { detail, runner } = state;
  const result = detail.results[runner];
  applyFilter();
  document.querySelectorAll(".runner-toggle button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.runner === runner));
  const runBtn = runner === "agent"
    ? `<button class="btn primary" id="run" ${detail.can_run ? "" : "disabled title='Set ANTHROPIC_API_KEY to run the agent'"}>${result ? "Re-run AI agent" : "Run AI agent"}</button>`
    : "";

  if (!result) {
    $("#analysis").innerHTML = `<p class="empty">No ${RUNNER[runner]} result for this contract yet.</p><div class="actions">${runBtn}</div><p class="error" id="run-error"></p>`;
    return;
  }

  const a = result.analysis;
  const ref = detail.reference;
  const s = result.scores;
  const { rows, missed } = matchObligations(a.obligations, ref.obligations);
  const c = a.consideration;
  const varOk = c.variable === ref.variable;
  const royOk = c.royalty_exception === ref.royalty_exception;
  const right = rows.filter((r) => r.kindOk && r.timingOk).length + varOk + royOk;
  const total = rows.length + missed.length + 2;

  $("#analysis").innerHTML = `
    <div class="headline">
      <div class="big">${pct(s.overall)}</div>
      <div><strong>${right} of ${total} calls match the answer key</strong>
      <p class="small muted">Click any row below to see the reasoning and the clauses behind it.</p></div>
    </div>

    <div class="section"><h3>What the seller promised, and when the revenue counts</h3>
      <div class="list">
      ${rows
        .map(({ o, kindOk, timingOk }) =>
          row(
            esc(detail.kinds[o.kind]),
            TIMING[o.timing],
            verdict(kindOk && timingOk, kindOk ? "Wrong timing" : "Extra"),
            `<p>${esc(o.description)}</p><p class="muted">${esc(o.rationale)}</p>
             <div class="row">${chips(o.clauses)}</div>
             ${o.guidance.length ? `<div class="refs">ASC ${o.guidance.map(esc).join(" · ")}</div>` : ""}`,
          ),
        )
        .join("")}
      ${missed
        .map((r) =>
          row(`<span class="muted">${esc(detail.kinds[r.kind])}</span>`, TIMING[r.timing], verdict(false, "Missed"),
            `<p class="muted">The answer key expects this promise, but the ${RUNNER[runner]} did not find it.</p><p class="muted">${esc(r.rationale)}</p><div class="row">${chips(r.clauses)}</div>`),
        )
        .join("")}
      </div>
    </div>

    <div class="section"><h3>Pricing</h3>
      <div class="list">
      ${row(`Price can change (usage, royalties, bonuses): <strong>${c.variable ? "yes" : "no"}</strong>`, "", verdict(varOk, "Wrong"),
        `<p>${esc(c.summary)}</p><p class="muted">${esc(c.rationale)}</p><div class="row">${chips(c.clauses)}</div>`)}
      ${row(`Royalty exception applies: <strong>${c.royalty_exception ? "yes" : "no"}</strong>`, "", verdict(royOk, "Wrong"),
        `<p class="muted">Sales-based royalties on a license are booked only when the sales happen (ASC 606-10-55-65).</p><div class="row">${chips(c.clauses)}</div>`)}
      </div>
    </div>

    ${a.open_questions.length ? `<div class="section"><h3>Questions for a human</h3><ol class="questions">${a.open_questions.map((q) => `<li class="small">${esc(q)}</li>`).join("")}</ol></div>` : ""}

    <div class="actions">
      <a class="btn" href="/api/cases/${encodeURIComponent(detail.case.id)}/memo.docx?runner=${runner}">Download Word memo</a>
      ${runBtn}
    </div>
    <p class="error" id="run-error"></p>

    <details class="more"><summary>Score breakdown</summary>
      <div class="scores">${METRICS.map(([k, label, tip]) => `<div class="metric" title="${esc(tip)}"><b>${pct(s[k])}</b><span>${label}</span></div>`).join("")}</div>
    </details>
    <details class="more"><summary>Summary</summary><p>${esc(a.summary)}</p></details>
    ${result.trace.length ? `<details class="more trace"><summary>Step-by-step trace · ${result.trace.length} steps · ${result.seconds}s</summary>
      <p class="small muted">${result.input_tokens.toLocaleString()} tokens in / ${result.output_tokens.toLocaleString()} out</p>
      <ol>${result.trace.map((st) => `<li><code>${esc(st.tool)}(${esc(st.tool === "submit_analysis" ? "…" : Object.values(st.input).join(", "))})</code><pre>${esc(st.output)}</pre></li>`).join("")}</ol>
    </details>` : ""}`;
}

function focusClause(id) {
  document.querySelectorAll(".clause.hl").forEach((el) => el.classList.remove("hl"));
  const el = document.getElementById(`clause-${id}`);
  if (!el) return;
  if (el.hidden) { state.citedOnly = false; applyFilter(); }
  el.classList.add("hl");
  el.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function selectCase(id) {
  state.detail = await api(`/api/cases/${encodeURIComponent(id)}`);
  state.citedOnly = true;
  renderList();
  renderContract();
  renderAnalysis();
}

async function runAgent(btn) {
  const id = state.detail.case.id;
  const url = `/api/cases/${encodeURIComponent(id)}/run`;
  btn.disabled = true;
  btn.textContent = "Starting…";
  try {
    await api(url, { method: "POST" });
  } catch (e) {
    $("#run-error").textContent = e.message;
    btn.disabled = false;
    btn.textContent = "Run AI agent";
    return;
  }
  const timer = setInterval(async () => {
    const run = await api(url).catch(() => null);
    if (!run) return;
    if (run.status !== "running") clearInterval(timer);
    const here = state.detail.case.id === id;
    if (run.status === "done") {
      state.cases = await api("/api/cases");
      if (here) await selectCase(id);
      else renderList();
      return;
    }
    // The panel may have re-rendered (runner toggle), so look the button up each tick.
    const b = $("#run");
    if (!here || !b) return;
    if (run.status === "error") {
      b.disabled = false;
      b.textContent = "Run AI agent";
      $("#run-error").textContent = run.error;
    } else {
      b.disabled = true;
      b.textContent = `Running · step ${run.step_count}${run.steps.length ? ` · ${run.steps.at(-1)}` : ""}`;
    }
  }, 1000);
}

async function renderScoreboard() {
  const board = await api("/api/scoreboard");
  const runners = ["agent", "baseline"];
  const r = board.runners;
  const title = Object.fromEntries(state.cases.map((c) => [c.id, c.title]));
  const best = (vals) => Math.max(...vals.filter((v) => v != null));
  const cell = (v, top) => `<td class="num ${v != null && v === top ? "win" : ""}">${pct(v)}</td>`;
  const head = `<tr><th></th>${runners.map((n) => `<th>${RUNNER[n]}</th>`).join("")}</tr>`;
  $("#scoreboard").innerHTML = `
    <div class="headline board-headline">
      <div class="big">${pct(r.agent?.overall)}</div>
      <div><strong>The AI agent agrees with the answer key ${pct(r.agent?.overall)} of the time. Keyword rules manage ${pct(r.baseline?.overall)}.</strong>
      <p class="small muted">Averaged over ${r.agent?.cases ?? 0} real contracts. Hover a row name for what it measures.</p></div>
    </div>
    <table class="board">
      <thead>${head}</thead>
      <tbody>
        ${METRICS.map(([k, label, tip]) => {
          const vals = runners.map((n) => r[n]?.[k]);
          return `<tr><td title="${esc(tip)}">${label}</td>${vals.map((v) => cell(v, best(vals))).join("")}</tr>`;
        }).join("")}
        <tr><td>Tokens (in / out)</td>${runners.map((n) => `<td class="num">${r[n]?.input_tokens ? `${r[n].input_tokens.toLocaleString()} / ${r[n].output_tokens.toLocaleString()}` : "–"}</td>`).join("")}</tr>
        <tr><td>Seconds</td>${runners.map((n) => `<td class="num">${r[n]?.seconds ?? "–"}</td>`).join("")}</tr>
      </tbody>
    </table>
    <h2>By contract</h2>
    <table class="board">
      <thead>${head}</thead>
      <tbody>${Object.entries(board.cases)
        .map(([id, sc]) => {
          const vals = runners.map((n) => sc[n]);
          return `<tr><td><button class="link" data-open="${esc(id)}">${esc(title[id] ?? id)}</button></td>${vals.map((v) => cell(v, best(vals))).join("")}</tr>`;
        })
        .join("")}</tbody>
    </table>`;
}

function showTab(tab) {
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === tab));
  $("#cases").hidden = tab !== "cases";
  $("#scoreboard").hidden = tab !== "scoreboard";
  $("#howto").hidden = tab !== "cases";
  if (tab === "scoreboard") renderScoreboard();
}

document.addEventListener("click", (e) => {
  const t = e.target.closest("button");
  if (!t) return;
  if (t.dataset.tab) showTab(t.dataset.tab);
  else if (t.dataset.case) selectCase(t.dataset.case);
  else if (t.dataset.open) { showTab("cases"); selectCase(t.dataset.open); }
  else if (t.dataset.runner) { state.runner = t.dataset.runner; renderAnalysis(); }
  else if (t.dataset.clause) focusClause(t.dataset.clause);
  else if (t.id === "run") runAgent(t);
  else if (t.id === "toggle-filter") { state.citedOnly = !state.citedOnly; applyFilter(); }
});
document.addEventListener("mouseover", (e) => {
  const chip = e.target.closest(".chip[data-clause]");
  // Hover only highlights; revealing a filtered-out clause waits for a click.
  if (chip && !document.getElementById(`clause-${chip.dataset.clause}`)?.hidden) focusClause(chip.dataset.clause);
});

(async () => {
  state.cases = await api("/api/cases");
  renderList();
  if (state.cases.length) await selectCase(state.cases[0].id);
})();
