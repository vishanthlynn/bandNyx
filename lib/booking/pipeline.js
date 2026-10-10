const STATUSES = [
  "New",
  "Researched",
  "Ready to Contact",
  "Contacted",
  "Follow-up",
  "Negotiation",
  "Won",
  "Lost",
];

const CSV_COLUMNS = [
  "organization",
  "contactName",
  "contactChannel",
  "sourceUrl",
  "sourceDate",
  "eventType",
  "city",
  "eventDate",
  "evidence",
  "estimatedValue",
  "quotedFee",
  "collectedRevenue",
  "status",
  "nextFollowUp",
  "nextAction",
  "lossReason",
  "doNotContact",
  "notes",
];

function daysUntil(eventDate, today) {
  if (!eventDate) return null;
  const event = new Date(`${eventDate}T00:00:00Z`);
  const current = new Date(`${today}T00:00:00Z`);
  return Math.round((event - current) / 86400000);
}

function scoreLead(lead, today) {
  let score = 0;
  const reasons = [];
  if (lead.evidence) {
    score += 30;
    reasons.push("Evidence that live entertainment is relevant");
  }
  const days = daysUntil(lead.eventDate, today);
  if (days !== null && days >= 14 && days <= 180) {
    score += 25;
    reasons.push("Actionable event timing");
  } else if (days !== null && days >= 0) {
    score += 10;
  }
  if (["college-fest", "corporate", "wedding"].includes(lead.eventType)) {
    score += 20;
    reasons.push("Fits NYX event formats");
  }
  if (["Vijayawada", "Guntur", "Hyderabad", "Tirupati", "Kurnool"].includes(lead.city)) {
    score += 15;
    reasons.push("Verified service geography");
  }
  const value = Number(lead.estimatedValue) || 0;
  if (value > 0) {
    score += Math.min(10, Math.round(value / 10000));
    reasons.push("Commercial value recorded");
  }
  if (lead.sourceUrl) score += 10;
  return { score, reasons, daysUntil: days };
}

function normalizeLead(input, today) {
  const lead = {
    id: input.id || `lead-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    organization: String(input.organization || "").trim(),
    contactName: String(input.contactName || "").trim(),
    contactChannel: String(input.contactChannel || "").trim(),
    sourceUrl: String(input.sourceUrl || "").trim(),
    sourceDate: input.sourceDate || today,
    eventType: input.eventType || "other",
    city: String(input.city || "").trim(),
    eventDate: input.eventDate || "",
    evidence: String(input.evidence || "").trim(),
    status: STATUSES.includes(input.status) ? input.status : "New",
    estimatedValue: Number(input.estimatedValue) || 0,
    quotedFee: Number(input.quotedFee) || 0,
    collectedRevenue: Number(input.collectedRevenue) || 0,
    lossReason: String(input.lossReason || "").trim(),
    nextFollowUp: input.nextFollowUp || "",
    nextAction: String(input.nextAction || "").trim(),
    notes: String(input.notes || "").trim(),
    doNotContact: input.doNotContact === true || input.doNotContact === "true",
    confidence: input.sourceUrl && input.evidence ? "verified-source" : "estimate",
  };
  return { ...lead, ...scoreLead(lead, today) };
}

function dedupeLeads(leads) {
  const seen = new Set();
  return leads.filter((lead) => {
    const key = `${lead.organization}|${lead.eventDate}|${lead.city}`.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  const input = text.replace(/^\uFEFF/, "");
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    if (quoted && char === '"' && input[index + 1] === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && input[index + 1] === "\n") index += 1;
      row.push(cell.trim());
      if (row.some(Boolean)) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell || row.length) {
    row.push(cell.trim());
    if (row.some(Boolean)) rows.push(row);
  }
  const [headers, ...body] = rows;
  if (!headers) return [];
  return body.map((cells) => Object.fromEntries(headers.map((header, index) => [header, cells[index] || ""])));
}

function toCsv(leads) {
  const rows = leads.map((lead) => CSV_COLUMNS.map((column) => `"${String(lead[column] || "").replaceAll('"', '""')}"`).join(","));
  return `${CSV_COLUMNS.join(",")}\n${rows.join("\n")}\n`;
}

function dailyActions(leads, today) {
  return leads
    .filter((lead) => !lead.doNotContact)
    .filter((lead) => lead.status === "Ready to Contact" || (lead.nextFollowUp && lead.nextFollowUp <= today))
    .sort((left, right) => right.score - left.score);
}

function outreachDraft(lead) {
  if (lead.doNotContact) return "This organizer is marked do-not-contact. Do not prepare or send outreach.";
  const audience = {
    "college-fest": "your college festival",
    corporate: "your corporate event",
    wedding: "your wedding celebration",
    venue: "events at your venue",
    agency: "events you produce",
  }[lead.eventType] || "your event";
  return [
    `Hello ${lead.contactName || lead.organization || "there"},`,
    "",
    `I am writing from Band Nyx, a six-piece live band based in Vijayawada. We perform Telugu, Hindi and English sets for ${audience}.`,
    lead.eventDate ? `I saw that your event is listed for ${lead.eventDate}.` : "",
    lead.city ? `We can discuss availability for ${lead.city}.` : "",
    "If you are considering live music, I can share performance videos, our technical requirements and a quotation for your date.",
    "",
    "Band Nyx",
    "+91 79950 22614",
    "https://band-nyx.vercel.app/booking",
    "",
    "Review this draft before sending. Historical performance fees have varied around ₹30,000 and are not a current quotation.",
  ].filter((line) => line !== "").join("\n");
}

function revenueSummary(leads, events) {
  const clicks = events.filter((event) => ["call", "whatsapp"].includes(event.conversion_type));
  const formCompletions = events.filter((event) => event.conversion_type === "form_completion");
  const won = leads.filter((lead) => lead.status === "Won");
  return {
    opportunities: leads.length,
    readyToContact: leads.filter((lead) => lead.status === "Ready to Contact").length,
    followUpsDue: leads.filter((lead) => lead.status === "Follow-up" || lead.status === "Contacted").length,
    qualifiedEnquiries: formCompletions.length,
    clickCount: clicks.length,
    clickNote: "Clicks are not answered calls or completed WhatsApp conversations.",
    quotations: leads.filter((lead) => lead.quotedFee > 0).length,
    confirmedBookings: won.length,
    pipelineValue: leads.reduce((sum, lead) => sum + (Number(lead.estimatedValue) || 0), 0),
    contractedValue: leads.filter((lead) => lead.status === "Won" || lead.status === "Negotiation")
      .reduce((sum, lead) => sum + (Number(lead.quotedFee) || 0), 0),
    collectedRevenue: won.reduce((sum, lead) => sum + (Number(lead.collectedRevenue) || 0), 0),
  };
}

const pipelineApi = {
  STATUSES,
  CSV_COLUMNS,
  scoreLead,
  normalizeLead,
  dedupeLeads,
  parseCsv,
  toCsv,
  dailyActions,
  outreachDraft,
  revenueSummary,
};

if (typeof module !== "undefined" && module.exports) module.exports = pipelineApi;
if (typeof window !== "undefined") window.NyxPipeline = pipelineApi;
