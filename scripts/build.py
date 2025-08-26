import os, re, datetime
from pathlib import Path
from jinja2 import Template

ROOT = Path(__file__).resolve().parents[1]
PRIV = ROOT / "myExhale-private" 
SITE = ROOT / "site"
SITE.mkdir(exist_ok=True)

def parse_file(p: Path):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    date = re.search(r"^#\s*(\d{4}-\d{2}-\d{2})", txt, re.M)
    date = date.group(1) if date else p.stem
    items = []
    cur = None
    for line in txt.splitlines():
        if m := re.match(r"^##\s*(.+)", line):
            cur = m.group(1).strip()
        elif cur and re.match(r"^\s*-\s+", line):
            first = re.sub(r"^\s*-\s+", "", line).strip()
            items.append((cur, first))
            cur = None  # セクション最初の項目だけ拾う
    return {"date": date, "items": items}

def collect():
    entries = []
    for p in sorted(PRIV.glob("*.md")):
        entries.append(parse_file(p))
    return entries

HTML = Template("""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>myExhale</title>
<link rel="alternate" type="application/rss+xml" href="./feed.xml">
<style>
  body{font:16px/1.6 system-ui;margin:40px;max-width:780px}
  h1{margin:0} .sub{color:#666;margin:0 0 24px}
  .day{padding:14px 0;border-bottom:1px solid #eee}
  .date{font-weight:700}
  ul{margin:6px 0 0 22px}
  .badge{display:inline-block;padding:2px 8px;border:1px solid #ddd;border-radius:12px;margin-right:6px}
</style>
<h1>myExhale</h1>
<p class="sub">凡から積む ─ 呼吸を外に置くログ（要約のみ）</p>
<p>Streak: <b>{{streak}}</b> days ・ Total days: <b>{{total}}</b></p>
{% for e in entries|reverse -%}
<div class="day" id="{{e.date}}">
  <div class="date">{{e.date}}</div>
  <ul>
  {% for c, line in e.items %}<li><span class="badge">{{c}}</span> {{line}}</li>{% endfor %}
  </ul>
</div>
{%- endfor %}
<footer style="margin-top:24px;color:#777">Last build: {{build_ts}}</footer>
""")

RSS = Template("""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>myExhale</title>
<link>{{site}}</link>
<description>日々の証跡（要約のみ）</description>
{% for e in entries|reverse -%}
<item>
  <title>{{e.date}}</title>
  <link>{{site}}#{{e.date}}</link>
  <description><![CDATA[{% for c, line in e.items %}{{c}}: {{line}} {% endfor %}]]></description>
  <pubDate>{{e.date}} 00:00:00 +0900</pubDate>
</item>
{%- endfor %}
</channel></rss>""")

def streak(entries):
    if not entries: return 0
    dates = [datetime.date.fromisoformat(e["date"]) for e in entries]
    s = 1
    for i in range(len(dates)-1, 0, -1):
        if (dates[i] - dates[i-1]).days == 1: s += 1
        else: break
    return s

def main():
    entries = collect()
    total = len(entries)
    (SITE/"index.html").write_text(
        HTML.render(entries=entries, total=total, streak=streak(entries),
                    build_ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S +0900")),
        encoding="utf-8"
    )
    site_url = "{{PUBLIC_SITE_URL}}"
    (SITE/"feed.xml").write_text(RSS.render(entries=entries, site=site_url), encoding="utf-8")
    print("built -> site/")

if __name__ == "__main__":
    main()