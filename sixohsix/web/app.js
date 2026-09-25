const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const pct = (x) => (x == null ? "–" : x.toFixed(2));
const TIMING = { over_time: "Over time", point_in_time: "Point in time" };
const METRICS = [
  ["overall", "Overall"],
  ["obligation_f1", "Obligation F1"],
  ["timing_accuracy", "Timing"],
  ["consideration_correct", "Consideration"],
  ["grounding", "Grounding"],
];

const state = { cases: [], detail: null, runner: "agent" };

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

function mark(ok) {
  return `<span class="mark ${ok ? "match" : "miss"}">${ok ? "match" : "miss"}</span>`;
}

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

function renderList() {
  $("#case-list").innerHTML = state.cases
    .map(
      (c) => `<li><button data-case="${esc(c.id)}" aria-current="${state.detail?.case.id === c.id}">
        <span class="case-title">${esc(c.title)}</span>
        <span class="case-why" title="${esc(c.why_hard)}">${esc(c.why_hard)}</span>
        <span class="chips">
          <span class="score-chip">baseline <b>${pct(c.overall.baseline)}</b></span>
          <span class="score-chip">agent <b>${pct(c.overall.agent)}</b></span>
        </span>
      </button></li>`,
    )
    .join("");
}

function renderContract() {
  const c = state.detail.case;
  $("#contract-head").innerHTML = `<h2>${esc(c.title)}</h2>
    <p>${esc(c.contract_type)} · seller <strong>${esc(c.reporting_entity)}</strong> · customer ${esc(c.customer)}</p>`;
  $("#clauses").innerHTML = c.clauses
    .map(
      (cl) => `<li class="clause" id="clause-${esc(cl.id)}">
        <div class="clause-head"><span class="id-badge">${esc(cl.id)}</span><h3>${esc(cl.heading)}</h3><span class="cited-tag">cited</span></div>
        <p>${esc(cl.text)}</p>
      </li>`,
    )
    .join("");
}

function markCited(analysis) {
  const cited = new Set(analysis ? [...analysis.obligations.flatMap((o) => o.clauses), ...analysis.consideration.clauses] : []);
  document.querySelectorAll(".clause").forEach((el) => el.classList.toggle("cited", cited.has(el.id.slice("clause-".length))));
}

function renderAnalysis() {
  const { detail, runner } = state;
  const result = detail.results[runner];
  markCited(result?.analysis);
  document.querySelectorAll(".runner-toggle button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.runner === runner));
  const runBtn = runner === "agent"
    ? `<button class="btn primary" id="run" ${detail.can_run ? "" : "disabled title='Set ANTHROPIC_API_KEY to run the agent'"}>${result ? "Re-run agent" : "Run agent"}</button>`
    : "";

  if (!result) {
    $("#analysis").innerHTML = `<p class="empty">No ${runner} result for this contract yet.</p><div class="actions">${runBtn}</div><p class="error" id="run-error"></p>`;
    return;
  }

  const a = result.analysis;
  const ref = detail.reference;
  const s = result.scores;
  const { rows, missed } = matchObligations(a.obligations, ref.obligations);
  const c = a.consideration;

  $("#analysis").innerHTML = `
    <div class="scores">${METRICS.map(([k, label]) => `<div class="metric ${k === "overall" ? "overall" : ""}"><b>${pct(s[k])}</b><span>${label}</span></div>`).join("")}</div>
    <p>${esc(a.summary)}</p>

    <div class="section"><h3>Performance obligations</h3>
      ${rows
        .map(
          ({ o, kindOk, timingOk }) => `<div class="card">
          <div class="card-head"><strong>${esc(detail.kinds[o.kind])}</strong>${mark(kindOk)}</div>
          <div class="row"><span class="pill">${TIMING[o.timing]}</span>${kindOk ? mark(timingOk) : ""}</div>
          <p class="small">${esc(o.description)}</p>
          <p class="small muted">${esc(o.rationale)}</p>
          <div class="row">${chips(o.clauses)}</div>
          ${o.guidance.length ? `<div class="refs">ASC ${o.guidance.map(esc).join(" · ")}</div>` : ""}
        </div>`,
        )
        .join("") || `<p class="muted">None identified.</p>`}
      ${missed.length ? `<p class="small muted">Reference also expects:</p><ul class="expected">${missed.map((r) => `<li>${esc(detail.kinds[r.kind])} (${TIMING[r.timing].toLowerCase()})</li>`).join("")}</ul>` : ""}
    </div>

    <div class="section"><h3>Consideration</h3>
      <div class="card">
        <div class="row">Variable consideration: <strong>${c.variable ? "yes" : "no"}</strong>${mark(c.variable === ref.variable)}</div>
        <div class="row">Royalty exception (606-10-55-65): <strong>${c.royalty_exception ? "applies" : "does not apply"}</strong>${mark(c.royalty_exception === ref.royalty_exception)}</div>
        <p class="small">${esc(c.summary)}</p>
        <p class="small muted">${esc(c.rationale)}</p>
        <div class="row">${chips(c.clauses)}</div>
      </div>
    </div>

    <div class="section"><h3>Open questions</h3>
      ${a.open_questions.length ? `<ol class="questions">${a.open_questions.map((q) => `<li class="small">${esc(q)}</li>`).join("")}</ol>` : `<p class="small muted">None raised.</p>`}
    </div>

    ${result.trace.length ? `<div class="section"><details class="trace"><summary>Agent trace · ${result.trace.length} steps · ${result.input_tokens.toLocaleString()} in / ${result.output_tokens.toLocaleString()} out · ${result.seconds}s</summary>
      <ol>${result.trace.map((st) => `<li><code>${esc(st.tool)}(${esc(st.tool === "submit_analysis" ? "…" : Object.values(st.input).join(", "))})</code><pre>${esc(st.output)}</pre></li>`).join("")}</ol>
    </details></div>` : ""}

    <div class="actions">
      <a class="btn" href="/api/cases/${encodeURIComponent(detail.case.id)}/memo.docx?runner=${runner}">Download memo</a>
      ${runBtn}
    </div>
    <p class="error" id="run-error"></p>`;
}

function focusClause(id) {
  document.querySelectorAll(".clause.hl").forEach((el) => el.classList.remove("hl"));
  const el = document.getElementById(`clause-${id}`);
  if (!el) return;
  el.classList.add("hl");
  el.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function selectCase(id) {
  state.detail = await api(`/api/cases/${encodeURIComponent(id)}`);
  renderList();
  renderContract();
  renderAnalysis();
}

async function runAgent(btn) {
  btn.disabled = true;
  btn.textContent = "Running…";
  try {
    await api(`/api/cases/${encodeURIComponent(state.detail.case.id)}/run`, { method: "POST" });
    state.cases = await api("/api/cases");
    await selectCase(state.detail.case.id);
  } catch (e) {
    $("#run-error").textContent = e.message;
    btn.disabled = false;
    btn.textContent = "Run agent";
  }
}

async function renderScoreboard() {
  const board = await api("/api/scoreboard");
  const runners = ["baseline", "agent"];
  const r = board.runners;
  const best = (vals) => Math.max(...vals.filter((v) => v != null));
  const cell = (v, top) => `<td class="num ${v != null && v === top && runners.length > 1 ? "win" : ""}">${pct(v)}</td>`;
  $("#scoreboard").innerHTML = `
    <h2>Scoreboard</h2>
    <p>Mean scores over every case each runner has been evaluated on. Overall is the mean of obligation F1, timing and consideration, multiplied by grounding.</p>
    <table class="board">
      <thead><tr><th>Metric</th>${runners.map((n) => `<th>${n}</th>`).join("")}</tr></thead>
      <tbody>
        ${METRICS.map(([k, label]) => {
          const vals = runners.map((n) => r[n]?.[k]);
          return `<tr><td>${label}</td>${vals.map((v) => cell(v, best(vals))).join("")}</tr>`;
        }).join("")}
        <tr><td>Cases run</td>${runners.map((n) => `<td class="num">${r[n]?.cases ?? "–"}</td>`).join("")}</tr>
        <tr><td>Tokens (in / out)</td>${runners.map((n) => `<td class="num">${r[n] ? `${r[n].input_tokens.toLocaleString()} / ${r[n].output_tokens.toLocaleString()}` : "–"}</td>`).join("")}</tr>
        <tr><td>Seconds</td>${runners.map((n) => `<td class="num">${r[n]?.seconds ?? "–"}</td>`).join("")}</tr>
      </tbody>
    </table>
    <h2>By case</h2>
    <p>Overall score per contract.</p>
    <table class="board">
      <thead><tr><th>Case</th>${runners.map((n) => `<th>${n}</th>`).join("")}</tr></thead>
      <tbody>${Object.entries(board.cases)
        .map(([id, sc]) => {
          const vals = runners.map((n) => sc[n]);
          return `<tr><td>${esc(id)}</td>${vals.map((v) => cell(v, best(vals))).join("")}</tr>`;
        })
        .join("")}</tbody>
    </table>`;
}

function showTab(tab) {
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === tab));
  $("#cases").hidden = tab !== "cases";
  $("#scoreboard").hidden = tab !== "scoreboard";
  if (tab === "scoreboard") renderScoreboard();
}

document.addEventListener("click", (e) => {
  const t = e.target.closest("button");
  if (!t) return;
  if (t.dataset.tab) showTab(t.dataset.tab);
  else if (t.dataset.case) selectCase(t.dataset.case);
  else if (t.dataset.runner) { state.runner = t.dataset.runner; renderAnalysis(); }
  else if (t.dataset.clause) focusClause(t.dataset.clause);
  else if (t.id === "run") runAgent(t);
});
document.addEventListener("mouseover", (e) => {
  const chip = e.target.closest(".chip[data-clause]");
  if (chip) focusClause(chip.dataset.clause);
});

(async () => {
  state.cases = await api("/api/cases");
  renderList();
  if (state.cases.length) await selectCase(state.cases[0].id);
})();
