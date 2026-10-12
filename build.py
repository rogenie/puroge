#!/usr/bin/env python3
"""Build the Puroge site from data/looks.json.

Usage:  python3 build.py            published looks only (what goes live)
        python3 build.py --drafts   also build looks marked "draft": true (local preview)
Output: site/  (GitHub Actions builds and publishes this automatically on every push)

Generates:
  site/index.html             home: story + all published looks, newest first
  site/story/index.html       the story behind the name
  site/look/<id>/index.html   one page per look, Heirloom and Everyday tabs
  site/go/<id>-<n>-h/         redirect to the Heirloom piece n
  site/go/<id>-<n>-e/         redirect to the Everyday piece n
  site/404.html, favicon.svg, style.css, CNAME, robots.txt
Videos and DMs link to /look/<id> or /go/... so a dead product link is fixed
by editing looks.json and pushing, never by re-editing posts.
"""
import html
import json
import shutil
import sys
from pathlib import Path

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
.hero{aspect-ratio:4/5;background:var(--line);border-radius:6px;overflow:hidden;display:grid;place-items:center;color:var(--muted);font-size:14px}
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
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin:24px 0}
.card{text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:6px;overflow:hidden}
.card .hero{border-radius:0}
.card div.t{padding:12px}
.how{display:grid;gap:12px;margin:20px 0;padding:0;list-style:none;counter-reset:s}
.how li{counter-increment:s;display:grid;grid-template-columns:40px 1fr;gap:12px;align-items:baseline}
.how li::before{content:counter(s);font-family:'Cormorant Garamond',Georgia,serif;font-size:28px;color:var(--accent)}
.empty{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:28px 20px;text-align:center;color:var(--muted)}
.empty b{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:26px;line-height:1.2;margin-bottom:8px;color:var(--ink)}
.names{font-family:'Cormorant Garamond',Georgia,serif;font-size:26px;line-height:1.3;margin:28px 0}
.names span{color:var(--accent)}
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
<meta property="og:site_name" content="Puroge"><meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">{img}<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f6f1e8">
{FONTS}<link rel="stylesheet" href="/style.css"></head><body><div class="wrap">
<header><a class="brand" href="/">PUROGE</a><nav><a href="/#looks">Looks</a><a href="/story/">Our story</a></nav></header>
{body}
<footer>{socials and f"<p>{socials}</p>"}<p>{e(site['dedication'])}</p><p>{e(site['disclosure'])}</p></footer>
</div></body></html>"""


def hero(look):
    if look.get("image"):
        return f'<div class="hero"><img src="{e(look["image"])}" alt="{e(look["title"])}" loading="lazy"></div>'
    return '<div class="hero">Look image</div>'


def look_page(look, site):
    lid = look["id"]
    sw = "".join(f'<span style="background:{e(c)}"></span>' for c in look.get("palette", []))
    tabs, panels = [], []
    for i, (key, code, label, sub) in enumerate(TIERS):
        tabs.append(f'<button role="tab" aria-selected="{str(i == 0).lower()}" data-t="{key}">'
                    f'<b>{label}</b><small>{sub}</small></button>')
        rows = []
        for p in look["pieces"]:
            v = p.get(key) or {}
            if v.get("sold_out") or not v.get("url"):
                btn = '<span class="btn off">Sold out</span>'
            else:
                btn = f'<a class="btn" rel="sponsored nofollow" href="/go/{lid}-{p["n"]}-{code}/">Shop</a>'
            rows.append(f"""<div class="piece"><div class="num">{p['n']}</div><div>
<div class="name">{e(p['item'])}</div><div class="sub">{e(v.get('name'))} · {e(v.get('store'))} · {e(v.get('price'))}</div>
<span class="mat">{e(v.get('material'))}</span></div>{btn}</div>""")
        panels.append(f'<div class="panel" data-p="{key}"{"" if i == 0 else " hidden"}>{"".join(rows)}</div>')
    checked = max((v.get("last_checked", "") for p in look["pieces"] for k, *_ in TIERS
                   for v in [p.get(k) or {}]), default="")
    body = f"""<p class="meta" style="margin-top:24px">Look {e(lid)} · {e(look.get('occasion'))}</p>
<h1 style="margin-top:8px">{e(look['title'])}</h1>
{hero(look)}<p class="ai">Image is AI-generated. Every piece listed below is real and was in stock when checked.</p>
<div class="swatches">{sw}</div>
<p class="lesson">{e(look.get('lesson'))}</p>
<div class="tabs" role="tablist">{"".join(tabs)}</div>{"".join(panels)}
<p class="note">Numbers match the video. Prices and stock change; last checked {e(checked)}.</p>
<script>
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{{
 document.querySelectorAll('.tabs button').forEach(x=>x.setAttribute('aria-selected',x===b));
 document.querySelectorAll('.panel').forEach(p=>p.hidden=p.dataset.p!==b.dataset.t);
}});
</script>"""
    return page(f"Look {lid}: {look['title']} | Puroge", body, site, look.get("lesson"),
                f"/look/{lid}/", look.get("image", ""))


def home_page(looks, site):
    cards = "".join(f'<a class="card" href="/look/{l["id"]}/">{hero(l)}'
                    f'<div class="t"><div class="meta">Look {e(l["id"])}</div>{e(l["title"])}</div></a>'
                    for l in looks)
    looks_html = (f'<div class="grid">{cards}</div>' if looks else
                  '<div class="empty"><b>The first looks are being scouted.</b>'
                  'Every piece checked for fabric and fit before it goes up.</div>')
    body = f"""<h1>Elegant, never boring.<br>Every piece found for you.</h1>
<p class="lead">You see an outfit you love, and then the hunting starts. We do the hunting.
Each Puroge look is a complete outfit, numbered piece by piece, with a link to every item.</p>
<a class="btn" href="#looks">See the looks</a>
<h2>How it works</h2>
<ol class="how">
<li><div><b>Find a look you love</b> in our videos. Every piece in it is numbered.</div></li>
<li><div><b>Open the look here.</b> The numbers match, so you know exactly what is what.</div></li>
<li><div><b>Pick your version.</b> Heirloom is made to last a lifetime. Everyday is the same look at a gentler price.</div></li>
</ol>
<p>Every piece lists its fabric. We favor wool, linen, cotton, silk and leather, because a seamstress
judges clothes from the inside out.</p>
<h2 id="looks">The looks</h2>
{looks_html}"""
    return page("Puroge | Elegant, never boring", body, site,
                "Complete elegant outfits, every piece found and linked for you, in two price versions.")


def story_page(site):
    body = """<p class="meta" style="margin-top:24px">Our story</p>
<h1 style="margin-top:8px">Named for two women who sewed.</h1>
<p class="lead">My grandmothers, Lola Purisima and Lola Roberta, sewed and sold clothes for a living.</p>
<p class="names"><span>Pu</span>risima · <span>Ro</span>berta · Ro<span>ge</span>nie</p>
<p>Puroge carries all three of us: the first sound of each Lola's name, and mine.</p>
<p>The brand works the way a good shopkeeper does. Instead of leaving you to hunt down an outfit you saw
online, we find every piece for you, check what it is made of, and put it all on one page.
Two versions of each look, so it works for more than one budget.</p>
<p>Lola is Tagalog for grandmother.</p>
<p style="margin-top:28px"><a class="btn" href="/#looks">See the looks</a></p>"""
    return page("Our story | Puroge", body, site,
                "Puroge is named for Lola Purisima and Lola Roberta, who sewed and sold clothes for a living.",
                "/story/")


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


def main():
    show_drafts = "--drafts" in sys.argv
    data = json.loads((ROOT / "data" / "looks.json").read_text(encoding="utf-8"))
    site = data["site"]
    looks = [l for l in data["looks"] if show_drafts or not l.get("draft")]
    looks.sort(key=lambda l: l["id"], reverse=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    write(OUT / "style.css", CSS)
    write(OUT / "favicon.svg", FAVICON)
    write(OUT / "CNAME", site["domain"])
    write(OUT / "robots.txt", f"User-agent: *\nDisallow: /go/\nSitemap: https://{site['domain']}/sitemap.txt\n")
    urls = [f"https://{site['domain']}/", f"https://{site['domain']}/story/"]
    for look in looks:
        lid = look["id"]
        write(OUT / "look" / lid / "index.html", look_page(look, site))
        urls.append(f"https://{site['domain']}/look/{lid}/")
        for p in look["pieces"]:
            for key, code, *_ in TIERS:
                v = p.get(key) or {}
                url = None if v.get("sold_out") else v.get("url")
                write(OUT / "go" / f"{lid}-{p['n']}-{code}" / "index.html", go_page(url, f"/look/{lid}/"))
    write(OUT / "index.html", home_page(looks, site))
    write(OUT / "story" / "index.html", story_page(site))
    write(OUT / "404.html", page("Not found | Puroge",
          '<h1>This page wandered off.</h1><p class="lead">The look may have moved. '
          'Everything we have scouted is on the home page.</p><a class="btn" href="/#looks">See the looks</a>',
          site, "Page not found", "/404.html"))
    write(OUT / "sitemap.txt", "\n".join(urls) + "\n")
    drafts = len(data["looks"]) - len([l for l in data["looks"] if not l.get("draft")])
    print(f"Built {len(looks)} look(s) into {OUT}" + (f" ({drafts} draft(s) hidden)" if drafts and not show_drafts else ""))


if __name__ == "__main__":
    main()
