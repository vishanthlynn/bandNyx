# Band NYX (bandnyx)

Official press kit site for **Band NYX** — rock, melody, energy.

## Live site

**https://band-nyx.vercel.app/**

Vercel is the only canonical and indexable host. GitHub Pages deployment is
intentionally disabled because it cannot enforce the redirects in
`vercel.json`.

## Local preview

```bash
cd nyx-website
python3 -m http.server 8080
```

Open http://localhost:8080

## Search intelligence

The repository includes an offline technical SEO quality gate and an optional
weekly Google Search Console collector.

```bash
python3 -m scripts.search_intel validate-data
python3 -m scripts.search_intel sync
python3 -m scripts.search_intel audit
python3 -m unittest discover -s tests -v
```

See [`docs/search-intelligence.md`](docs/search-intelligence.md) for Google
Cloud credentials, private report handling, competitor imports, verified gig
requirements and WhatsApp attribution.

Booking enquiries, delivery rules and the private organizer pipeline are
documented in [`docs/booking-acquisition.md`](docs/booking-acquisition.md).

```bash
node --test tests/test_booking.js
```

## Repository

https://github.com/vishanthlynn/bandNyx
