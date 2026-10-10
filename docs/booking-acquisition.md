# Booking acquisition

The public site keeps its current design. Booking actions, enquiry delivery
and the organizer pipeline sit on top of it.

## Verified contact paths

- Call: `+91 79950 22614` and `+91 90597 53108`
- WhatsApp: `917995022614`
- Enquiry form: `/booking`
- Pipeline: `/admin` (noindex, omitted from the sitemap)

## Enquiry delivery

`POST /api/enquiry` validates the form. It returns `delivered: true` only when
`ENQUIRY_WEBHOOK_URL` accepts the JSON payload. Without that variable the
response is HTTP 202, `delivered: false`, and the browser opens a prepared
WhatsApp message. That state is not a delivered lead and not a confirmed
booking.

Optional: `ENQUIRY_WEBHOOK_TOKEN` is sent as a bearer token.

A phone or WhatsApp click is stored as a click. It is not recorded as an
answered call or a completed conversation.

## Admin pipeline

Set `ADMIN_ACCESS_TOKEN` on the host. The dashboard at `/admin` calls
`/api/admin-gate` before it opens on the public host. On localhost it opens
for local review.

Leads live in the browser until you export CSV. The page starts empty. Use
`seo/imports/leads/template.csv` as the column header, then add rows only from
sources you have opened. Drafts are copied for manual review and are never
sent by the site.

Do not contact a lead marked do-not-contact.

## Revenue fields

- Estimated value: unqualified pipeline estimate
- Quoted fee: amount actually quoted
- Collected revenue: money recorded on a won lead

The ₹5 lakh figure is a business target, not a forecast. Historical fees
around ₹30,000 are context for drafts, not a published rate.

## Local checks

```bash
node --test tests/test_booking.js
python3 -m unittest discover -s tests -v
python3 -m scripts.search_intel audit
```

## Deployment and rollback

Do not deploy until you approve it. Production still needs a Vercel login
before any new commit can go live.

To roll back, redeploy the previous Git commit. Unset `ENQUIRY_WEBHOOK_URL`
to stop server delivery without removing call and WhatsApp links.

## Still manual

- Google Search Console service account: `GSC_SERVICE_ACCOUNT_JSON`
- Weekly pull-request token: `SEO_PR_TOKEN`
- Enquiry webhook and admin token above
- GA4, if you add a gtag snippet yourself
- Organizer research and sending outreach
