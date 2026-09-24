const state = { rows: [], verification: {}, summary: {} };

const $ = (id) => document.getElementById(id);
const pct = (value) => value == null ? "-" : `${Math.round(value * 100)}%`;

async function loadJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));
}

function renderBars(target, pairs) {
  const el = $(target);
  if (!pairs?.length) {
    el.className = "bar-list empty-state";
    el.textContent = "Run the research agent to populate this chart.";
    return;
  }
  el.className = "bar-list";
  const max = Math.max(...pairs.map(([, v]) => v), 1);
  el.innerHTML = pairs.slice(0, 7).map(([label, value]) => `
    <div class="bar-row">
      <span class="bar-label" title="${esc(label)}">${esc(label)}</span>
      <span class="bar-bg"><span class="bar-fill" style="width:${(value/max)*100}%"></span></span>
      <span class="bar-value">${value}</span>
    </div>`).join("");
}

function derivePatterns(rows) {
  const researched = rows.filter(r => r.status === "researched");
  if (researched.length < 5) return [];

  const counts = (fn) => {
    const map = new Map();
    researched.forEach(r => {
      const keys = fn(r);
      (Array.isArray(keys) ? keys : [keys]).filter(Boolean).forEach(k => map.set(k, (map.get(k)||0)+1));
    });
    return [...map.entries()].sort((a,b)=>b[1]-a[1]);
  };

  const auth = counts(r => r.auth_methods);
  const access = counts(r => r.access_model);
  const blocker = counts(r => r.main_blocker);
  const buildable = researched.filter(r => r.buildability === "yes").length;
  const composio = researched.filter(r => r.composio_toolkit).length;

  const patterns = [];
  if (auth[0]) patterns.push(`${auth[0][0]} is the most common auth pattern in the researched set (${auth[0][1]} apps).`);
  if (access[0]) patterns.push(`${access[0][0].replaceAll("-", " ")} is the most common developer-access model (${access[0][1]} apps).`);
  patterns.push(`${buildable} of ${researched.length} researched apps currently have enough documented surface to call buildable without an outreach dependency.`);
  if (blocker[0]) patterns.push(`The most repeated blocker is "${blocker[0][0]}" (${blocker[0][1]} apps).`);
  if (composio) patterns.push(`${composio} researched apps already match a toolkit in the live Composio catalog.`);
  return patterns.slice(0, 5);
}

function renderOverview() {
  const rows = state.rows;
  const researched = rows.filter(r => r.status === "researched");
  const buildable = researched.filter(r => r.buildability === "yes").length;
  const gated = researched.filter(r => ["admin-gated","partner-gated","contact-sales"].includes(r.access_model)).length;
  const composio = researched.filter(r => r.composio_toolkit).length;

  $("metricResearched").textContent = researched.length;
  $("metricBuildable").textContent = researched.length ? buildable : "-";
  $("metricGated").textContent = researched.length ? gated : "-";
  $("metricComposio").textContent = researched.length ? composio : "-";

  const progress = rows.length ? researched.length / rows.length : 0;
  $("progressText").textContent = `${researched.length} of ${rows.length || 100} apps researched`;
  $("progressPct").textContent = `${Math.round(progress*100)}%`;
  $("progressBar").style.width = `${progress*100}%`;

  renderBars("authBars", state.summary.auth_methods || []);
  renderBars("accessBars", state.summary.access_models || []);

  const patterns = derivePatterns(rows);
  const grid = $("patternCards");
  if (!patterns.length) {
    $("insightBadge").textContent = "Awaiting data";
    grid.innerHTML = `<div class="pattern-card muted"><span>01</span><p>Patterns appear here after the pipeline has researched enough apps to make the counts meaningful.</p></div>`;
  } else {
    $("insightBadge").textContent = `${researched.length} apps analyzed`;
    grid.innerHTML = patterns.map((p,i)=>`<div class="pattern-card"><span>${String(i+1).padStart(2,"0")}</span><p>${esc(p)}</p></div>`).join("");
  }
}

function renderVerification() {
  const v = state.verification || {};
  $("verifySample").textContent = v.sample_size || "-";
  $("verifyBefore").textContent = pct(v.first_pass_accuracy);
  $("verifyAfter").textContent = pct(v.post_verification_accuracy);
  $("verifyCorrections").textContent = v.corrections?.length || "-";

  const list = $("correctionsList");
  if (!v.corrections?.length) {
    list.className = "correction-list empty-state";
    list.textContent = "Verification output will appear here after the browser pass runs.";
    return;
  }
  list.className = "correction-list";
  list.innerHTML = v.corrections.slice(0, 12).map(c => `
    <div class="correction-item">
      <div class="correction-app">${esc(c.app_name)}</div>
      <div class="correction-body">
        <strong>${esc(c.field)}</strong><br>
        ${esc(JSON.stringify(c.before))} -> ${esc(JSON.stringify(c.after))}
        ${c.reason ? `<br>${esc(c.reason)}` : ""}
      </div>
    </div>`).join("");
}

function categoryOptions() {
  const categories = [...new Set(state.rows.map(r => r.category))];
  $("categoryFilter").innerHTML = `<option value="">All categories</option>` +
    categories.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
}

function verdictPill(row) {
  if (row.status !== "researched") return `<span class="pill pending">${esc(row.status || "pending")}</span>`;
  return `<span class="pill ${esc(row.buildability)}">${esc(row.buildability)}</span>`;
}

function renderRows() {
  const q = $("searchInput").value.trim().toLowerCase();
  const category = $("categoryFilter").value;
  const build = $("buildFilter").value;

  const rows = state.rows.filter(r => {
    const hay = JSON.stringify(r).toLowerCase();
    return (!q || hay.includes(q)) &&
      (!category || r.category === category) &&
      (!build || r.buildability === build);
  });

  $("rowCount").textContent = `${rows.length} apps`;
  $("resultsBody").innerHTML = rows.map(r => {
    const auth = r.auth_methods?.length
      ? r.auth_methods.map(a=>`<span class="pill">${esc(a)}</span>`).join("")
      : `<span class="pill pending">pending</span>`;
    const api = r.api_surface || "Pending research";
    const mcp = r.mcp_status ? `<div class="app-cat">MCP: ${esc(r.mcp_status)}</div>` : "";
    const evidence = r.evidence?.length
      ? r.evidence.slice(0,3).map((e,i)=>`<a href="${esc(e.url)}" target="_blank" rel="noreferrer">source ${i+1} ^</a>`).join("")
      : `<span class="app-cat">-</span>`;
    return `<tr>
      <td><div class="app-name">${esc(r.name)}</div><div class="app-cat">${esc(r.category)}</div></td>
      <td>${auth}</td>
      <td>${esc(r.access_model || "-")}</td>
      <td>${esc(api)}${mcp}</td>
      <td>${verdictPill(r)}</td>
      <td>${esc(r.main_blocker || "-")}</td>
      <td><div class="evidence-links">${evidence}</div></td>
    </tr>`;
  }).join("");
}

async function boot() {
  try {
    const [apps, researchedRows, verification, summary] = await Promise.all([
      loadJSON("/data/apps.json"),
      loadJSON("/data/results.json"),
      loadJSON("/data/verification.json"),
      loadJSON("/data/summary.json"),
    ]);
    const byId = new Map(researchedRows.map(r => [r.id, r]));
    state.rows = apps.map(app => byId.get(app.id) || {
      ...app,
      status: "pending",
      auth_methods: [],
      access_model: null,
      api_surface: null,
      mcp_status: null,
      buildability: null,
      main_blocker: null,
      composio_toolkit: null,
      evidence: []
    });
    state.verification = verification;
    state.summary = summary;
    categoryOptions();
    renderOverview();
    renderVerification();
    renderRows();

    ["searchInput","categoryFilter","buildFilter"].forEach(id => {
      $(id).addEventListener(id === "searchInput" ? "input" : "change", renderRows);
    });
  } catch (err) {
    console.error(err);
    $("progressText").textContent = "Could not load research data.";
  }
}

boot();
