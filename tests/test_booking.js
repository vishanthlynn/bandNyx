const { test } = require("node:test");
const assert = require("node:assert/strict");
const { validateEnquiry, enquiryMessage, deliverEnquiry } = require("../lib/booking/enquiry");
const { normalizeLead, dedupeLeads, parseCsv, outreachDraft, revenueSummary, dailyActions } = require("../lib/booking/pipeline");
const { authorizeAdmin } = require("../lib/booking/admin");

const valid = {
  name: "Ananya Rao",
  phone: "+91 79950 22614",
  organization: "Campus Fest",
  eventType: "college-fest",
  eventDate: "2026-12-01",
  city: "Vijayawada",
  venue: "Open air stage",
  startedAt: Date.now() - 5000,
};

test("accepts a complete enquiry", () => {
  const result = validateEnquiry(valid);
  assert.equal(result.ok, true);
  assert.equal(result.value.city, "Vijayawada");
});

test("rejects a missing date and invalid phone", () => {
  const result = validateEnquiry({ ...valid, phone: "123", eventDate: "" });
  assert.equal(result.ok, false);
  assert.ok(result.errors.phone);
  assert.ok(result.errors.eventDate);
});

test("rejects a filled honeypot", () => {
  const result = validateEnquiry({ ...valid, company: "spam" });
  assert.equal(result.ok, false);
});

test("rejects a form submitted too quickly", () => {
  const result = validateEnquiry({ ...valid, startedAt: Date.now() });
  assert.equal(result.ok, false);
});

test("builds a quotation message without claiming delivery", () => {
  const message = enquiryMessage(validateEnquiry(valid).value, "ENQ-TEST");
  assert.match(message, /quotation/);
  assert.match(message, /ENQ-TEST/);
});

test("does not claim delivery when no webhook is configured", async () => {
  const result = await deliverEnquiry({ reference: "ENQ-TEST" }, {});
  assert.equal(result.delivered, false);
  assert.equal(result.channel, "not_configured");
});

test("claims delivery only after the webhook succeeds", async () => {
  const calls = [];
  const result = await deliverEnquiry({ reference: "ENQ-TEST" }, { ENQUIRY_WEBHOOK_URL: "https://example.test/hook" }, async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 204 };
  });
  assert.equal(result.delivered, true);
  assert.equal(calls.length, 1);
});

test("reports failed webhook delivery", async () => {
  const result = await deliverEnquiry({}, { ENQUIRY_WEBHOOK_URL: "https://example.test/hook" }, async () => ({ ok: false, status: 500 }));
  assert.equal(result.delivered, false);
  assert.equal(result.status, 500);
});

test("scores a sourced college opportunity above an empty lead", () => {
  const strong = normalizeLead({
    organization: "City College",
    eventType: "college-fest",
    city: "Vijayawada",
    eventDate: "2026-12-20",
    evidence: "Official fest page says live entertainment",
    sourceUrl: "https://example.edu/fest",
    estimatedValue: 30000,
  }, "2026-10-11");
  const empty = normalizeLead({ organization: "Unknown" }, "2026-10-11");
  assert.ok(strong.score > empty.score);
  assert.equal(strong.confidence, "verified-source");
  assert.equal(empty.confidence, "estimate");
});

test("deduplicates the same organizer, date and city", () => {
  const leads = dedupeLeads([
    normalizeLead({ organization: "City College", eventDate: "2026-12-20", city: "Vijayawada" }, "2026-10-11"),
    normalizeLead({ organization: "city college", eventDate: "2026-12-20", city: "Vijayawada" }, "2026-10-11"),
  ]);
  assert.equal(leads.length, 1);
});

test("imports only supplied CSV rows", () => {
  const rows = parseCsv("organization,city\nCity College,Vijayawada\n");
  assert.deepEqual(rows, [{ organization: "City College", city: "Vijayawada" }]);
});

test("blocks outreach drafts for do-not-contact leads", () => {
  const lead = normalizeLead({ organization: "Private Host", doNotContact: true }, "2026-10-11");
  assert.match(outreachDraft(lead), /do-not-contact/i);
});

test("keeps click counts separate from revenue", () => {
  const summary = revenueSummary(
    [normalizeLead({ organization: "Host", status: "Won", quotedFee: 40000, collectedRevenue: 25000 }, "2026-10-11")],
    [{ conversion_type: "call" }, { conversion_type: "form_completion" }],
  );
  assert.equal(summary.clickCount, 1);
  assert.equal(summary.qualifiedEnquiries, 1);
  assert.equal(summary.collectedRevenue, 25000);
  assert.match(summary.clickNote, /not answered calls/);
});

test("prioritizes ready leads and due follow-ups", () => {
  const actions = dailyActions([
    normalizeLead({ organization: "Later", status: "New" }, "2026-10-11"),
    normalizeLead({ organization: "Now", status: "Ready to Contact", city: "Guntur", eventType: "corporate", evidence: "Public page", sourceUrl: "https://example.com" }, "2026-10-11"),
  ], "2026-10-11");
  assert.deepEqual(actions.map((lead) => lead.organization), ["Now"]);
});

test("locks the dashboard until an admin token is configured and matched", () => {
  assert.equal(authorizeAdmin("", {}).status, 503);
  assert.equal(authorizeAdmin("Bearer wrong", { ADMIN_ACCESS_TOKEN: "secret" }).status, 401);
  assert.equal(authorizeAdmin("Bearer secret", { ADMIN_ACCESS_TOKEN: "secret" }).status, 200);
});
