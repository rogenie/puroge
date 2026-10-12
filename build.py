#!/usr/bin/env python3
"""Build the Purogé site from data/site.json and data/looks/*.json (one file per look).

Usage:  python3 build.py            published looks only (what goes live)
        python3 build.py --drafts   also build looks marked "draft": true (local preview)
Output: site/  (GitHub Actions builds and publishes this automatically on every push)

Generates:
  /                           home: latest-video button, the three ways in, latest looks, values
  /latest/                    the bio link: newest looks first, same order as the feed
  /looks/                     every look, filterable by occasion, colors, mood and season
  /look/<slug>/               one page per look, Heirloom and Everyday tabs
  /<slug>/                    short link to a look (say it or show it in the video)
  /occasion/, /style/, /colors/            the three ways in (hub pages)
  /occasion/<x>/              "Where are you going?"   from tags.occasion
  /style/<piece>/             "Style a piece you own"  from each piece's "types"
  /colors/<pair>/             "Colors that work"       from tags.pairing
  /season/<x>/                season pages; mood is a filter only
  /series/<slug>/             a video that shows several looks (e.g. one color, three partners)
  /<series-slug>/             short link to a series
  /go/<slug>-<n>-h|e/         redirect to piece n, Heirloom or Everyday
Tags must come from the taxonomy in data/site.json, so hundreds of looks stay consistent.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).parent
OUT = ROOT / "site"
TIERS = [("heirloom", "h", "Heirloom", "Made to last a lifetime"),
         ("everyday", "e", "Everyday", "Same look, gentler price")]

e = lambda s: html.escape(str(s or ""))

CSS = """
:root{--bg:#f6f1e8;--ink:#2a2420;--muted:#7a6e63;--line:#e2d8c8;--card:#fffdf8;--accent:#6b2a26}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--ink:#efe7db;--muted:#a89a8a;--line:#3a332d;--card:#24201c;--accent:#d08a7d}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Inter,system-ui,sans-serif}
a{color:inherit}
.wrap{max-width:760px;margin:0 auto;padding:0 16px}
header{padding:28px 0 8px;display:flex;justify-content:space-between;align-items:baseline;gap:16px}
.brand{font-family:'Cormorant Garamond',Georgia,serif;font-size:30px;letter-spacing:.06em;text-decoration:none}
nav a{color:var(--muted);font-size:14px;text-decoration:none;margin-left:16px}
nav a:hover{color:var(--ink)}
h1{font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:clamp(34px,8vw,52px);line-height:1.08;margin:32px 0 12px}
h2{font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:30px;margin:48px 0 8px}
.meta{color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.1em}
.lesson,.lead{font-size:18px;margin:16px 0 20px}
.hero{aspect-ratio:3/4;background:var(--line);border-radius:6px;overflow:hidden;display:grid;place-items:center;color:var(--muted);font-size:14px}
.hero img{width:100%;height:100%;object-fit:cover}
.ai{font-size:12px;color:var(--muted);margin-top:6px}
.swatches{display:flex;gap:6px;margin:16px 0}
.swatches span{width:28px;height:28px;border-radius:50%;border:1px solid var(--line)}
.tabs{display:flex;border-bottom:1px solid var(--line);margin:28px 0 0}
.tabs button{flex:1;background:none;border:0;border-bottom:2px solid transparent;padding:12px 4px;font:inherit;color:var(--muted);cursor:pointer;text-align:left}
.tabs button small{display:block;font-size:12px}
.tabs button[aria-selected=true]{color:var(--ink);border-color:var(--accent)}
.tabs b{font-family:'Cormorant Garamond',Georgia,serif;font-size:22px;font-weight:500}
.panel[hidden]{display:none}
.piece{display:grid;grid-template-columns:40px 1fr auto;gap:12px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}
.num{font-family:'Cormorant Garamond',Georgia,serif;font-size:28px;color:var(--accent)}
.piece .name{font-weight:600}
.piece .sub{color:var(--muted);font-size:14px}
.mat{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px;margin-top:4px}
.btn{display:inline-block;background:var(--ink);color:var(--bg);text-decoration:none;padding:10px 18px;border-radius:99px;font-size:14px;white-space:nowrap}
.btn.off{background:none;color:var(--muted);border:1px solid var(--line)}
.note{color:var(--muted);font-size:13px;margin:24px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin:24px 0}
.card{text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:6px;overflow:hidden}
.card .hero{border-radius:0}
.card div.t{padding:12px}
.how{display:grid;gap:12px;margin:20px 0;padding:0;list-style:none;counter-reset:s}
.how li{counter-increment:s;display:grid;grid-template-columns:40px 1fr;gap:12px;align-items:baseline}
.how li::before{content:counter(s);font-family:'Cormorant Garamond',Georgia,serif;font-size:28px;color:var(--accent)}
.vals{list-style:none;padding:0;margin:16px 0 24px;display:grid;gap:14px}
.vals li{border-left:2px solid var(--accent);padding-left:14px}
.vals b{font-weight:600}
.empty{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:28px 20px;text-align:center;color:var(--muted)}
.empty b{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:26px;line-height:1.2;margin-bottom:8px;color:var(--ink)}
.names{font-family:'Cormorant Garamond',Georgia,serif;font-size:26px;line-height:1.3;margin:28px 0}
.names span{color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:6px 14px;font:inherit;font-size:14px;text-decoration:none;cursor:pointer}
.chip[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.filters{margin:8px 0 4px}
.filters .lbl{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-top:12px}
.card[hidden]{display:none}
.count{color:var(--muted);font-size:14px}
.tags a{color:var(--muted)}
.feed .card{display:grid;grid-template-columns:96px 1fr;align-items:center}
.feed .card .hero{aspect-ratio:3/4;height:auto}
.feed .card div.t{font-family:'Cormorant Garamond',Georgia,serif;font-size:22px;line-height:1.2}
.feed{grid-template-columns:1fr}
.doors{display:grid;gap:12px;margin:20px 0}
.door{display:block;text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:18px 18px 16px}
.door b{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:26px;line-height:1.15}
.door span{color:var(--muted);font-size:14px}
.door .chips{margin:10px 0 0}
.door .chips i{font-style:normal;font-size:13px;border:1px solid var(--line);border-radius:99px;padding:2px 10px;color:var(--ink)}
.hub{list-style:none;padding:0;margin:20px 0;display:grid;gap:8px}
.hub a{display:flex;justify-content:space-between;text-decoration:none;border-bottom:1px solid var(--line);padding:12px 0;font-size:17px}
.hub a span{color:var(--muted);font-size:14px}
footer{border-top:1px solid var(--line);margin-top:56px;padding:20px 0 40px;color:var(--muted);font-size:13px}
footer a{margin-right:14px}
"""

FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" rx="14" fill="#6b2a26"/>'
           '<text x="32" y="45" text-anchor="middle" font-family="Georgia,serif" '
           'font-size="40" fill="#f6f1e8">P</text></svg>')

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500&'
         'family=Inter:wght@400;600&display=swap" rel="stylesheet">')


def page(title, body, site, desc="", path="/", image=""):
    url = f"https://{site['domain']}{path}"
    img = f'<meta property="og:image" content="https://{site["domain"]}{e(image)}">' if image else ""
    socials = "".join(f'<a href="{e(s["url"])}" rel="me">{e(s["name"])}</a>' for s in site.get("socials", []))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:site_name" content="Purogé"><meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">{img}<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f6f1e8">
{FONTS}<link rel="stylesheet" href="/style.css"></head><body><div class="wrap">
<header><a class="brand" href="/">PUROGÉ</a><nav><a href="/looks/">Looks</a><a href="/values/">Values</a><a href="/story/">Story</a></nav></header>
{body}
<footer>{socials and f"<p>{socials}</p>"}<p>{e(site['dedication'])}</p><p>{e(site['disclosure'])} {e(site.get('amazon_disclosure'))}</p></footer>
</div></body></html>"""


def hero(look):
    if look.get("image"):
        return f'<div class="hero"><img src="{e(look["image"])}" alt="{e(look["title"])}" loading="lazy"></div>'
    return '<div class="hero">Look image</div>'


GROUPS = {
    # group: (url base, way-in title, way-in question, how a single page is headed)
    "occasion": ("occasion", "Where are you going?", "Complete outfits for the place you're headed.", lambda n: f"Outfits for {n.lower()}"),
    "style": ("style", "Style a piece you own", "Start from what's in your closet. Shop only what's missing.", None),
    "pairing": ("colors", "Colors that work", "Pairings that look elegant and never boring.", lambda n: n),
    "season": ("season", "By season", "", lambda n: f"{n} looks"),
}


def label(site, group, key):
    v = site["taxonomy"][group].get(key, key)
    return v["label"] if isinstance(v, dict) else v


def heading(site, group, key):
    v = site["taxonomy"][group].get(key, key)
    if isinstance(v, dict):
        return v.get("title", v["label"])
    return GROUPS[group][3](v)


def look_types(look):
    out = []
    for p in look["pieces"]:
        for t in p.get("types", []):
            if t not in out:
                out.append(t)
    return out


def members_of(looks, group, key):
    if group == "style":
        return [l for l in looks if key in look_types(l)]
    return [l for l in looks if key in l["tags"].get(group, [])]


def used_keys(site, looks, group):
    order = list(site["taxonomy"][group])
    found = {k for l in looks for k in (look_types(l) if group == "style" else l["tags"].get(group, []))}
    return [k for k in order if k in found]


def card(look, site):
    t = look["tags"]
    data = " ".join(f'data-{g}="{e(" ".join(t.get(g, [])))}"' for g in ("occasion", "pairing", "mood", "season"))
    return (f'<a class="card" href="/look/{look["slug"]}/" {data}>{hero(look)}'
            f'<div class="t"><div class="meta">{e(label(site, "kind", look["kind"]))}</div>{e(look["title"])}</div></a>')


def look_page(look, site):
    slug = look["slug"]
    sw = "".join(f'<span style="background:{e(c)}"></span>' for c in look.get("palette", []))
    tabs, panels = [], []
    for i, (key, code, lab, sub) in enumerate(TIERS):
        tabs.append(f'<button role="tab" aria-selected="{str(i == 0).lower()}" data-t="{key}">'
                    f'<b>{lab}</b><small>{sub}</small></button>')
        rows = []
        for p in look["pieces"]:
            v = p.get(key) or {}
            if v.get("sold_out") or not v.get("url"):
                btn = '<span class="btn off">Sold out</span>'
            else:
                btn = f'<a class="btn" rel="sponsored nofollow" href="/go/{slug}-{p["n"]}-{code}/">Shop</a>'
            fit = f'<div class="sub">Fit: {e(v["fit"])}</div>' if v.get("fit") else ""
            rows.append(f"""<div class="piece"><div class="num">{p['n']}</div><div>
<div class="name">{e(p['item'])}</div><div class="sub">{e(v.get('name'))} · {e(v.get('store'))} · {e(v.get('price'))}</div>
{fit}<span class="mat">{e(v.get('material'))}</span></div>{btn}</div>""")
        panels.append(f'<div class="panel" data-p="{key}"{"" if i == 0 else " hidden"}>{"".join(rows)}</div>')
    checked = max((v.get("last_checked", "") for p in look["pieces"] for k, *_ in TIERS
                   for v in [p.get(k) or {}]), default="")
    t = look["tags"]
    def links(group, keys):
        base = GROUPS[group][0]
        return "".join(f'<a class="chip" href="/{base}/{k}/">{e(label(site, group, k))}</a>' for k in keys)
    more = f"""<h2>Find more like this</h2>
<p class="lbl meta">Occasion</p><div class="chips">{links("occasion", t.get("occasion", []))}</div>
<p class="lbl meta">Colors</p><div class="chips">{links("pairing", t.get("pairing", []))}</div>
<p class="lbl meta">Style a piece</p><div class="chips">{links("style", look_types(look))}</div>"""
    mood = " · ".join(label(site, "mood", m) for m in t.get("mood", []))
    body = f"""<p class="meta" style="margin-top:24px">{e(label(site, "kind", look["kind"]))}{" · " + e(mood) if mood else ""}</p>
<h1 style="margin-top:8px">{e(look['title'])}</h1>
{hero(look)}<p class="ai">Image is AI-generated. Every piece listed below is real and was in stock when checked.</p>
<div class="swatches">{sw}</div>
<p class="lesson">{e(look.get('lesson'))}</p>
<div class="tabs" role="tablist">{"".join(tabs)}</div>{"".join(panels)}
<p class="note">Numbers match the video. Prices and stock change; last checked {e(checked)}.</p>
{more}
<p style="margin-top:24px"><a class="btn off" href="/looks/">Browse all looks</a></p>
<script>
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{{
 document.querySelectorAll('.tabs button').forEach(x=>x.setAttribute('aria-selected',x===b));
 document.querySelectorAll('.panel').forEach(p=>p.hidden=p.dataset.p!==b.dataset.t);
}});
</script>"""
    return page(f"{look['title']} | Purogé", body, site, look.get("lesson"),
                f"/look/{slug}/", look.get("image", ""))


def door(site, looks, group):
    base, title, question, _ = GROUPS[group]
    keys = used_keys(site, looks, group)[:5]
    chips = "".join(f"<i>{e(label(site, group, k))}</i>" for k in keys)
    return (f'<a class="door" href="/{base}/"><b>{e(title)}</b><span>{e(question)}</span>'
            f'<div class="chips">{chips}</div></a>')


def home_page(looks, site):
    cards = "".join(card(l, site) for l in looks[:6])
    looks_html = (f'<div class="grid">{cards}</div><a class="btn off" href="/looks/">See all {len(looks)} looks</a>'
                  if looks else
                  '<div class="empty"><b>The first looks are being scouted.</b>'
                  'Every piece checked for fabric and fit before it goes up.</div>')
    doors = (f'<div class="doors">{door(site, looks, "occasion")}{door(site, looks, "style")}{door(site, looks, "pairing")}</div>'
             if looks else "")
    body = f"""<h1>Elegant, never boring.<br>Every piece found for you.</h1>
<p class="lead">You see an outfit you love, and then the hunting starts. We do the hunting.
Every look is a complete outfit, numbered piece by piece, in two price versions.</p>
<a class="btn" href="/latest/">Find the look from our latest video</a>
<h2>Start here</h2>
{doors}
<h2 id="looks">Latest looks</h2>
{looks_html}
<h2>How it works</h2>
<ol class="how">
<li><div><b>Find a look you love</b> in our videos. Every piece in it is numbered.</div></li>
<li><div><b>Open the look here.</b> The name in the video is the address: the look "Navy and Brown" lives at puroge.com/navy-and-brown.</div></li>
<li><div><b>Pick your version.</b> Heirloom is made to last a lifetime. Everyday is the same look at a gentler price.</div></li>
</ol>
<h2>What we stand for</h2>
<ul class="vals">
<li><b>Fabric first.</b> Every piece names what it is made of. We favor natural fibers because they wear better, last longer and age well.</li>
<li><b>Elegant, never boring.</b> Classic foundations with one deliberate detail that makes the outfit yours.</li>
<li><b>Real, and honest about it.</b> Our images are AI-generated and labeled. The clothes in them are real, checked and linked.</li>
<li><b>Made to be kept.</b> Fewer, better pieces, worn for years and handed down.</li>
</ul>
<a class="btn off" href="/values/">Our values and where we're going</a>"""
    return page("Purogé | Elegant, never boring", body, site,
                "Complete elegant outfits, every piece found and linked for you, in two price versions.")


def series_card(series, by_slug, site):
    first = by_slug[series["looks"][0]["slug"]]
    return (f'<a class="card" href="/series/{series["slug"]}/">{hero(first)}'
            f'<div class="t"><div class="meta">{len(series["looks"])} looks</div>{e(series["title"])}</div></a>')


def series_page(series, by_slug, site):
    items = []
    for i, ref in enumerate(series["looks"], 1):
        l = by_slug[ref["slug"]]
        items.append(f'''<a class="card" href="/look/{l["slug"]}/">{hero(l)}
<div class="t"><div class="meta">{i} · {e(ref.get("label", ""))}{" · " + e(ref["mood"]) if ref.get("mood") else ""}</div>{e(l["title"])}</div></a>''')
    body = f"""<p class="meta" style="margin-top:24px">From our videos</p>
<h1 style="margin-top:8px">{e(series["title"])}</h1>
<p class="lead">{e(series.get("intro", ""))}</p>
<p class="note">Tap a look to see every piece, numbered as in the video, in Heirloom and Everyday versions.</p>
<div class="grid">{"".join(items)}</div>
<a class="btn off" href="/latest/">More from our videos</a>"""
    return page(f"{series['title']} | Purogé", body, site, series.get("intro", ""), f"/series/{series['slug']}/")


def latest_page(looks, site, series_list=()):
    by_slug = {l["slug"]: l for l in looks}
    in_series = {r["slug"] for sr in series_list for r in sr["looks"]}
    feed = [(sr.get("published", ""), series_card(sr, by_slug, site)) for sr in series_list]
    feed += [(l.get("published", ""), card(l, site)) for l in looks if l["slug"] not in in_series]
    feed.sort(key=lambda x: x[0], reverse=True)
    items = "".join(c for _, c in feed[:30])
    body = f"""<p class="meta" style="margin-top:24px">From our videos</p>
<h1 style="margin-top:8px">The latest looks</h1>
<p class="lead">Newest first, in the same order as our videos. Tap the one you just watched.</p>
<div class="grid feed">{items}</div>
<a class="btn off" href="/looks/">Browse every look</a>"""
    return page("Latest looks | Purogé", body, site, "The looks from our newest videos, newest first.", "/latest/")


def all_looks_page(looks, site):
    groups = []
    for g, title in (("occasion", "Occasion"), ("pairing", "Colors"), ("mood", "Mood"), ("season", "Season")):
        chips = "".join(f'<button class="chip" aria-pressed="false" data-g="{g}" data-v="{k}">{e(label(site, g, k))}</button>'
                        for k in used_keys(site, looks, g))
        groups.append(f'<p class="lbl meta">{title}</p><div class="chips">{chips}</div>')
    cards = "".join(card(l, site) for l in looks)
    body = f"""<p class="meta" style="margin-top:24px">Every look</p>
<h1 style="margin-top:8px">All looks</h1>
<div class="filters">{"".join(groups)}</div>
<p class="count" id="count">{len(looks)} looks</p>
<div class="grid" id="grid">{cards}</div>
<script>
const sel={{occasion:new Set(),pairing:new Set(),mood:new Set(),season:new Set()}};
const cards=[...document.querySelectorAll('#grid .card')], count=document.getElementById('count');
function apply(){{let n=0;cards.forEach(c=>{{const ok=Object.entries(sel).every(([g,s])=>!s.size||(c.dataset[g]||'').split(' ').some(v=>s.has(v)));c.hidden=!ok;if(ok)n++;}});count.textContent=n+(n===1?' look':' looks');}}
document.querySelectorAll('.filters .chip').forEach(b=>b.onclick=()=>{{const s=sel[b.dataset.g],on=b.getAttribute('aria-pressed')!=='true';b.setAttribute('aria-pressed',on);on?s.add(b.dataset.v):s.delete(b.dataset.v);apply();}});
</script>"""
    return page("All looks | Purogé", body, site, "Every Purogé look, filterable by occasion, colors, mood and season.", "/looks/")


def hub_page(looks, site, group):
    base, title, question, _ = GROUPS[group]
    rows = "".join(f'<li><a href="/{base}/{k}/">{e(label(site, group, k))}<span>{len(members_of(looks, group, k))}</span></a></li>'
                   for k in used_keys(site, looks, group))
    body = f"""<p class="meta" style="margin-top:24px">Start here</p>
<h1 style="margin-top:8px">{e(title)}</h1>
<p class="lead">{e(question)}</p>
<ul class="hub">{rows}</ul>
<a class="btn off" href="/looks/">Browse every look</a>"""
    return page(f"{title} | Purogé", body, site, question, f"/{base}/")


def collection_page(members, site, group, key):
    base, title, _, _ = GROUPS[group]
    head = heading(site, group, key)
    cards = "".join(card(l, site) for l in members)
    body = f"""<p class="meta" style="margin-top:24px"><a href="/{base}/">{e(title)}</a></p>
<h1 style="margin-top:8px">{e(head)}</h1>
<p class="count">{len(members)} look{"s" if len(members) != 1 else ""}</p>
<div class="grid">{cards}</div>
<a class="btn off" href="/{base}/">{e(title)}</a>"""
    return page(f"{head} | Purogé", body, site, f"Complete Purogé outfits: {head}.", f"/{base}/{key}/")


def redirect_page(to):
    return (f'<!doctype html><meta charset="utf-8"><title>Purogé</title><link rel="canonical" href="{e(to)}">'
            f'<meta http-equiv="refresh" content="0;url={e(to)}"><script>location.replace({json.dumps(to)})</script>'
            f'<a href="{e(to)}">Continue</a>')


def values_page(site):
    body = """<p class="meta" style="margin-top:24px">Values and vision</p>
<h1 style="margin-top:8px">Dress well. Buy less. Keep it longer.</h1>
<p class="lead">Purogé helps you dress with elegance that never feels boring, using clothes made to last.
Here is what guides every look we publish, and where we are going.</p>

<h2>Our values</h2>
<ul class="vals">
<li><b>Fabric first.</b> A seamstress judges clothes from the inside out. Every piece we list names its fiber,
and we favor wool, linen, cotton, silk, cashmere and leather because they wear better, breathe better and age well.
When a piece is a blend, we say so.</li>
<li><b>Sustainability you can check.</b> We don't use vague words like "eco-friendly." We tell you what a garment
is made of and let the materials speak. Buying fewer, longer-lasting pieces is the most sustainable choice there is.</li>
<li><b>Elegant, never boring.</b> Timeless foundations, then one deliberate detail: a color, a texture, an unexpected shoe.
Elegance is edited, not erased.</li>
<li><b>We do the hunting.</b> You see an outfit you love, and we find every piece in it. Two versions of each look,
Heirloom and Everyday, so good style works for more than one budget.</li>
<li><b>Honest about everything.</b> Our model images are AI-generated, and we label them. The clothes are real and checked.
Some links earn us a commission, and we disclose it.</li>
<li><b>Made to be kept.</b> Our name carries two grandmothers who sewed and sold clothes for a living.
We honor that by choosing clothes worth keeping, mending and handing down.</li>
</ul>

<h2>Our vision</h2>
<p>Today, Purogé curates: complete outfits from brands that meet our standards, found and linked for you.</p>
<p>Tomorrow, the Purogé label: premium dresses of our own, cut from natural fibers and sewn to be kept for a lifetime.
Everything we learn from curating, which pieces you love and which ones are impossible to find, shapes what we make.</p>
<p style="margin-top:28px"><a class="btn" href="/looks/">See the looks</a></p>"""
    return page("Values and vision | Purogé", body, site,
                "Fabric first, elegant never boring, made to be kept. What Purogé stands for and where it is going.",
                "/values/")


def story_page(site):
    body = """<p class="meta" style="margin-top:24px">Our story</p>
<h1 style="margin-top:8px">Named for two women who sewed.</h1>
<p class="lead">My grandmothers, Lola Purisima and Lola Roberta, sewed and sold clothes for a living.</p>
<p class="names"><span>Pu</span>risima · <span>Ro</span>berta · Ro<span>ge</span>nie</p>
<p>Purogé carries all three of us: the first sound of each Lola's name, and mine.</p>
<p>The brand works the way a good shopkeeper does. Instead of leaving you to hunt down an outfit you saw
online, we find every piece for you, check what it is made of, and put it all on one page.
Two versions of each look, so it works for more than one budget.</p>
<p>Lola is Tagalog for grandmother.</p>
<p style="margin-top:28px"><a class="btn" href="/looks/">See the looks</a></p>"""
    return page("Our story | Purogé", body, site,
                "Purogé is named for Lola Purisima and Lola Roberta, who sewed and sold clothes for a living.",
                "/story/")


def with_affiliate(url, site):
    """Add the Amazon store ID to Amazon links, replacing any other tag already on them."""
    tag = site.get("amazon_tag")
    if not url or not tag:
        return url
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if not (host == "amazon.com" or host.endswith(".amazon.com") or host in ("amzn.to", "a.co")):
        return url
    if host in ("amzn.to", "a.co"):
        return url  # short links already carry the tag they were created with
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "tag"]
    query.append(("tag", tag))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def go_page(url, back):
    if not url:
        return (f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
                f'<meta http-equiv="refresh" content="0;url={e(back)}"><a href="{e(back)}">Back to the look</a>')
    return (f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
            f'<meta http-equiv="refresh" content="0;url={e(url)}">'
            f'<script>location.replace({json.dumps(url)})</script><a href="{e(url)}">Continue to store</a>')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


RESERVED = {"series", "look", "looks", "latest", "go", "occasion", "style", "colors", "season", "story", "values",
            "favicon.svg", "style.css", "404.html", "robots.txt", "sitemap.txt", "CNAME"}


def load(show_drafts):
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    tax = site["taxonomy"]
    looks, errors, seen = [], [], set()
    for f in sorted((ROOT / "data" / "looks").glob("*.json")):
        l = json.loads(f.read_text(encoding="utf-8"))
        slug, where = l.get("slug", ""), f.name
        if slug != f.stem: errors.append(f"{where}: slug must match the file name")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug): errors.append(f"{where}: slug must be lowercase words joined by dashes")
        if slug in RESERVED: errors.append(f"{where}: '{slug}' is a reserved address")
        if slug in seen: errors.append(f"{where}: duplicate slug")
        seen.add(slug)
        if l.get("kind") not in tax["kind"]: errors.append(f"{where}: unknown kind '{l.get('kind')}'")
        for g in ("occasion", "pairing", "mood", "season"):
            for v in l.get("tags", {}).get(g, []):
                if v not in tax[g]: errors.append(f"{where}: unknown {g} '{v}' (add it to site.json first)")
        for p in l.get("pieces", []):
            if not p.get("types"): errors.append(f"{where}: piece {p.get('n')} needs at least one type")
            for v in p.get("types", []):
                if v not in tax["style"]: errors.append(f"{where}: unknown piece type '{v}' (add it to site.json first)")
        if show_drafts or not l.get("draft"):
            looks.append(l)
    if errors:
        sys.exit("Fix these before building:\n  " + "\n  ".join(errors))
    looks.sort(key=lambda l: (l.get("published", ""), l["slug"]), reverse=True)
    visible = {l["slug"] for l in looks}
    series_list = []
    for f in sorted((ROOT / "data" / "series").glob("*.json")) if (ROOT / "data" / "series").exists() else []:
        sr = json.loads(f.read_text(encoding="utf-8"))
        if sr.get("slug") != f.stem: errors.append(f"{f.name}: slug must match the file name")
        if sr.get("slug") in RESERVED or sr.get("slug") in seen: errors.append(f"{f.name}: address already used")
        missing = [r["slug"] for r in sr.get("looks", []) if r["slug"] not in seen]
        if missing: errors.append(f"{f.name}: unknown looks {missing}")
        if not missing and all(r["slug"] in visible for r in sr["looks"]) and (show_drafts or not sr.get("draft")):
            series_list.append(sr)
    if errors:
        sys.exit("Fix these before building:\n  " + "\n  ".join(errors))
    series_list.sort(key=lambda x: x.get("published", ""), reverse=True)
    return site, looks, series_list


def main():
    show_drafts = "--drafts" in sys.argv
    site, looks, series_list = load(show_drafts)
    if OUT.exists():
        shutil.rmtree(OUT)
    d = site["domain"]
    write(OUT / "style.css", CSS)
    if (ROOT / "images" / "looks").exists():
        shutil.copytree(ROOT / "images" / "looks", OUT / "images" / "looks")
    write(OUT / "favicon.svg", FAVICON)
    write(OUT / "CNAME", d)
    write(OUT / "robots.txt", f"User-agent: *\nDisallow: /go/\nSitemap: https://{d}/sitemap.txt\n")
    urls = [f"https://{d}{p}" for p in ("/", "/latest/", "/looks/", "/occasion/", "/style/", "/colors/", "/values/", "/story/")]
    for look in looks:
        slug = look["slug"]
        write(OUT / "look" / slug / "index.html", look_page(look, site))
        write(OUT / slug / "index.html", redirect_page(f"/look/{slug}/"))
        for old in look.get("old_urls", []):
            write(OUT / old.strip("/") / "index.html", redirect_page(f"/look/{slug}/"))
        urls.append(f"https://{d}/look/{slug}/")
        for p in look["pieces"]:
            for key, code, *_ in TIERS:
                v = p.get(key) or {}
                url = None if v.get("sold_out") else with_affiliate(v.get("url"), site)
                write(OUT / "go" / f"{slug}-{p['n']}-{code}" / "index.html", go_page(url, f"/look/{slug}/"))
    for group in ("occasion", "style", "pairing", "season"):
        base = GROUPS[group][0]
        if group != "season":
            write(OUT / base / "index.html", hub_page(looks, site, group))
        for key in used_keys(site, looks, group):
            write(OUT / base / key / "index.html", collection_page(members_of(looks, group, key), site, group, key))
            urls.append(f"https://{d}/{base}/{key}/")
    for old, to in site.get("legacy_redirects", {}).items():
        if not (OUT / old.strip("/") / "index.html").exists():
            write(OUT / old.strip("/") / "index.html", redirect_page(to))
    write(OUT / "index.html", home_page(looks, site))
    by_slug = {l["slug"]: l for l in looks}
    for sr in series_list:
        write(OUT / "series" / sr["slug"] / "index.html", series_page(sr, by_slug, site))
        write(OUT / sr["slug"] / "index.html", redirect_page(f"/series/{sr['slug']}/"))
        urls.append(f"https://{d}/series/{sr['slug']}/")
    write(OUT / "latest" / "index.html", latest_page(looks, site, series_list))
    write(OUT / "looks" / "index.html", all_looks_page(looks, site))
    write(OUT / "story" / "index.html", story_page(site))
    write(OUT / "values" / "index.html", values_page(site))
    write(OUT / "404.html", page("Not found | Purogé",
          '<h1>This page wandered off.</h1><p class="lead">The look may have moved. '
          'Every look we have scouted is on the looks page.</p><a class="btn" href="/looks/">See all looks</a>',
          site, "Page not found", "/404.html"))
    write(OUT / "sitemap.txt", "\n".join(urls) + "\n")
    print(f"Built {len(looks)} look(s) into {OUT}")


if __name__ == "__main__":
    main()
