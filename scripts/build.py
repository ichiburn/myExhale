import datetime
import re
from pathlib import Path
from jinja2 import Template

# ルートと入出力
ROOT = Path(__file__).resolve().parents[1]
PRIV = ROOT / "myExhale-private"   # サブモジュール名に合わせる
SITE = ROOT / "site"
SITE.mkdir(exist_ok=True)

# ========== 解析 ==========

def parse_file(p: Path):
    """
    1日1ファイル (# YYYY-MM-DD) を前提に、
    ## セクション見出し → 直下の '-' 箇条書きを全部拾う（最初の1行だけに制限しない）
    """
    txt = p.read_text(encoding="utf-8", errors="ignore")
    mdate = re.search(r"^#\s*(\d{4}-\d{2}-\d{2})", txt, re.M)
    date = mdate.group(1) if mdate else p.stem

    items = []
    cur = None
    for line in txt.splitlines():
        # セクション開始
        m = re.match(r"^##\s*(.+)", line)
        if m:
            cur = m.group(1).strip()
            continue
        # 箇条書き（セクションが設定されている間は全部拾う）
        if cur and re.match(r"^\s*-\s+", line):
            entry = re.sub(r"^\s*-\s+", "", line).strip()
            if entry:
                items.append((cur, entry))
            continue
        # 空行やその他行はスキップ
    # RSS用（今回は未使用だが将来用に持っておく）
    desc = " ".join([f"{c}: {line}" for c, line in items])
    return {"date": date, "items": items, "desc": desc}

def collect_all_entries():
    entries = []
    for p in sorted(PRIV.rglob("*.md")):
        entries.append(parse_file(p))
    # 日付でソート（古→新）
    entries.sort(key=lambda x: x["date"])
    return entries

def streak(entries):
    if not entries:
        return 0
    dates = [datetime.date.fromisoformat(e["date"]) for e in entries]
    s = 1
    for i in range(len(dates)-1, 0, -1):
        if (dates[i] - dates[i-1]).days == 1:
            s += 1
        else:
            break
    return s

# ========== 表示用データ整形 ==========

def only_current_month(entries, tz_hours=9):
    """
    当月のみ抽出（JST基準）。“最新の記録が別月”でも、仕様通り“今月”を出す。
    """
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=tz_hours)
    y, m = now.year, now.month
    ym = f"{y:04d}-{m:02d}"
    month_entries = [e for e in entries if e["date"].startswith(ym)]
    return ym, month_entries

# ========== テンプレート ==========

HTML = Template("""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>myExhale ({{ym}})</title>
<style>
  :root { --fg:#111; --muted:#666; --line:#eee; --bg:#fff; --badge:#222; }
  @media (prefers-color-scheme: dark) {
    :root { --fg:#eee; --muted:#9aa; --line:#2a2a2a; --bg:#0b0b0b; --badge:#ddd; }
  }
  html,body { margin:0; padding:0; background:var(--bg); color:var(--fg); font:16px/1.65 system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans JP", sans-serif; }
  .wrap { max-width: 880px; margin: 40px auto; padding: 0 20px; }
  h1 { margin: 0; font-size: 28px; letter-spacing: .2px; }
  .sub { color: var(--muted); margin: 6px 0 16px; }
  .meta { color: var(--muted); margin: 0 0 24px; }
  .toolbar { display:flex; gap:8px; margin: 10px 0 18px; flex-wrap:wrap; }
  button { padding:8px 12px; border-radius:10px; border:1px solid var(--line); background:transparent; color:var(--fg); cursor:pointer; }
  button:hover { background: rgba(127,127,127,.08); }
  .day { border-top:1px solid var(--line); padding:14px 0; }
  .date { display:flex; align-items:center; justify-content:space-between; font-weight:700; cursor:pointer; user-select:none; }
  .date .chev { transition: transform .18s ease; margin-left: 8px; font-weight:400; color:var(--muted); }
  .collapsed .chev { transform: rotate(-90deg); }
  ul { margin: 10px 0 0 22px; padding:0; }
  li { margin: 6px 0; list-style: disc; }
  .badge { display:inline-block; padding:2px 8px; border:1px solid var(--line); border-radius:12px; margin-right:6px; color:var(--badge); }
  .hidden { display:none; }
  footer { color: var(--muted); margin-top: 24px; font-size: 13px; }
  .empty { color: var(--muted); border:1px dashed var(--line); padding:16px; border-radius:12px; }
</style>
<div class="wrap">
  <h1>myExhale</h1>
  <p class="sub">凡から積む（{{ym}} / 当月のみ表示）</p>
  <p class="meta">Streak: <b>{{streak}}</b> days ・ Total days: <b>{{total}}</b></p>

  <div class="toolbar">
    <button id="openAll">すべて開く</button>
    <button id="closeAll">すべて閉じる</button>
  </div>

  {% if entries %}
    {% for e in entries|reverse -%}
      <div class="day">
        <div class="date collapsed" onclick="toggleList(this)">
          <span>{{e.date}}</span>
          <span class="chev">▸</span>
        </div>
        <ul class="hidden">
          {% for c, line in e["items"] -%}
            <li><span class="badge">{{c}}</span> {{line}}</li>
          {%- endfor %}
        </ul>
      </div>
    {%- endfor %}
  {% else %}
    <div class="empty">この月の記録はまだありません。</div>
  {% endif %}

  <footer>Last build: {{build_ts}} JST ・ <a href="./feed.xml">RSS</a></footer>
</div>

<script>
  function toggleList(header){
    const ul = header.nextElementSibling;
    ul.classList.toggle('hidden');
    header.classList.toggle('collapsed');
  }
  document.getElementById('openAll').onclick = () => {
    document.querySelectorAll('.day .date').forEach(h => {
      const ul = h.nextElementSibling;
      ul.classList.remove('hidden');
      h.classList.remove('collapsed');
    });
  };
  document.getElementById('closeAll').onclick = () => {
    document.querySelectorAll('.day .date').forEach(h => {
      const ul = h.nextElementSibling;
      ul.classList.add('hidden');
      h.classList.add('collapsed');
    });
  };
</script>
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
  <description><![CDATA[{{ e["desc"] }}]]></description>
  <pubDate>{{e.date}} 00:00:00 +0900</pubDate>
</item>
{%- endfor %}
</channel></rss>""")

# ========== ビルド ==========

def main():
    all_entries = collect_all_entries()
    ym, month_entries = only_current_month(all_entries, tz_hours=9)  # JST基準の当月

    # HTML（当月のみ）
    (SITE/"index.html").write_text(
        HTML.render(
            ym=ym,
            entries=month_entries,
            total=len(all_entries),
            streak=streak(all_entries),
            build_ts=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
        ),
        encoding="utf-8"
    )

    # RSS（軽量のため最新60日のみ）
    latest = all_entries[-60:]
    site_url = "{{PUBLIC_SITE_URL}}"
    (SITE/"feed.xml").write_text(
        RSS.render(entries=latest, site=site_url),
        encoding="utf-8"
    )
    print(f"built -> site/ (month={ym}, entries_this_month={len(month_entries)}, total={len(all_entries)})")

if __name__ == "__main__":
    main()
