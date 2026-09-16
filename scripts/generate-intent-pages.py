#!/usr/bin/env python3
"""Generate intent landing pages, sitemap entries, and seo-query-map.json."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://band-nyx.vercel.app"

BOOK = (
    '<p><strong>Book Band Nyx:</strong> <a href="tel:+917995022614">+91 79950 22614</a> · '
    '<a href="tel:+919059753108">+91 90597 53108</a> · '
    '<a href="https://instagram.com/band.nyx">@band.nyx</a> · '
    '<a href="/booking">Booking</a> · <a href="/">Press kit home</a></p>'
)

INTENTS = [
    ("live-music-vijayawada", "Live music Vijayawada — Band Nyx bookings", "Live music in Vijayawada",
     "Band Nyx is a Vijayawada-based six-piece live band for weddings, college fests, corporate nights and private concerts.",
     ["live music Vijayawada", "live music bands Vijayawada", "bands in Vijayawada"],
     ["Vijayawada home base", "50+ performances on official press kit", "Telugu, Hindi and English sets"]),
    ("live-music-hyderabad", "Live music Hyderabad — Band Nyx travel bookings", "Live music in Hyderabad",
     "Band Nyx travels to Hyderabad for college fests, corporate events and private concerts with full six-piece lineup.",
     ["live music Hyderabad", "live bands Hyderabad", "bands in Hyderabad"],
     ["Hyderabad listed among cities performed", "Professional booking coordination", "Rock, pop and regional languages"]),
    ("live-music-guntur", "Live music Guntur — Band Nyx Andhra Pradesh", "Live music in Guntur",
     "Band Nyx performs in Guntur and across Andhra Pradesh from its Vijayawada base.",
     ["live music Guntur", "bands Guntur", "live bands Guntur"],
     ["Guntur on official city list", "College and cultural events", "50+ press kit performances overall"]),
    ("live-music-tirupati", "Live music Tirupati — Band Nyx events", "Live music in Tirupati",
     "Band Nyx books destination and campus events in Tirupati and surrounding areas.",
     ["live music Tirupati", "bands Tirupati", "best bands Tirupati"],
     ["Tirupati on official city list", "Cultural and private events", "Six-piece live band"]),
    ("live-music-bands-andhra-pradesh", "Live music bands Andhra Pradesh — Band Nyx", "Live music bands in Andhra Pradesh",
     "Band Nyx is a professional live band serving Andhra Pradesh with Vijayawada as home base.",
     ["live music bands in Andhra Pradesh", "best live bands Andhra Pradesh", "professional bands Andhra Pradesh"],
     ["Cities: Vijayawada, Guntur, Tirupati, Kurnool bookings", "Telugu live band capability", "Weddings and fests"]),
    ("wedding-band-vijayawada", "Wedding band Vijayawada — Band Nyx reception & sangeet", "Wedding band in Vijayawada",
     "Band Nyx performs high-energy wedding receptions, sangeet and cocktail nights in Vijayawada with flexible Telugu and Bollywood sets.",
     ["wedding band Vijayawada", "best wedding bands Vijayawada", "Telugu wedding band", "live band for wedding reception"],
     ["Wedding receptions on press kit venue list", "50+ live performances", "Six musicians, full stage energy"]),
    ("wedding-band-hyderabad", "Wedding band Hyderabad — hire Band Nyx", "Wedding band in Hyderabad",
     "Band Nyx travels to Hyderabad for wedding receptions and private celebrations.",
     ["wedding band Hyderabad", "live band for wedding Hyderabad", "wedding entertainment Hyderabad"],
     ["Hyderabad performances listed officially", "Telugu, Hindi, English setlists", "Book via phone or @band.nyx"]),
    ("live-band-wedding", "Live band for wedding — Band Nyx India", "Live band for wedding",
     "Band Nyx provides live music for wedding receptions, engagement parties and sangeet programmes across Andhra Pradesh and Telangana.",
     ["live band for wedding", "band for wedding reception", "wedding music band", "live music for wedding"],
     ["Resorts and wedding venues on press materials", "Crowd-focused performances", "Professional event coordination"]),
    ("corporate-event-band", "Corporate event band — Band Nyx live music", "Corporate event band",
     "Band Nyx performs for corporate annual days, brand activations, office parties and company celebrations.",
     ["corporate event band", "live band for corporate event", "corporate entertainment band", "band for office party"],
     ["Corporate events on venue grid", "Flexible setlists for mixed audiences", "On-time professional team"]),
    ("corporate-band-hyderabad", "Corporate band Hyderabad — Band Nyx", "Corporate band in Hyderabad",
     "Band Nyx books corporate nights and company events in Hyderabad.",
     ["corporate band Hyderabad", "corporate entertainment Hyderabad", "band for company event Hyderabad"],
     ["Hyderabad city performances", "English and Telugu corporate-friendly sets", "Booking: +91 79950 22614"]),
    ("college-fest-band", "College fest band — Band Nyx Battle of Bands", "College fest live band",
     "Band Nyx specializes in college festivals and campus concerts, with Battle of Bands wins at KL University and SRM University AP.",
     ["college fest band", "college fest live band", "band for college event", "live music for college fest"],
     ["Battle of Bands — KL University", "Battle of Bands — SRM University AP", "High-energy crowd engagement"]),
    ("book-live-band", "Book a live band — Band Nyx Andhra Pradesh", "Book a live band",
     "Book Band Nyx for weddings, fests, corporate events and private parties. Call or WhatsApp to check dates and setlists.",
     ["book a live band", "live band booking", "hire a live band", "band booking Vijayawada"],
     ["Official booking phones listed on site", "Instagram @band.nyx", "Press kit with services overview"]),
    ("hire-live-band-vijayawada", "Hire live band Vijayawada — Band Nyx", "Hire a live band in Vijayawada",
     "Hire Band Nyx in Vijayawada for local events with minimal travel logistics.",
     ["hire band Vijayawada", "live band booking Vijayawada", "band booking Vijayawada"],
     ["Vijayawada-based band", "50+ press kit performances", "Same-day coordination for local venues"]),
    ("hire-live-band-hyderabad", "Hire live band Hyderabad — Band Nyx", "Hire a live band in Hyderabad",
     "Hire Band Nyx for Hyderabad events; travel and production planned with your organizer.",
     ["hire band Hyderabad", "band booking Hyderabad", "live band booking Hyderabad"],
     ["Hyderabad on city list", "Six-piece professional lineup", "Telugu and Bollywood coverage"]),
    ("telugu-live-band", "Telugu live band — Band Nyx Vijayawada", "Telugu live band",
     "Band Nyx performs Telugu crowd favorites alongside Hindi and English hits for weddings, fests and private shows.",
     ["Telugu live band", "Telugu band Vijayawada", "Telugu rock band", "Telugu wedding band"],
     ["Telugu listed in press kit languages", "Andhra Pradesh home market", "Live band (not DJ)"]),
    ("party-band-private-events", "Party band — Band Nyx private events", "Live band for private party",
     "Band Nyx performs birthday parties, house parties, anniversaries and private concerts.",
     ["live band for party", "band for birthday party", "band for private party", "birthday live music"],
     ["Private concerts on press kit", "Flexible setlists", "Crowd engagement focus"]),
    ("bollywood-live-band", "Bollywood live band — Band Nyx", "Bollywood live band",
     "Band Nyx includes Bollywood and Hindi hits in wedding and corporate setlists.",
     ["Bollywood live band", "Hindi live band", "Bollywood wedding band"],
     ["Hindi in press kit languages", "Wedding and fest experience", "Full live band"]),
    ("rock-band-vijayawada", "Rock band Vijayawada — Band Nyx", "Rock band in Vijayawada",
     "Band Nyx: Rock. Melody. Energy. — live rock and pop with Telugu and English vocals.",
     ["rock band Vijayawada", "pop band Vijayawada", "live rock band Andhra Pradesh"],
     ["Rock-forward press kit positioning", "Battle of Bands history", "Six-piece band"]),
    ("destination-wedding-band", "Destination wedding band — Band Nyx travel", "Band for destination wedding",
     "Band Nyx travels for destination weddings and resort events across South India when dates align.",
     ["band for destination wedding", "destination wedding live music", "resort event band"],
     ["Resorts on venue press sheet", "International show on timeline (Charlotte USA)", "Professional travel coordination"]),
    ("wedding-band-guntur", "Wedding band Guntur — Band Nyx", "Wedding band in Guntur",
     "Band Nyx travels from Vijayawada for wedding receptions and celebrations in Guntur.",
     ["wedding band Guntur", "live band wedding Guntur", "Telugu wedding band Guntur"],
     ["Guntur on official city list", "Wedding venues on press kit", "Telugu and Bollywood sets"]),
    ("wedding-band-tirupati", "Wedding band Tirupati — Band Nyx", "Wedding band in Tirupati",
     "Band Nyx performs wedding receptions and private events in Tirupati and nearby areas.",
     ["wedding band Tirupati", "live music wedding Tirupati"],
     ["Tirupati performances listed", "Destination-friendly travel", "Six-piece band"]),
    ("college-fest-band-vijayawada", "College fest band Vijayawada — Band Nyx", "College fest band in Vijayawada",
     "Band Nyx is built for campus festivals and Battle of Bands stages in the Vijayawada region.",
     ["college fest band Vijayawada", "band for college event Vijayawada", "university live band Vijayawada"],
     ["Battle of Bands wins", "50+ press kit performances", "Crowd engagement"]),
    ("live-band-booking-andhra-pradesh", "Live band booking Andhra Pradesh — Band Nyx", "Live band booking in Andhra Pradesh",
     "Book Band Nyx for weddings, fests and corporate events across Andhra Pradesh.",
     ["live band booking Vijayawada", "live band booking Hyderabad", "band booking Andhra Pradesh", "hire live band"],
     ["Official phones on website", "Press kit services list", "Instagram @band.nyx"]),
    ("professional-live-band-vijayawada", "Professional live band Vijayawada — Band Nyx", "Professional live band in Vijayawada",
     "Band Nyx is a six-piece professional live band based in Vijayawada for fests, weddings and corporate clients.",
     ["professional live band Vijayawada", "best live band Vijayawada", "top bands Vijayawada"],
     ["Home base Vijayawada", "Award-winning fest history", "Telugu Hindi English"]),
    ("professional-live-band-hyderabad", "Professional live band Hyderabad — Band Nyx", "Professional live band in Hyderabad",
     "Band Nyx delivers professional six-piece live shows for Hyderabad events with travel support.",
     ["professional live band Hyderabad", "best live band Hyderabad", "hire band Hyderabad"],
     ["Hyderabad city performances", "Corporate and wedding capable", "Full lineup"]),
]


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_page(slug, title, h1, intro, queries, bullets):
    canonical = f"{BASE}/{slug}"
    meta_desc = intro if len(intro) <= 160 else intro[:157] + "..."
    bl = "\n".join(f"        <li>{b}</li>" for b in bullets)
    qmeta = ", ".join(queries[:4])
    ql = ", ".join(json.dumps(q) for q in queries)
    intro_json = esc(intro)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{esc(meta_desc)}" />
  <meta name="robots" content="index,follow" />
  <title>{esc(title)}</title>
  <link rel="canonical" href="{canonical}" />
  <link rel="stylesheet" href="/styles.css" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": "{esc(title)}",
    "description": "{intro_json}",
    "url": "{canonical}",
    "about": {{"@id": "{BASE}/#band-nyx"}},
    "keywords": [{ql}],
    "breadcrumb": {{
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{"@type": "ListItem", "position": 1, "name": "Band Nyx", "item": "{BASE}/"}},
        {{"@type": "ListItem", "position": 2, "name": "{esc(h1)}", "item": "{canonical}"}}
      ]
    }}
  }}
  </script>
</head>
<body class="seo-crawl-page">
  <main class="seo-page-main">
    <div class="container page-content seo-prose">
      <p class="eyebrow">Band Nyx · {esc(qmeta)}</p>
      <h1>{esc(h1)}</h1>
      <p>{esc(intro)}</p>
      <h2>Why Band Nyx fits this search</h2>
      <ul>
{bl}
      </ul>
      <h2>Related</h2>
      <p><a href="/best-bands-vijayawada">Bands Vijayawada</a> · <a href="/best-bands-hyderabad">Bands Hyderabad</a> · <a href="/booking">Booking</a> · <a href="/live">Performances</a> · <a href="/members">Members</a> · <a href="/site-index.html">All pages</a></p>
      {BOOK}
    </div>
  </main>
</body>
</html>
"""


def main():
    query_map = []
    for slug, title, h1, intro, queries, bullets in INTENTS:
        (ROOT / f"{slug}.html").write_text(
            render_page(slug, title, h1, intro, queries, bullets), encoding="utf-8"
        )
        for q in queries:
            query_map.append({"query": q, "url": f"{BASE}/{slug}"})

    static = ["", "band-nyx-vijayawada", "members", "music", "live", "booking"]
    city = sorted({f.stem for f in ROOT.glob("best-bands-*.html")} |
                  {f.stem for f in ROOT.glob("bands-*.html")} |
                  {f.stem for f in ROOT.glob("live-bands-*.html")} -
                  {"bands-near-me-andhra-pradesh"})
    events = sorted(f"events/{f.stem}" for f in (ROOT / "events").glob("*.html"))
    intents = [i[0] for i in INTENTS]
    all_paths = list(dict.fromkeys(static + city + intents + events + ["site-index", "get-listed"]))

    # HTML site index for crawlers (not linked from press kit nav)
    sections = [
        ("Press kit", static),
        ("City searches", city),
        ("Services & booking intent", intents),
        ("Events", events),
        ("Listings & outreach", ["get-listed"]),
    ]
    links_html = []
    for heading, paths in sections:
        links_html.append(f"      <h2>{heading}</h2>\n      <ul>")
        for p in paths:
            loc = "/" if p == "" else (f"/{p}" if not p.startswith("events/") else f"/{p}")
            label = "Home — press kit" if p == "" else p.replace("-", " ").replace("/", " — ")
            links_html.append(f'        <li><a href="{loc}">{esc(label)}</a></li>')
        links_html.append("      </ul>")
    site_index = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="index,follow" />
  <title>Band Nyx — site index (all public pages)</title>
  <meta name="description" content="Complete index of Band Nyx official pages: Vijayawada live band, Hyderabad bookings, weddings, college fests, corporate events." />
  <link rel="canonical" href="{BASE}/site-index" />
  <link rel="stylesheet" href="/styles.css" />
</head>
<body class="seo-crawl-page">
  <main class="seo-page-main">
    <div class="container page-content seo-prose">
      <h1>Band Nyx — official site index</h1>
      <p>Canonical home: <a href="/">band-nyx.vercel.app press kit</a>. Instagram: <a href="https://instagram.com/band.nyx">@band.nyx</a>.</p>
{chr(10).join(links_html)}
      {BOOK}
    </div>
  </main>
</body>
</html>
"""
    (ROOT / "site-index.html").write_text(site_index, encoding="utf-8")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in all_paths:
        loc = BASE + ("/" if p == "" else f"/{p}")
        if p == "":
            pri = "1.0"
        elif p in ("booking", "band-nyx-vijayawada"):
            pri = "0.85"
        elif p == "site-index":
            pri = "0.75"
        elif p in intents:
            pri = "0.65"
        else:
            pri = "0.55"
        lines.append(f"  <url><loc>{loc}</loc><changefreq>monthly</changefreq><priority>{pri}</priority></url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "seo-query-map.json").write_text(
        json.dumps({"canonical_site": BASE, "future_domain": "https://bandnyx.com/", "queries": query_map}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(INTENTS)} intent pages, {len(all_paths)} sitemap URLs, {len(query_map)} query rows")


if __name__ == "__main__":
    main()
