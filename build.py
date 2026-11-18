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
  /journal/                   the SEO journal, built from the puroge-site repo by the publish workflow
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
SHOW_DRAFTS = False
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
header{padding:28px 0 8px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.brand{text-decoration:none;display:block;color:var(--ink)}
.brand svg{display:block;height:24px;width:auto}
.tagline{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:15px;color:var(--accent);margin-top:6px;letter-spacing:.01em}
header nav{display:flex;flex-wrap:wrap;justify-content:flex-end}
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

/* Home intro: the swing tag */
.intro{display:grid;grid-template-columns:1fr 300px;gap:36px;align-items:center;margin:28px 0 8px}
.intro h1{font-size:clamp(46px,8.4vw,68px);line-height:.98;margin:0 0 18px;letter-spacing:-.01em}
.intro .kicker{font-size:11px;font-weight:600;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);margin:0 0 18px}
.intro .lead{margin:0 0 26px;max-width:30em}
.intro .row{display:flex;gap:10px;flex-wrap:wrap}
.stage{position:relative;height:400px;border-radius:6px;overflow:hidden;
  background:
    repeating-linear-gradient(0deg,rgba(120,98,70,.05) 0 1px,transparent 1px 3px),
    repeating-linear-gradient(90deg,rgba(120,98,70,.045) 0 1px,transparent 1px 4px),
    linear-gradient(160deg,#efe6d6,#e6dac6);
  box-shadow:inset 0 0 0 1px rgba(120,98,70,.12)}
.stage .light{position:absolute;inset:-40%;background:radial-gradient(closest-side,rgba(255,250,236,.85),rgba(255,250,236,0) 70%);
  animation:light 14s ease-in-out infinite alternate}
.stage .shade{position:absolute;inset:0;background:repeating-linear-gradient(105deg,transparent 0 46px,rgba(90,70,50,.05) 46px 58px);
  animation:shade 14s ease-in-out infinite alternate}
.swing{position:absolute;left:50%;top:0;width:200px;margin-left:-100px;transform-origin:50% 0;animation:sway 7s ease-in-out infinite alternate}
.string{width:1px;height:78px;margin:0 auto;background:linear-gradient(#b5a184,#9d8768)}
.tag{position:relative;width:200px;height:268px;margin-top:-6px;padding:44px 22px 20px;color:#2a2420;text-align:center;
  background:linear-gradient(175deg,#fdfaf3,#f4ecdd);
  clip-path:polygon(18% 0,82% 0,100% 12%,100% 100%,0 100%,0 12%);
  filter:drop-shadow(0 14px 18px rgba(60,40,20,.16));animation:flutter 7s ease-in-out infinite alternate}
.eyelet{position:absolute;top:13px;left:50%;width:14px;height:14px;margin-left:-7px;border-radius:50%;
  border:2px solid #b08d57;background:#e6dac6;box-shadow:inset 0 1px 2px rgba(0,0,0,.2)}
.tag-brand{display:block;font:600 10px/1 Inter,sans-serif;letter-spacing:.42em;margin-left:.42em}
.tag-rule{display:block;width:28px;height:1px;background:#b08d57;margin:14px auto 0}
.fiber{position:relative;height:120px;margin-top:18px}
.f{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center}
.f b{font:500 28px/1.05 'Cormorant Garamond',Georgia,serif;letter-spacing:-.005em;white-space:nowrap}
.f i{font:400 12px/1.4 Inter,sans-serif;font-style:normal;color:#7a6e63;margin-top:10px;letter-spacing:.02em}
.f-poly{animation:poly 12s ease-in-out infinite}
.f-linen{opacity:0;animation:linen 12s ease-in-out infinite}
.f b{position:relative}
.strike{position:absolute;left:-6px;right:-6px;top:54%;height:1.5px;background:#6b2a26;transform:scaleX(0);transform-origin:left;
  animation:strike 12s cubic-bezier(.6,0,.2,1) infinite}
.tag-foot{position:absolute;left:0;right:0;bottom:20px;font:italic 400 15px/1.3 'Cormorant Garamond',Georgia,serif;color:#6b2a26}
@keyframes sway{from{transform:rotate(-2.6deg)}to{transform:rotate(2.6deg)}}
@keyframes flutter{from{transform:perspective(600px) rotateY(-7deg)}to{transform:perspective(600px) rotateY(7deg)}}
@keyframes light{from{transform:translate(-18%,-14%)}to{transform:translate(16%,12%)}}
@keyframes shade{from{transform:translateX(-30px)}to{transform:translateX(30px)}}
@keyframes poly{0%,30%{opacity:1;filter:blur(0)}42%,92%{opacity:0;filter:blur(3px)}100%{opacity:1;filter:blur(0)}}
@keyframes strike{0%,14%{transform:scaleX(0)}26%,92%{transform:scaleX(1)}96%,100%{transform:scaleX(0)}}
@keyframes linen{0%,36%{opacity:0;transform:translateY(6px)}48%,88%{opacity:1;transform:none}96%,100%{opacity:0}}
@media (prefers-color-scheme:dark){.stage{background:
    repeating-linear-gradient(0deg,rgba(255,240,210,.035) 0 1px,transparent 1px 3px),
    repeating-linear-gradient(90deg,rgba(255,240,210,.03) 0 1px,transparent 1px 4px),
    linear-gradient(160deg,#2c2621,#221d19)}
  .stage .light{background:radial-gradient(closest-side,rgba(255,226,180,.18),rgba(255,226,180,0) 70%)}}
@media (max-width:640px){.intro{grid-template-columns:1fr;gap:24px}.stage{height:360px;order:-1}}
@media (prefers-reduced-motion:reduce){.stage *{animation:none!important}.f-poly{opacity:0}.f-linen{opacity:1}}
.door .chips{margin:10px 0 0}
.door .chips i{font-style:normal;font-size:13px;border:1px solid var(--line);border-radius:99px;padding:2px 10px;color:var(--ink)}
.hub{list-style:none;padding:0;margin:20px 0;display:grid;gap:8px}
.hub a{display:flex;justify-content:space-between;text-decoration:none;border-bottom:1px solid var(--line);padding:12px 0;font-size:17px}
.hub a span{color:var(--muted);font-size:14px}
footer{border-top:1px solid var(--line);margin-top:56px;padding:20px 0 40px;color:var(--muted);font-size:13px}
footer a{margin-right:14px}
.story p{font-size:17px;line-height:1.75}
.story h2{margin-top:44px}
.story p.names{font-size:32px;line-height:1.3;margin:20px 0 24px}
.story-quote{margin:40px 0;padding:0 0 0 20px;border-left:2px solid var(--accent);font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:28px;line-height:1.3;color:var(--accent)}
/* The Purogé Label pre-order */
.label-sec{margin:56px 0 8px;padding:40px 0 8px;border-top:1px solid var(--line)}
.label-sec .kicker{font-size:11px;font-weight:600;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);margin:0 0 14px}
.label-sec h2{font-size:clamp(34px,6vw,46px);margin:0 0 12px;line-height:1.05}
.lp-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:26px 0 20px}
.lp{position:relative;display:flex;flex-direction:column;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:0 0 16px;cursor:pointer;overflow:hidden;transition:border-color .2s}
.lp input{position:absolute;opacity:0;pointer-events:none}
.lp:hover{border-color:var(--muted)}
.lp:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.sw{display:block;height:120px;margin-bottom:10px;background:
  repeating-linear-gradient(0deg,rgba(255,255,255,.18) 0 1px,transparent 1px 3px),
  repeating-linear-gradient(90deg,rgba(0,0,0,.05) 0 1px,transparent 1px 4px),var(--c)}
.sw-oat{--c:#d9cbb3}.sw-ivory{--c:#eee5d4}.sw-clay{--c:#c7a48b}.sw-sage{--c:#b5baa0}
.lp-name,.lp-line,.lp-price,.lp-pick{padding:0 16px}
.lp-name{font-family:'Cormorant Garamond',Georgia,serif;font-size:24px;line-height:1.15}
.lp-line{font-size:14px;color:var(--muted);line-height:1.5}
.lp-price{font-size:14px;font-weight:600;margin-top:4px}.lp-price.soon{font-weight:400;font-style:italic;color:var(--muted)}
.lp-pick{align-self:flex-start;margin:10px 16px 0!important;padding:10px 18px!important;border:1.5px solid var(--accent);border-radius:99px;font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);background:transparent;transition:background .25s,color .25s,transform .25s}
.lp:hover .lp-pick{background:var(--accent);color:#fbf6ee;transform:translateY(-1px)}
.lp:has(input:checked) .lp-pick{background:var(--accent);color:#fbf6ee}
.pk-on{display:none}.lp:has(input:checked) .pk-on{display:inline}.lp:has(input:checked) .pk-off{display:none}
.lf-fields{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.lf-fields input{font:inherit;font-size:15px;padding:12px 14px;border:1px solid var(--line);border-radius:99px;background:var(--card);color:var(--ink)}
.lf-fields input[name=notes]{grid-column:1/-1}
.lf-fields .btn{grid-column:1/-1;border:0;cursor:pointer;font:inherit;font-size:15px;padding:13px 18px}
.hp{position:absolute;left:-9999px}
.lf-msg{min-height:1.4em;margin:12px 0 0;color:var(--accent);font-weight:600}
.label-form.done .lf-fields,.label-form.done .lp-grid{opacity:.5;pointer-events:none}
@media (max-width:640px){.lp-grid{grid-template-columns:1fr 1fr;gap:10px}.sw{height:84px}.lp-name{font-size:20px}.lf-fields{grid-template-columns:1fr}}
.lf-cue{display:flex;flex-direction:column;align-items:center;gap:6px;margin:30px 0 18px;text-align:center;font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:24px;color:var(--ink)}
.lf-arrow{font-family:Inter,sans-serif;font-style:normal;font-size:30px;line-height:1;color:var(--accent);animation:cue 1.6s ease-in-out infinite}
.label-form.picked .lf-cue{color:var(--accent)}
.label-form.picked .lf-fields{box-shadow:0 0 0 2px var(--accent);border-radius:34px;padding:8px;background:var(--card)}
@keyframes cue{0%,100%{transform:translateY(0)}50%{transform:translateY(8px)}}
@media (prefers-reduced-motion:reduce){.lf-arrow{animation:none}}
.site-head .brand{display:flex;align-items:center;gap:14px}
.site-head .brand .emb svg{width:52px;height:52px;display:block;filter:drop-shadow(0 3px 6px rgba(107,42,38,.25))}
.site-head .wm{display:flex;flex-direction:column}
.site-head .brand .wm svg{height:30px;width:auto}
.site-head .tagline{font-size:15px;margin-top:7px}
.h-brand{display:flex;align-items:center;gap:18px;margin:0 0 34px}
.h-emb svg{width:78px;height:78px;display:block;filter:drop-shadow(0 6px 14px rgba(107,42,38,.28))}
.h-wm svg{height:40px;width:auto;display:block}
.h-wm{color:var(--ink)}
@media (max-width:900px){.site-head .brand .emb svg{width:40px;height:40px}.site-head nav{gap:10px}.site-head nav a{font-size:10.5px;letter-spacing:.07em}.site-head .brand{gap:10px}}
@media (max-width:430px){.site-head nav a[href='/story/'],.site-head .nav-the{display:none}.site-head .brand .wm svg{height:17px}.h-brand{display:none}}
.fbar{position:relative;display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:18px 0 6px}
.fbar-l{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-right:4px}
.dd{position:relative}
.dd summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--card);border-radius:99px;padding:8px 14px;font-size:14px;color:var(--ink);user-select:none}
.dd summary::-webkit-details-marker{display:none}
.dd-car{width:7px;height:7px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(45deg) translateY(-2px);margin-left:2px;transition:transform .2s}
.dd[open] .dd-car{transform:rotate(-135deg) translate(-2px,0)}
.dd.on summary,.dd[open] summary{border-color:var(--ink)}
.dd.on summary{background:var(--ink);color:var(--bg)}
.dd-panel{position:absolute;z-index:15;top:calc(100% + 8px);left:0;width:max-content;max-width:min(360px,86vw);background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;box-shadow:0 14px 34px rgba(30,20,10,.16)}
.dd-panel .chips{margin:0}
.fclear{border:0;background:none;color:var(--accent);font:inherit;font-size:13px;text-decoration:underline;text-underline-offset:3px;cursor:pointer;padding:6px}
@media (max-width:640px){.fbar{gap:6px}.fbar-l{width:100%}.dd{position:static}.dd summary{padding:7px 10px;font-size:13px;gap:4px}.dd-panel{left:0;right:0;width:auto;max-width:none;top:calc(100% + 6px)}}
footer a.ded{font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:18px;color:var(--accent);text-decoration:none;border-bottom:1px solid var(--line)}
footer a.ded:hover{border-color:var(--accent)}
/* ===== Redesign: site frame ===== */
body{font-size:16px}
.site-head{display:block;padding:0;position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:saturate(1.3) blur(10px);border-bottom:1px solid color-mix(in srgb,var(--line) 70%,transparent)}
.head-in{max-width:1240px;margin:0 auto;padding:16px 28px;display:flex;align-items:center;justify-content:space-between;gap:20px}
.site-head .brand svg{height:22px}
.site-head .tagline{font-size:13px;margin-top:5px}
.site-head nav{display:flex;gap:28px}
.site-head nav a{white-space:nowrap;margin:0;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink);text-decoration:none;position:relative}
.site-head nav a::after{content:"";position:absolute;left:0;right:0;bottom:-5px;height:1px;background:var(--accent);transform:scaleX(0);transform-origin:left;transition:transform .35s ease}
.site-head nav a:hover::after{transform:scaleX(1)}
main .wrap{padding-top:8px}
.site-foot{--accent:#d39a8e;margin-top:96px;background:#221d19;color:#d9cfc1;text-align:center;padding:72px 24px 56px}
.foot-in{max-width:760px;margin:0 auto}
.foot-brand{color:#f6f1e8}.foot-brand svg{height:30px;width:auto}
.site-foot .tagline{color:#d39a8e;font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:19px;margin:10px 0 26px}
.site-foot a{color:#efe6d8}
.site-foot a.ded{color:#f6f1e8;font-size:22px;border-bottom-color:#5a4e44}
.foot-nav{display:flex;flex-wrap:wrap;justify-content:center;gap:22px;margin:28px 0;font-size:12px;letter-spacing:.16em;text-transform:uppercase}
.foot-nav a{text-decoration:none;margin:0}
.site-foot .fine{font-size:12px;color:#9c8f80;margin:8px 0}
.btn{transition:background .25s,color .25s,transform .25s}
.btn:hover{transform:translateY(-1px)}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--ink)}
.btn.ghost:hover{background:var(--ink);color:var(--bg)}
.btn.light{background:#f6f1e8;color:#221d19}
.kicker{font-size:11px;font-weight:600;letter-spacing:.24em;text-transform:uppercase;color:var(--accent);margin:0 0 16px}
.reveal{opacity:0;transform:translateY(28px);transition:opacity 1s ease,transform 1s cubic-bezier(.2,.7,.2,1)}
.reveal.in{opacity:1;transform:none}

/* ===== Home ===== */
.home h1,.home h2{font-family:'Cormorant Garamond',Georgia,serif;font-weight:400}
.h-hero{display:grid;grid-template-columns:1.05fr 1fr;min-height:calc(100vh - 74px);max-height:920px}
.h-copy{display:flex;flex-direction:column;justify-content:center;padding:64px 6vw 64px max(28px,calc((100vw - 1240px)/2 + 28px))}
.h-copy h1{font-size:clamp(54px,7.6vw,112px);line-height:.92;letter-spacing:-.02em;margin:0 0 28px}
.h-copy h1 em{font-style:italic;color:var(--accent)}
.h-copy .lead{font-size:19px;line-height:1.65;max-width:30em;margin:0 0 34px;color:var(--ink)}
.h-copy .row{display:flex;gap:12px;flex-wrap:wrap}
.h-copy .btn{padding:15px 28px;font-size:13px;letter-spacing:.12em;text-transform:uppercase}
.h-note{margin:40px 0 0;font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted)}
.h-room{position:relative;overflow:hidden;background:#e9dfcf}
.room-img{position:absolute;inset:0;background:url(/images/set/del-mar-living.jpg) center 60%/cover;animation:kb 28s ease-in-out infinite alternate}
.room-light{position:absolute;inset:-30%;background:radial-gradient(closest-side,rgba(255,246,226,.55),rgba(255,246,226,0) 70%);mix-blend-mode:soft-light;animation:light 16s ease-in-out infinite alternate}
.h-room .swing{left:58%;width:210px;margin-left:-105px}
.h-room .string{height:24vh;background:linear-gradient(#cbb89a,#9d8768)}
.h-room .tag{filter:drop-shadow(0 22px 26px rgba(40,25,10,.28))}
@keyframes kb{from{transform:scale(1.02)}to{transform:scale(1.12) translate(-1.5%,-1%)}}

.ribbon{overflow:hidden;background:#221d19;color:#f1e8da;padding:18px 0;border-top:1px solid #3a322b}
.ribbon-track{display:flex;gap:34px;width:max-content;animation:ribbon 48s linear infinite;font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:24px;white-space:nowrap}
.ribbon i{color:#d39a8e;font-style:normal}
@keyframes ribbon{to{transform:translateX(-50%)}}

.edit,.journal-tease,.pillars,.wide-wrap{max-width:1240px;margin:0 auto;padding:0 28px}
.edit{padding-top:110px}
.sec-head{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:36px}
.sec-head h2{font-size:clamp(36px,4.6vw,60px);line-height:1.02;margin:0;max-width:16ch}
.more{font-size:12px;letter-spacing:.16em;text-transform:uppercase;text-decoration:none;white-space:nowrap;border-bottom:1px solid var(--line);padding-bottom:4px}
.more:hover{border-color:var(--accent);color:var(--accent)}
.rail{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(260px,24%);gap:22px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:18px;scrollbar-width:thin}
.slide{scroll-snap-align:start;text-decoration:none;color:var(--ink)}
.slide .ph{position:relative;aspect-ratio:3/4;overflow:hidden;background:var(--line)}
.slide img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform 1.4s cubic-bezier(.2,.7,.2,1),opacity .7s ease}
.slide .ev{opacity:0}
.slide:hover img{transform:scale(1.04)}
.slide:hover .ev,.slide:focus .ev{opacity:1}
.tier-chip{position:absolute;left:12px;bottom:12px;display:flex;gap:2px;background:rgba(251,247,240,.92);border-radius:99px;padding:3px;font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.tier-chip b,.tier-chip i{font-style:normal;font-weight:500;padding:5px 10px;border-radius:99px;color:#2a2420;transition:background .5s,color .5s}
.tier-chip b{background:#2a2420;color:#f6f1e8}
.slide:hover .tier-chip b{background:transparent;color:#2a2420}
.slide:hover .tier-chip i{background:#2a2420;color:#f6f1e8}
.cap{display:flex;flex-direction:column;gap:4px;padding:16px 2px 0}
.cap-k{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
.cap-t{font-family:'Cormorant Garamond',Georgia,serif;font-size:27px;line-height:1.1}
.cap-l{font-size:14px;line-height:1.55;color:var(--muted)}
.rail-hint{font-size:12px;color:var(--muted);margin:8px 0 0}

.tiers{max-width:1240px;margin:120px auto 0;padding:0 28px;display:grid;grid-template-columns:1fr 1.05fr 1fr;gap:28px;align-items:center}
.tier{position:relative;aspect-ratio:3/4;overflow:hidden}
.tier img{width:100%;height:100%;object-fit:cover}
.tier-t{position:absolute;left:0;right:0;bottom:0;padding:60px 20px 20px;color:#fbf6ee;background:linear-gradient(transparent,rgba(25,18,12,.72))}
.tier-t span{display:block;font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:#f0c9bf}
.tier-t b{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-weight:400;font-size:28px;line-height:1.1;margin:6px 0 4px}
.tier-t i{font-style:normal;font-size:13px;opacity:.85}
.tier-mid{text-align:center;padding:0 8px}
.tier-mid h2{font-size:clamp(40px,4.4vw,58px);line-height:1;margin:0 0 18px}
.tier-mid p{color:var(--muted);margin:0 0 26px}

.wide-wrap .label-sec{margin-top:120px;border-top:0;padding-top:0}
.wide-wrap .label-sec h2{font-size:clamp(40px,5vw,64px)}
.wide-wrap .lp-grid{grid-template-columns:repeat(4,1fr);gap:18px}
.wide-wrap .sw{height:220px;transition:transform 1.2s cubic-bezier(.2,.7,.2,1)}
.wide-wrap .lp:hover .sw{transform:scale(1.04)}
.wide-wrap .lp{border-radius:0}
.sw.lp-ph{position:relative;overflow:hidden;background:#e9dfcf;height:auto!important;aspect-ratio:4/5}
.lp-ph img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform 1.2s cubic-bezier(.2,.7,.2,1)}
.lp:hover .lp-ph img{transform:scale(1.05)}
.wide-wrap .lp:hover .sw.lp-ph{transform:none}
.wide-wrap .lf-fields{grid-template-columns:1fr 1fr 1fr auto;max-width:none}
.wide-wrap .lf-fields input[name=notes]{grid-column:auto}
.wide-wrap .lf-fields .btn{grid-column:auto;padding:12px 26px}

.story-tease{margin:130px 0 0;background:#221d19;color:#efe6d8;text-align:center;padding:110px 28px}
.story-tease .kicker{color:#d39a8e}
.story-tease p.big-names{max-width:none;display:flex;justify-content:center;flex-wrap:wrap;gap:6px 22px;font-family:'Cormorant Garamond',Georgia,serif;font-size:clamp(34px,6vw,84px);line-height:1;margin:10px 0 34px;color:#7d7064}
.big-names b{font-weight:500;color:#7d7064;transition:color 1.2s ease}
.big-names .dot{color:#5a4e44}
.story-tease.in .big-names b{color:#f6f1e8}
.story-tease.in .nm:nth-child(3) b{transition-delay:.5s}.story-tease.in .nm:nth-child(5) b{transition-delay:1s}
.story-tease h2{font-size:clamp(30px,3.6vw,46px);margin:0 0 16px;color:#f6f1e8}
.story-tease p{max-width:34em;margin:0 auto 30px;color:#c9bdae;font-size:17px}

.journal-tease{padding-top:110px}
.jt-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.jt{display:flex;flex-direction:column;gap:10px;min-height:230px;padding:30px 28px;background:var(--card);border:1px solid var(--line);text-decoration:none;transition:border-color .3s,transform .4s}
.jt:hover{border-color:var(--ink);transform:translateY(-3px)}
.jt-k{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent)}
.jt-t{font-family:'Cormorant Garamond',Georgia,serif;font-size:28px;line-height:1.12}
.jt-d{font-size:14px;color:var(--muted);line-height:1.55;margin-top:auto}

.pillars{display:grid;grid-template-columns:repeat(4,1fr);gap:28px;padding-top:110px}
.pillars span{font-family:'Cormorant Garamond',Georgia,serif;font-size:40px;color:var(--accent)}
.pillars b{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:24px;margin:6px 0 6px}
.pillars p{margin:0;font-size:14.5px;color:var(--muted);line-height:1.6}

@media (max-width:900px){
 .h-hero{grid-template-columns:1fr;min-height:0;max-height:none}
 .h-room{height:62vh;order:-1}
 .h-copy{padding:44px 22px 20px}
 .rail{grid-auto-columns:72%}
 .tiers{grid-template-columns:1fr 1fr}.tier-mid{grid-column:1/-1;order:-1;padding:0}
 .wide-wrap .lp-grid{grid-template-columns:1fr 1fr}
 .wide-wrap .sw{height:130px}
 .wide-wrap .lf-fields{grid-template-columns:1fr}
 .jt-grid,.pillars{grid-template-columns:1fr}
 .sec-head{flex-direction:column;align-items:flex-start}
 .site-head nav{gap:16px}.head-in{padding:12px 20px}
 .site-head .tagline{display:none}
}
@media (max-width:640px){.site-head nav{flex-wrap:nowrap}header{flex-direction:row}}
@media (prefers-reduced-motion:reduce){.reveal{opacity:1;transform:none;transition:none}.ribbon-track,.room-img,.room-light{animation:none}}
"""

import hashlib
CSS_VERSION = hashlib.sha1(CSS.encode()).hexdigest()[:10]

FAVICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="Purogé emblem">\n<circle cx="50" cy="50" r="49" fill="#6b2a26"/>\n<circle cx="50" cy="50" r="42" fill="none" stroke="#f6f1e8" stroke-width="1" stroke-dasharray="3.2 2.4" opacity=".75"/>\n<g fill="#f6f1e8" transform="translate(30.04 74.00) scale(0.0732 -0.0732)"><path d="M208 85Q208 55 215.0 39.5Q222 24 244.5 18.0Q267 12 312 12Q315 12 315.0 6.0Q315 0 312 0Q280 0 242.5 1.0Q205 2 161 2Q126 2 94.0 1.0Q62 0 37 0Q34 0 34.0 6.0Q34 12 37 12Q70 12 86.0 17.0Q102 22 107.5 37.0Q113 52 113 81V544Q113 573 107.5 587.5Q102 602 86.0 607.5Q70 613 37 613Q34 613 34.0 619.0Q34 625 37 625Q62 625 93.5 623.5Q125 622 160 622Q184 622 222.5 625.0Q261 628 297 628Q358 628 405.5 611.5Q453 595 481.0 559.0Q509 523 511 464Q512 412 493.0 374.0Q474 336 441.5 311.5Q409 287 370.0 274.5Q331 262 292 262Q281 262 268.5 263.0Q256 264 244 267Q241 268 242 275Q243 279 245 280Q246 280 247 280Q255 278 265.0 277.0Q275 276 282 276Q315 276 343.0 294.0Q371 312 388.5 349.0Q406 386 406 442Q406 495 389.0 532.0Q372 569 341.5 588.5Q311 608 267 608Q244 608 231.0 603.5Q218 599 213.0 585.0Q208 571 208 542Z"/></g>\n</svg>'

EMBLEM = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" aria-hidden="true" focusable="false">\n<circle cx="50" cy="50" r="49" fill="#6b2a26"/>\n<circle cx="50" cy="50" r="42" fill="none" stroke="#f6f1e8" stroke-width="1" stroke-dasharray="3.2 2.4" opacity=".75"/>\n<g fill="#f6f1e8" transform="translate(30.04 74.00) scale(0.0732 -0.0732)"><path d="M208 85Q208 55 215.0 39.5Q222 24 244.5 18.0Q267 12 312 12Q315 12 315.0 6.0Q315 0 312 0Q280 0 242.5 1.0Q205 2 161 2Q126 2 94.0 1.0Q62 0 37 0Q34 0 34.0 6.0Q34 12 37 12Q70 12 86.0 17.0Q102 22 107.5 37.0Q113 52 113 81V544Q113 573 107.5 587.5Q102 602 86.0 607.5Q70 613 37 613Q34 613 34.0 619.0Q34 625 37 625Q62 625 93.5 623.5Q125 622 160 622Q184 622 222.5 625.0Q261 628 297 628Q358 628 405.5 611.5Q453 595 481.0 559.0Q509 523 511 464Q512 412 493.0 374.0Q474 336 441.5 311.5Q409 287 370.0 274.5Q331 262 292 262Q281 262 268.5 263.0Q256 264 244 267Q241 268 242 275Q243 279 245 280Q246 280 247 280Q255 278 265.0 277.0Q275 276 282 276Q315 276 343.0 294.0Q371 312 388.5 349.0Q406 386 406 442Q406 495 389.0 532.0Q372 569 341.5 588.5Q311 608 267 608Q244 608 231.0 603.5Q218 599 213.0 585.0Q208 571 208 542Z"/></g>\n</svg>'

LOGO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 4974 865" aria-hidden="true" focusable="false"><g fill="currentColor" transform="translate(0 815) scale(1 -1)"><path transform="translate(0 0)" d="M200 85Q200 55 207.5 39.5Q215 24 239.0 18.0Q263 12 311 12Q314 12 314.0 6.0Q314 0 311 0Q279 0 241.5 1.0Q204 2 160 2Q127 2 95.5 1.0Q64 0 39 0Q37 0 37.0 6.0Q37 12 39 12Q74 12 91.5 17.0Q109 22 114.5 37.0Q120 52 120 81V544Q120 573 114.5 587.5Q109 602 91.5 607.5Q74 613 39 613Q37 613 37.0 619.0Q37 625 39 625Q64 625 95.0 623.5Q126 622 159 622Q185 622 222.5 625.0Q260 628 298 628Q356 628 402.5 611.0Q449 594 477.0 558.0Q505 522 506 464Q506 412 487.0 374.0Q468 336 435.5 311.0Q403 286 363.5 274.0Q324 262 286 262Q274 262 261.5 263.0Q249 264 238 267Q234 268 236 275Q237 280 239 280Q239 280 240 280Q249 278 258.5 277.0Q268 276 275 276Q313 276 345.0 294.0Q377 312 397.0 349.5Q417 387 417 443Q417 497 398.5 534.0Q380 571 347.0 591.0Q314 611 271 611Q243 611 227.5 607.0Q212 603 206.0 588.0Q200 573 200 542Z"/><path transform="translate(746 0)" d="M572 510Q572 560 549.5 586.5Q527 613 483 613Q480 613 480.0 619.0Q480 625 483 625Q506 625 531.0 623.5Q556 622 585 622Q610 622 634.5 623.5Q659 625 680 625Q682 625 682.0 619.0Q682 613 680 613Q640 613 619.5 586.5Q599 560 599 510V227Q599 152 569.0 98.0Q539 44 485.0 15.5Q431 -13 359 -13Q285 -13 229.0 15.5Q173 44 142.0 97.0Q111 150 111 223V544Q111 573 105.0 587.5Q99 602 81.5 607.5Q64 613 30 613Q27 613 27.0 619.0Q27 625 30 625Q55 625 85.0 623.5Q115 622 150 622Q186 622 216.5 623.5Q247 625 270 625Q273 625 273.0 619.0Q273 613 270 613Q236 613 218.5 607.0Q201 601 195.5 586.0Q190 571 190 542V258Q190 138 242.0 78.5Q294 19 386 19Q474 19 523.0 73.5Q572 128 572 226Z"/><path transform="translate(1646 0)" d="M546 0Q530 0 493.5 38.5Q457 77 406 149Q358 216 298 308Q276 304 253 304Q241 304 228.0 304.5Q215 305 204 306V81Q204 52 209.5 37.0Q215 22 232.5 17.0Q250 12 285 12Q288 12 288.0 6.0Q288 0 285 0Q260 0 230.0 1.0Q200 2 164 2Q130 2 99.0 1.0Q68 0 43 0Q40 0 40.0 6.0Q40 12 43 12Q77 12 94.5 17.0Q112 22 118.5 37.0Q125 52 125 81V544Q125 573 119.0 587.5Q113 602 96.0 607.5Q79 613 44 613Q42 613 42.0 619.0Q42 625 44 625Q69 625 99.5 623.5Q130 622 164 622Q196 622 236.0 625.0Q276 628 306 628Q390 628 434.5 592.5Q479 557 479 498Q479 442 447 398Q416 355 365 330Q444 216 501 147Q559 75 604.0 43.5Q649 12 690 12Q693 12 693.0 6.0Q693 0 690 0ZM397 466Q397 522 382.0 553.5Q367 585 339.5 598.0Q312 611 275 611Q237 611 220.5 597.5Q204 584 204 542V331Q218 330 234.5 329.0Q251 328 263 328Q337 328 367.0 362.0Q397 396 397 466Z"/><path transform="translate(2527 0)" d="M366 -12Q294 -12 235.5 13.5Q177 39 135.5 84.0Q94 129 71.5 187.5Q49 246 49 312Q49 393 80.5 454.0Q112 515 164.0 555.5Q216 596 278.0 616.0Q340 636 401 636Q475 636 533.5 609.5Q592 583 633.0 538.0Q674 493 695.5 436.0Q717 379 717 319Q717 249 689.0 189.0Q661 129 612.5 84.0Q564 39 500.5 13.5Q437 -12 366 -12ZM401 10Q464 10 515.5 42.5Q567 75 596.5 137.5Q626 200 626 291Q626 384 593.5 456.5Q561 529 501.5 570.5Q442 612 360 612Q255 612 197.5 541.0Q140 470 140 347Q140 276 158.5 214.5Q177 153 212.0 107.0Q247 61 295.0 35.5Q343 10 401 10Z"/><path transform="translate(3493 0)" d="M412 -12Q326 -12 258.5 13.5Q191 39 144.5 84.0Q98 129 73.5 188.0Q49 247 49 313Q49 388 77.5 447.0Q106 506 158.0 548.5Q210 591 279.0 613.5Q348 636 429 636Q481 636 527.5 627.0Q574 618 605 601Q614 597 615.0 594.0Q616 591 617 578L630 454Q630 451 625.0 450.0Q620 449 618 453Q608 484 591.0 513.5Q574 543 548.0 566.5Q522 590 486.5 604.0Q451 618 404 618Q330 618 270.0 583.5Q210 549 175.0 484.5Q140 420 140 330Q140 266 159.5 207.0Q179 148 217.0 102.0Q255 56 310.5 29.5Q366 3 438 3Q483 3 509.5 14.5Q536 26 548.0 52.5Q560 79 560 125Q560 173 554.0 195.5Q548 218 525.0 225.0Q502 232 450 232Q444 232 444.0 240.0Q444 248 449 248Q515 244 568.5 243.5Q622 243 680 246Q685 246 685.0 239.0Q685 232 680 232Q659 233 649.0 225.5Q639 218 636.5 193.0Q634 168 634 115Q634 82 636.0 66.0Q638 50 639.5 42.5Q641 35 641 27Q641 21 639.0 19.0Q637 17 630 15Q578 4 520.5 -4.0Q463 -12 412 -12Z"/><path transform="translate(4412 0)" d="M469 0H43Q40 0 40.0 6.0Q40 12 43 12Q77 12 94.5 17.0Q112 22 118.0 37.0Q124 52 124 81V544Q124 573 118.0 587.5Q112 602 94.5 607.5Q77 613 43 613Q40 613 40.0 619.0Q40 625 43 625H451Q461 625 461 616L463 490Q463 487 457.5 486.5Q452 486 451 489Q444 544 412.0 572.5Q380 601 328 601H277Q247 601 231.0 596.0Q215 591 209.0 577.5Q203 564 203 540V337H313Q364 337 388.0 354.5Q412 372 412 409Q412 411 417.5 411.0Q423 411 423 409Q423 378 422.5 361.0Q422 344 422 325Q422 302 423.5 279.0Q425 256 425 230Q425 228 419.0 228.0Q413 228 413 230Q413 273 388.5 293.5Q364 314 310 314H203V85Q203 61 208.5 47.5Q214 34 229.0 28.5Q244 23 271 23H337Q394 23 431.0 56.5Q468 90 482 152Q482 153 482 153Q483 155 488 154Q494 153 494 150Q490 123 487.0 85.0Q484 47 484 15Q484 0 469 0Z"/></g><g transform="translate(0 815)"><path d="M4677 -687 L4739 -783" style="stroke:var(--accent)" stroke-width="38" stroke-linecap="round" fill="none"/></g></svg>'

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&'
         'family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')


def page(title, body, site, desc="", path="/", image="", wide=False):
    url = f"https://{site['domain']}{path}"
    img = f'<meta property="og:image" content="https://{site["domain"]}{e(image)}">' if image else ""
    socials = "".join(f'<a href="{e(s["url"])}" rel="me">{e(s["name"])}</a>' for s in site.get("socials", []))
    main = body if wide else f'<div class="wrap">{body}</div>'
    lab = '<a href="/#label"><span class="nav-the">The </span>Label</a>' if (site.get("label", {}).get("live") or SHOW_DRAFTS) else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:site_name" content="Purogé"><meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">{img}<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f6f1e8">
{FONTS}<link rel="stylesheet" href="/style.css?v={CSS_VERSION}"></head><body class="{'home' if wide else 'page'}">
<header class="site-head"><div class="head-in">
<a class="brand" href="/" aria-label="Purogé home"><span class="emb">{EMBLEM}</span><span class="wm">{LOGO}<span class="tagline">{e(site["tagline"])}</span></span></a>
<nav><a href="/looks/">Looks</a>{lab}<a href="/story/">Story</a><a href="/journal/">Journal</a></nav>
</div></header>
<main>{main}</main>
<footer class="site-foot"><div class="foot-in">
<div class="foot-brand">{LOGO}<p class="tagline">{e(site["tagline"])}</p></div>
<p><a class="ded" href="/story/">{e(site['dedication'])}</a></p>
<p class="foot-nav"><a href="/looks/">Looks</a>{lab}<a href="/story/">Story</a><a href="/values/">Values</a><a href="/journal/">Journal</a></p>
{socials and f"<p>{socials}</p>"}
<p class="fine">{e(site['disclosure'])} {e(site.get('amazon_disclosure'))}</p>
<p class="fine">Made with care in San Diego, California.</p>
</div></footer>
<script>
(function(){{var els=document.querySelectorAll('.reveal');if(!('IntersectionObserver' in window)){{els.forEach(function(x){{x.classList.add('in')}});return}}
var io=new IntersectionObserver(function(es){{es.forEach(function(en){{if(en.isIntersecting){{en.target.classList.add('in');io.unobserve(en.target)}}}})}},{{rootMargin:'0px 0px -10% 0px'}});
els.forEach(function(x){{io.observe(x)}});}})();
</script>
</body></html>"""


def tier_hero(look):
    """Look page hero: one image per tier when the look has them; the tabs swap it."""
    imgs = look.get("images") or {}
    if not imgs.get("heirloom"):
        return hero(look)
    data = " ".join(f'data-{k}="{e(v)}"' for k, v in imgs.items())
    return (f'<div class="hero"><img id="tier-img" src="{e(imgs["heirloom"])}" {data} '
            f'alt="{e(look["title"])}, Heirloom version"></div>')


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
{tier_hero(look)}<p class="ai">Image is AI-generated. Every piece listed below is real and was in stock when checked.</p>
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
 const im=document.getElementById('tier-img');
 if(im&&im.dataset[b.dataset.t]){{im.src=im.dataset[b.dataset.t];im.alt=im.alt.replace(/[A-Z][a-z]+ version$/,b.querySelector('b').textContent+' version');}}
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


def label_section(site):
    lab = site.get("label") or {}
    cards = ""
    for pc in lab.get("pieces", []):
        price = f'<span class="lp-price">{e(pc["price"])}</span>' if pc.get("price") else '<span class="lp-price soon">Price at launch</span>'
        ph = (f'<span class="sw lp-ph"><img src="{e(pc["image"])}" alt="{e(pc["name"])} in linen" loading="lazy"></span>'
              if pc.get("image") else f'<span class="sw sw-{e(pc.get("swatch","oat"))}"></span>')
        cards += (f'<label class="lp"><input type="checkbox" name="pieces" value="{e(pc["name"])}">{ph}'
                  f'<span class="lp-name">{e(pc["name"])}</span><span class="lp-line">{e(pc["line"])}</span>{price}'
                  f'<span class="lp-pick"><span class="pk-off">Reserve this</span><span class="pk-on">✓ Selected</span></span></label>')
    endpoint = lab.get("endpoint", "")
    return f"""<section class="label-sec" id="label">
<p class="kicker">The Purogé Label · Made in San Diego · Pre-order</p>
<h2>Our own label, in linen.</h2>
<p class="lead">Our first collection: four linen pieces, made in San Diego, California, to be worn for years and
handed on. Reserve yours now. Reserving is free; nothing is charged until your pieces are ready.</p>
<form class="label-form" data-endpoint="{e(endpoint)}">
<div class="lp-grid">{cards}</div>
<p class="lf-cue" aria-live="polite"><span class="lf-cue-t">Choose your pieces, then reserve them here</span><span class="lf-arrow" aria-hidden="true">↓</span></p>
<div class="lf-fields">
<input name="name" placeholder="Your name" autocomplete="name" aria-label="Your name">
<input name="email" type="email" required placeholder="Email" autocomplete="email" aria-label="Email">
<input name="notes" placeholder="Sizes or bed size (optional)" aria-label="Sizes or bed size">
<input name="website" tabindex="-1" autocomplete="off" class="hp" aria-hidden="true">
<button class="btn" type="submit">Reserve my pieces</button>
</div>
<p class="lf-msg" role="status"></p>
<p class="note">We will email you before anything ships with final prices, sizes and a date. You can change your mind at any time. Product images are AI-generated previews of the finished pieces.</p>
</form>
<script>
(function(){{var f=document.querySelector('.label-form');if(!f)return;var m=f.querySelector('.lf-msg');
var cue=f.querySelector('.lf-cue-t');f.addEventListener('change',function(ev){{if(ev.target.name!=='pieces')return;
var n=f.querySelectorAll('input[name=pieces]:checked').length;f.classList.toggle('picked',n>0);
cue.textContent=n?(n+(n>1?' pieces':' piece')+' selected. Add your name and email below to reserve.'):'Choose your pieces, then reserve them here';}});
f.addEventListener('submit',function(ev){{ev.preventDefault();
var picks=[].slice.call(f.querySelectorAll('input[name=pieces]:checked')).map(function(i){{return i.value}});
if(!picks.length){{m.textContent='Choose at least one piece to reserve.';return}}
var d=new URLSearchParams();d.append('name',f.name.value);d.append('email',f.email.value);d.append('notes',f.notes.value);
d.append('website',f.website.value);d.append('pieces',picks.join(', '));d.append('page',location.pathname);
var b=f.querySelector('button');b.disabled=true;m.textContent='Reserving…';
fetch(f.dataset.endpoint,{{method:'POST',mode:'no-cors',body:d}}).then(function(){{
f.classList.add('done');m.textContent='Reserved. Thank you, we will be in touch before anything ships.';}})
.catch(function(){{b.disabled=false;m.textContent='Something went wrong. Please try again.';}});}});}})();
</script>
</section>"""


def home_page(looks, site):
    tag = """<div class="swing"><div class="string"></div><div class="tag"><span class="eyelet"></span>
<span class="tag-brand">PUROGÉ</span><span class="tag-rule"></span>
<div class="fiber"><div class="f f-poly"><b>100% Polyester<span class="strike"></span></b><i>Spun from oil</i></div>
<div class="f f-linen"><b>100% Linen</b><i>Grown from flax. Made to last.</i></div></div>
<span class="tag-foot">Wear plants against your skin</span></div></div>"""

    slides = ""
    for l in looks[:8]:
        imgs = l.get("images") or {}
        h = imgs.get("heirloom") or l.get("image")
        ev = imgs.get("everyday")
        if not h:
            continue
        swap = f'<img class="ev" src="{e(ev)}" alt="" loading="lazy">' if ev else ""
        occ = ", ".join(label(site, "occasion", o) for o in l["tags"].get("occasion", [])[:2])
        slides += (f'<a class="slide" href="/look/{l["slug"]}/"><div class="ph">'
                   f'<img class="hl" src="{e(h)}" alt="{e(l["title"])} outfit" loading="lazy">{swap}'
                   f'<span class="tier-chip"><b>Heirloom</b>{"<i>Everyday</i>" if ev else ""}</span></div>'
                   f'<div class="cap"><span class="cap-k">{e(occ)}</span><span class="cap-t">{e(l["title"])}</span>'
                   f'<span class="cap-l">{e((l.get("lesson") or "")[:110])}{"…" if len(l.get("lesson") or "")>110 else ""}</span></div></a>')

    tiers = ""
    for l in looks:
        imgs = l.get("images") or {}
        if imgs.get("heirloom") and imgs.get("everyday"):
            tiers = f"""<section class="tiers reveal">
<div class="tier"><img src="{e(imgs['heirloom'])}" alt="{e(l['title'])}, Heirloom version" loading="lazy">
<div class="tier-t"><span>Heirloom</span><b>Made to last a lifetime.</b><i>The investment version, in the best fabric we could find.</i></div></div>
<div class="tier-mid"><p class="kicker">Every look, two ways</p><h2>Same look.<br>Your budget.</h2>
<p>Every outfit we curate comes in two versions, with each piece numbered and linked. Heirloom for the pieces you
will keep for decades. Everyday for the same look at a gentler price.</p>
<a class="btn" href="/look/{l['slug']}/">See {e(l['title'])}</a></div>
<div class="tier"><img src="{e(imgs['everyday'])}" alt="{e(l['title'])}, Everyday version" loading="lazy">
<div class="tier-t"><span>Everyday</span><b>Same look, gentler price.</b><i>Chosen with the same eye for fabric and fit.</i></div></div>
</section>"""
            break

    label_html = label_section(site) if (site.get("label", {}).get("live") or SHOW_DRAFTS) else ""
    body = f"""<section class="h-hero">
<div class="h-copy">
<div class="h-brand"><span class="h-emb">{EMBLEM}</span><span class="h-wm">{LOGO}</span></div>
<p class="kicker">Check the label</p>
<h1>Wear plants,<br><em>not plastic.</em></h1>
<p class="lead">Most of what’s in a modern closet is spun from oil. We find the linen and natural-fiber pieces worth
keeping, for the office, the airport and every year after.</p>
<div class="row"><a class="btn" href="/looks/">Shop the edit</a>
<a class="btn ghost" href="/journal/why-humans-should-wear-sustainable-clothing/">Why it matters</a></div>
<p class="h-note">Curated in San Diego, California</p>
</div>
<div class="h-room" aria-hidden="true"><div class="room-img"></div><div class="room-light"></div>{tag}</div>
</section>

<div class="ribbon" aria-hidden="true"><div class="ribbon-track">
<span>100% linen</span><i>·</i><span>Made in San Diego</span><i>·</i><span>Worn for years</span><i>·</i><span>Handed on</span><i>·</i><span>Natural fiber, found for you</span><i>·</i>
<span>100% linen</span><i>·</i><span>Made in San Diego</span><i>·</i><span>Worn for years</span><i>·</i><span>Handed on</span><i>·</i><span>Natural fiber, found for you</span><i>·</i>
</div></div>

<section class="edit reveal">
<div class="sec-head"><div><p class="kicker">The edit</p><h2>Complete looks, every piece found for you.</h2></div>
<a class="more" href="/looks/">All {len(looks)} looks →</a></div>
<div class="rail">{slides}</div>
<p class="rail-hint">Hover or tap a look to see its Everyday version.</p>
</section>

{tiers}

<div class="wide-wrap">{label_html}</div>

<section class="story-tease reveal">
<p class="kicker">Our story</p>
<p class="big-names"><span class="nm"><b>Pu</b>risima</span><span class="dot">·</span><span class="nm"><b>Ro</b>berta</span><span class="dot">·</span><span class="nm">Ro<b>ge</b>nie</span></p>
<h2>Three women are hidden in our name.</h2>
<p>One walked miles with second-hand clothes on her head. One sewed sixteen hours a day. The third is building Purogé
in San Diego.</p>
<a class="btn light" href="/story/">Read their story</a>
</section>

<section class="journal-tease reveal">
<div class="sec-head"><div><p class="kicker">The journal</p><h2>The case for natural fiber.</h2></div>
<a class="more" href="/journal/">All articles →</a></div>
<div class="jt-grid" id="jt"><a class="jt" href="/journal/why-humans-should-wear-sustainable-clothing/"><span class="jt-k">The case for natural fiber</span><span class="jt-t">Why Humans Should Wear Sustainable Clothing</span></a></div>
<script>
fetch('/journal/feed.xml').then(function(r){{return r.text()}}).then(function(x){{
var d=new DOMParser().parseFromString(x,'text/xml'),it=[].slice.call(d.querySelectorAll('item')).slice(0,3);if(!it.length)return;
var g=document.getElementById('jt');g.innerHTML='';it.forEach(function(i){{var a=document.createElement('a');a.className='jt';
a.href=i.querySelector('link').textContent.replace('https://puroge.com','');
a.innerHTML='<span class="jt-k">Read · Journal</span><span class="jt-t"></span><span class="jt-d"></span>';
a.querySelector('.jt-t').textContent=i.querySelector('title').textContent;a.querySelector('.jt-d').textContent=i.querySelector('description').textContent;g.appendChild(a);}});}}).catch(function(){{}});
</script>
</section>

<section class="pillars reveal">
<div><span>01</span><b>Fabric first</b><p>Every piece names what it is made of. We favor natural fibers because they wear better and age well.</p></div>
<div><span>02</span><b>Elegant, never boring</b><p>Classic foundations with one deliberate detail that makes the outfit yours.</p></div>
<div><span>03</span><b>Honest about it</b><p>Our images are AI-generated and labeled. The clothes in them are real, checked and linked.</p></div>
<div><span>04</span><b>Made to be kept</b><p>Fewer, better pieces, worn for years and handed down.</p></div>
</section>"""
    return page("Purogé | Natural fiber, found for you", body, site,
                "Linen and natural-fiber outfits for work and travel, curated in San Diego. Every piece found, checked and linked, in two price versions.",
                wide=True, image="/images/set/del-mar-living.jpg")


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
        keys = used_keys(site, looks, g)
        if not keys:
            continue
        chips = "".join(f'<button type="button" class="chip" aria-pressed="false" data-g="{g}" data-v="{k}">{e(label(site, g, k))}</button>'
                        for k in keys)
        groups.append(f'<details class="dd" data-g="{g}"><summary>{title}<span class="dd-n"></span><span class="dd-car" aria-hidden="true"></span></summary>'
                      f'<div class="dd-panel"><div class="chips">{chips}</div></div></details>')
    cards = "".join(card(l, site) for l in looks)
    body = f"""<p class="meta" style="margin-top:24px">Every look</p>
<h1 style="margin-top:8px">All looks</h1>
<div class="fbar"><span class="fbar-l">Filter</span>{"".join(groups)}<button type="button" class="fclear" hidden>Clear</button></div>
<p class="count" id="count">{len(looks)} looks</p>
<div class="grid" id="grid">{cards}</div>
<script>
const sel={{occasion:new Set(),pairing:new Set(),mood:new Set(),season:new Set()}};
const cards=[...document.querySelectorAll('#grid .card')], count=document.getElementById('count'), clr=document.querySelector('.fclear');
const dds=[...document.querySelectorAll('.dd')];
function apply(){{let n=0;cards.forEach(c=>{{const ok=Object.entries(sel).every(([g,s])=>!s.size||(c.dataset[g]||'').split(' ').some(v=>s.has(v)));c.hidden=!ok;if(ok)n++;}});
count.textContent=n+(n===1?' look':' looks');let any=false;
dds.forEach(d=>{{const k=sel[d.dataset.g].size;d.querySelector('.dd-n').textContent=k?' · '+k:'';d.classList.toggle('on',k>0);if(k)any=true;}});clr.hidden=!any;}}
document.querySelectorAll('.fbar .chip').forEach(b=>b.onclick=()=>{{const s=sel[b.dataset.g],on=b.getAttribute('aria-pressed')!=='true';b.setAttribute('aria-pressed',on);on?s.add(b.dataset.v):s.delete(b.dataset.v);apply();}});
dds.forEach(d=>d.addEventListener('toggle',()=>{{if(d.open)dds.forEach(o=>{{if(o!==d)o.open=false}})}}));
document.addEventListener('click',ev=>{{if(!ev.target.closest('.dd'))dds.forEach(d=>d.open=false)}});
clr.onclick=()=>{{Object.values(sel).forEach(s=>s.clear());document.querySelectorAll('.fbar .chip').forEach(b=>b.setAttribute('aria-pressed','false'));dds.forEach(d=>d.open=false);apply();}};
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
    body = """<article class="story">
<p class="meta" style="margin-top:24px">Our story</p>
<h1 style="margin-top:8px">Three women are hidden in our name.</h1>
<p class="lead">Before there was a brand, there was a road, a needle, and twenty-four children to feed.</p>

<h2>The road</h2>
<p>My Lola Purisima, now 91, sewed and sold used clothes for a living. She walked miles upon miles with a pile of
second-hand clothes balanced on her head, selling each piece to someone who would wear it again.</p>
<p>That is how she raised twelve children.</p>

<h2>The needle</h2>
<p>My Lola Roberta, now 89, sewed sixteen hours a day to help support her family. Sixteen hours is a day that begins
before the light and ends long after it.</p>
<p>She raised twelve children, too.</p>

<blockquote class="story-quote">Twenty-four children. Two women. One needle each, and more miles than anyone counted.</blockquote>

<h2>The name</h2>
<p class="names"><span>Pu</span>risima · <span>Ro</span>berta · Ro<span>ge</span>nie</p>
<p>Purogé carries all three of us: the first sound of each Lola’s name, and mine. The accent in our logo
is drawn as a single stitch, for them.</p>

<h2>What they knew</h2>
<p>Lola Purisima was selling second-hand clothing long before anyone called it sustainable. To her, a garment
is never finished after one owner. It was carried, sold, and worn again.</p>
<p>Lola Roberta knows what a seam costs. When you have given sixteen hours to make something, you do not make it
to be thrown away.</p>
<p>That is the whole idea behind Purogé. Choose natural fiber. Choose pieces made well. Wear them for years,
then hand them on.</p>

<h2>From San Diego</h2>
<p>I’m Rogenie, their granddaughter, and I build Purogé from San Diego, California. I don’t carry clothes on my
head. I carry the search for you: I find every piece in an outfit, check what it is made of, and put it all on one
page, in two versions so it works for more than one budget.</p>
<p>And now we make our own. The Purogé label is linen, made here in San Diego, to be worn for years and
handed on.</p>
<p>Both of my Lolas are still with us. This is for them.</p>
<p>Three women are hidden in our name. Now you know where to find them.</p>
<p class="note">Lola is Tagalog for grandmother.</p>
<p style="margin-top:28px"><a class="btn" href="/looks/">See the looks</a>
<a class="btn off" href="/journal/why-humans-should-wear-sustainable-clothing/">Why natural fiber matters</a></p>
</article>"""
    return page("Our story | Purogé", body, site,
                "Purogé is named for Lola Purisima, who walked miles selling second-hand clothes, and Lola Roberta, "
                "who sewed sixteen hours a day. Their granddaughter Rogenie builds it from San Diego.",
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
            "favicon.svg", "style.css", "404.html", "robots.txt", "sitemap.txt", "CNAME", "journal", "llms.txt", "brand"}


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
    global SHOW_DRAFTS
    show_drafts = SHOW_DRAFTS = "--drafts" in sys.argv
    site, looks, series_list = load(show_drafts)
    if OUT.exists():
        shutil.rmtree(OUT)
    d = site["domain"]
    write(OUT / "style.css", CSS)
    if (ROOT / "images" / "looks").exists():
        shutil.copytree(ROOT / "images" / "looks", OUT / "images" / "looks")
    if (ROOT / "images" / "set").exists():
        shutil.copytree(ROOT / "images" / "set", OUT / "images" / "set")
    write(OUT / "favicon.svg", FAVICON)
    if (ROOT / "brand").exists():
        shutil.copytree(ROOT / "brand", OUT / "brand")
    write(OUT / "CNAME", d)
    write(OUT / "robots.txt", f"User-agent: *\nDisallow: /go/\n\n"
          "# Search engines and AI answer engines are welcome to read and cite this site.\n"
          + "".join(f"User-agent: {b}\nAllow: /\nDisallow: /go/\n\n" for b in
                    ["OAI-SearchBot", "ChatGPT-User", "GPTBot", "PerplexityBot", "ClaudeBot", "Claude-SearchBot", "Google-Extended"])
          + f"Sitemap: https://{d}/sitemap.txt\nSitemap: https://{d}/journal/sitemap.xml\n")
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
