document.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-conversion]");
  if (!link) return;

  const detail = {
    conversion_type: link.dataset.conversion,
    conversion_ref: link.dataset.ref,
    source_path: window.location.pathname,
    destination_host: new URL(link.href).hostname,
  };

  window.dispatchEvent(new CustomEvent("nyx:conversion", { detail }));

  if (typeof window.gtag === "function") {
    window.gtag("event", `${detail.conversion_type}_click`, {
      conversion_ref: detail.conversion_ref,
      source_path: detail.source_path,
      transport_type: "beacon",
    });
  }
});
