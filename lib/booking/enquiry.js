const EVENT_TYPES = [
  "college-fest",
  "corporate",
  "wedding",
  "private",
  "cultural",
  "other",
];

const LIMITS = {
  name: 80,
  phone: 20,
  organization: 120,
  city: 80,
  venue: 120,
  requirements: 1000,
};

function clean(value, limit) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function validateEnquiry(input, now = Date.now()) {
  const errors = {};
  if (clean(input.company, 80)) errors.company = "Spam check failed";
  const startedAt = Number(input.startedAt);
  if (!Number.isFinite(startedAt) || now - startedAt < 1500) {
    errors.startedAt = "Please review the form before submitting";
  }

  const value = {
    name: clean(input.name, LIMITS.name),
    phone: clean(input.phone, LIMITS.phone),
    organization: clean(input.organization, LIMITS.organization),
    eventType: clean(input.eventType, 40),
    eventDate: clean(input.eventDate, 10),
    city: clean(input.city, LIMITS.city),
    venue: clean(input.venue, LIMITS.venue),
    budget: clean(input.budget, 40),
    requirements: clean(input.requirements, LIMITS.requirements),
    sourcePath: clean(input.sourcePath, 160),
    utm: {
      source: clean(input.utmSource, 80),
      medium: clean(input.utmMedium, 80),
      campaign: clean(input.utmCampaign, 80),
    },
  };

  if (value.name.length < 2) errors.name = "Enter your name";
  if (!/^[0-9+\-\s()]{8,20}$/.test(value.phone)) errors.phone = "Enter a valid phone number";
  if (!EVENT_TYPES.includes(value.eventType)) errors.eventType = "Choose an event type";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value.eventDate)) errors.eventDate = "Choose an event date";
  if (value.city.length < 2) errors.city = "Enter the city";

  return { ok: Object.keys(errors).length === 0, errors, value };
}

function enquiryMessage(value, reference) {
  return [
    "Hi Band Nyx, I would like a quotation for a live performance.",
    `Name: ${value.name}`,
    `Phone: ${value.phone}`,
    value.organization ? `Organization: ${value.organization}` : "",
    `Event type: ${value.eventType}`,
    `Date: ${value.eventDate}`,
    `City: ${value.city}`,
    value.venue ? `Venue: ${value.venue}` : "",
    value.budget ? `Estimated budget: ${value.budget}` : "",
    value.requirements ? `Requirements: ${value.requirements}` : "",
    `Ref: ${reference}`,
  ].filter(Boolean).join("\n");
}

async function deliverEnquiry(payload, env, fetchImpl = fetch) {
  const webhook = env.ENQUIRY_WEBHOOK_URL;
  if (!webhook) {
    return { delivered: false, channel: "not_configured" };
  }
  const response = await fetchImpl(webhook, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(env.ENQUIRY_WEBHOOK_TOKEN
        ? { authorization: `Bearer ${env.ENQUIRY_WEBHOOK_TOKEN}` }
        : {}),
    },
    body: JSON.stringify(payload),
  });
  return {
    delivered: response.ok,
    channel: "webhook",
    status: response.status,
  };
}

module.exports = {
  EVENT_TYPES,
  validateEnquiry,
  enquiryMessage,
  deliverEnquiry,
};
