document.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-conversion]");
  if (!link) return;

  const detail = {
    conversion_type: link.dataset.conversion,
    conversion_ref: link.dataset.ref,
    source_path: window.location.pathname,
    destination_host: new URL(link.href).hostname,
  };

  detail.answered = false;
  try {
    const events = JSON.parse(localStorage.getItem("nyx-events") || "[]");
    events.push({ ...detail, time: new Date().toISOString() });
    localStorage.setItem("nyx-events", JSON.stringify(events.slice(-500)));
  } catch {
    // Storage can be unavailable in private browsing.
  }

  window.dispatchEvent(new CustomEvent("nyx:conversion", { detail }));

  if (typeof window.gtag === "function") {
    window.gtag("event", `${detail.conversion_type}_click`, {
      conversion_ref: detail.conversion_ref,
      source_path: detail.source_path,
      transport_type: "beacon",
    });
  }
});
