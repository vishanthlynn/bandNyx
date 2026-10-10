const pipeline = window.NyxPipeline;
const lock = document.querySelector("#lock");
const workspace = document.querySelector("#workspace");
const lockStatus = document.querySelector("#lock-status");
const today = new Date().toISOString().slice(0, 10);

function load(key) {
  return JSON.parse(localStorage.getItem(key) || "[]");
}

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function leads() {
  return load("nyx-leads").map((lead) => pipeline.normalizeLead(lead, today));
}

function render() {
  const rows = leads();
  const events = load("nyx-events");
  const summary = pipeline.revenueSummary(rows, events);
  document.querySelector("#metrics").innerHTML = [
    ["Opportunities", summary.opportunities],
    ["Ready to contact", summary.readyToContact],
    ["Form completions", summary.qualifiedEnquiries],
    ["Clicks", summary.clickCount],
    ["Quotations", summary.quotations],
    ["Confirmed bookings", summary.confirmedBookings],
    ["Pipeline value", summary.pipelineValue],
    ["Collected revenue", summary.collectedRevenue],
  ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
  document.querySelector("#metrics").insertAdjacentHTML("beforeend", `<p>${summary.clickNote} Pipeline value is an estimate. Collected revenue counts won leads only.</p>`);

  const actions = pipeline.dailyActions(rows, today);
  document.querySelector("#actions").innerHTML = actions.length
    ? `<ol>${actions.map((lead) => `<li>${lead.organization} · score ${lead.score} · ${lead.nextAction || lead.status}</li>`).join("")}</ol>`
    : "<p>No follow-ups are due. Add a verified organizer before contacting anyone.</p>";

  const query = document.querySelector("#search").value.toLowerCase();
  const status = document.querySelector("#status-filter").value;
  const visible = rows
    .filter((lead) => !query || `${lead.organization} ${lead.city} ${lead.notes}`.toLowerCase().includes(query))
    .filter((lead) => !status || lead.status === status)
    .sort((left, right) => right.score - left.score);

  document.querySelector("#leads").innerHTML = `<table class="pipeline-table"><thead><tr><th>Organizer</th><th>Score</th><th>Status</th><th>Revenue</th><th>Draft</th></tr></thead><tbody>${
    visible.map((lead) => `<tr>
      <td><strong>${lead.organization}</strong><br />${lead.city} · ${lead.eventDate || "date unknown"}<br /><a href="${lead.sourceUrl}">Source</a><br />${lead.confidence}</td>
      <td>${lead.score}<br />${lead.reasons.join("; ")}</td>
      <td>
        <select data-id="${lead.id}" data-field="status">${pipeline.STATUSES.map((item) => `<option ${item === lead.status ? "selected" : ""}>${item}</option>`).join("")}</select>
        <input data-id="${lead.id}" data-field="quotedFee" value="${lead.quotedFee || ""}" placeholder="Quoted fee" />
        <input data-id="${lead.id}" data-field="collectedRevenue" value="${lead.collectedRevenue || ""}" placeholder="Collected" />
        <input data-id="${lead.id}" data-field="lossReason" value="${lead.lossReason}" placeholder="Loss reason" />
        <label><input data-id="${lead.id}" data-field="doNotContact" type="checkbox" ${lead.doNotContact ? "checked" : ""} /> Do not contact</label>
      </td>
      <td>${lead.collectedRevenue || 0}</td>
      <td><button type="button" data-draft="${lead.id}">Copy draft</button></td>
    </tr>`).join("") || "<tr><td colspan='5'>No leads yet. Nothing has been discovered automatically.</td></tr>"
  }</tbody></table>`;

  document.querySelector("#experiments").innerHTML = `<ul>${load("nyx-experiments").map((item) => `<li><strong>${item.hypothesis}</strong> — ${item.change}. Window: ${item.window}. Result: ${item.result || "not enough data"}</li>`).join("")}</ul>`;
}

document.querySelector("#unlock-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = new FormData(event.target).get("token");
  const local = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (local) {
    lock.hidden = true;
    workspace.hidden = false;
    render();
    return;
  }
  const response = await fetch("/api/admin-gate", { headers: { authorization: `Bearer ${token}` } });
  const result = await response.json();
  if (!result.ok) {
    lockStatus.textContent = result.reason === "not_configured"
      ? "Set ADMIN_ACCESS_TOKEN on the host before using this dashboard."
      : "The token was not accepted.";
    return;
  }
  lock.hidden = true;
  workspace.hidden = false;
  render();
});

document.querySelector("#status-filter").innerHTML += pipeline.STATUSES.map((status) => `<option>${status}</option>`).join("");
document.querySelector("#lead-form").sourceDate.value = today;

document.querySelector("#lead-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  if (!data.sourceUrl || !data.evidence) return;
  const next = pipeline.dedupeLeads([pipeline.normalizeLead(data, today), ...leads()]);
  save("nyx-leads", next);
  event.target.reset();
  event.target.sourceDate.value = today;
  render();
});

document.querySelector("#csv-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const imported = pipeline.parseCsv(await file.text()).map((row) => pipeline.normalizeLead(row, today));
  save("nyx-leads", pipeline.dedupeLeads([...imported, ...leads()]));
  render();
});

document.querySelector("#export-csv").addEventListener("click", () => {
  const blob = new Blob([pipeline.toCsv(leads())], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "nyx-leads.csv";
  link.click();
});

document.querySelector("#search").addEventListener("input", render);
document.querySelector("#status-filter").addEventListener("change", render);
document.querySelector("#leads").addEventListener("change", (event) => {
  const field = event.target.dataset.field;
  if (!field) return;
  const next = leads().map((lead) => {
    if (lead.id !== event.target.dataset.id) return lead;
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    return pipeline.normalizeLead({ ...lead, [field]: value }, today);
  });
  save("nyx-leads", next);
  render();
});

document.querySelector("#leads").addEventListener("click", async (event) => {
  const id = event.target.dataset.draft;
  if (!id) return;
  const lead = leads().find((item) => item.id === id);
  await navigator.clipboard.writeText(pipeline.outreachDraft(lead));
  event.target.textContent = "Copied for review";
});

document.querySelector("#experiment-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  save("nyx-experiments", [...load("nyx-experiments"), data]);
  event.target.reset();
  render();
});
