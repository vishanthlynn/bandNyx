# Permitted competitor observations

Place manually collected or licensed SERP exports in `serp/` using
`template.csv`.

Rules enforced by the importer:

- one observation date, query, locale and device per result set;
- positions 1–20 only;
- an observer and source note are mandatory;
- result URLs must use HTTP or HTTPS;
- at most 20 rows per query/date/device.

Do not scrape Google. Google Search Console describes only NYX's own
performance. A future automated competitor provider must expose a licensed API
and write the same CSV schema so reports remain provider-independent.
