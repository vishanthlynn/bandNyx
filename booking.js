const form = document.querySelector(".booking-form");
const status = document.querySelector(".booking-status");

function utm(name) {
  return new URLSearchParams(window.location.search).get(name) || "";
}

function track(conversionType, detail) {
  const payload = { conversion_type: conversionType, source_path: window.location.pathname, ...detail };
  const events = JSON.parse(localStorage.getItem("nyx-events") || "[]");
  events.push({ ...payload, time: new Date().toISOString() });
  localStorage.setItem("nyx-events", JSON.stringify(events.slice(-500)));
  window.dispatchEvent(new CustomEvent("nyx:conversion", { detail: payload }));
  if (typeof window.gtag === "function") {
    window.gtag("event", `${conversionType}`, payload);
  }
}

document.querySelectorAll('a[href^="tel:"]').forEach((link) => {
  link.dataset.conversion = link.dataset.conversion || "call";
  link.dataset.ref = link.dataset.ref || "CALL";
});

if (!document.querySelector(".mobile-booking-bar")) {
  const bar = document.createElement("div");
  bar.className = "mobile-booking-bar";
  bar.innerHTML = `
    <a href="tel:+917995022614" data-conversion="call" data-ref="MOBILE-CALL">Call</a>
    <a href="https://wa.me/917995022614?text=Hi%20Band%20Nyx%2C%20I%20want%20a%20quotation%20for%20a%20live%20performance.%20Ref%3A%20MOBILE-WA" data-conversion="whatsapp" data-ref="MOBILE-WA">WhatsApp</a>
    <a href="/booking">Enquiry</a>`;
  document.body.append(bar);
}

if (form && status) {
  const started = document.createElement("input");
  started.type = "hidden";
  started.name = "startedAt";
  started.value = String(Date.now());
  form.append(started);
  let startedEvent = false;
  form.addEventListener("focusin", () => {
    if (startedEvent) return;
    startedEvent = true;
    track("form_start", { conversion_ref: "BOOKING-FORM" });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.hidden = false;
    status.textContent = "Checking your enquiry…";
    const data = Object.fromEntries(new FormData(form));
    data.utmSource = utm("utm_source");
    data.utmMedium = utm("utm_medium");
    data.utmCampaign = utm("utm_campaign");
    data.sourcePath = window.location.pathname;
    try {
      const response = await fetch("/api/enquiry", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      if (!response.ok && response.status !== 202) {
        status.textContent = Object.values(result.errors || { form: "Please check the form." }).join(" ");
        return;
      }
      track("form_completion", { conversion_ref: result.reference, delivered: result.delivered });
      if (result.delivered) {
        status.textContent = `Enquiry delivered. Reference ${result.reference}.`;
        form.reset();
        return;
      }
      status.textContent = `Server delivery is not configured. Send the prepared WhatsApp message to complete enquiry ${result.reference}. This is not counted as a delivered lead.`;
      window.open(result.whatsappUrl, "_blank", "noopener");
    } catch {
      status.textContent = "The enquiry could not be delivered. Please call +91 79950 22614 or use WhatsApp.";
    }
  });
}
