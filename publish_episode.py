"""Add an episode to the private podcast feed (GitHub Pages) and rebuild feed.xml.

Usage:
  python3 publish_episode.py REPO_DIR BASE_URL MP3_PATH "Episode title" "Short description" [YYYY-MM-DD]

REPO_DIR  local clone of the GitHub Pages repo (contains cover.jpg)
BASE_URL  public Pages URL, e.g. https://<user>.github.io/bank-credit-briefing
Re-encodes to 64 kbps mono (speech quality, ~0.5 MB/min) and keeps the newest 14 episodes; older MP3s are deleted from the repo.
"""
import sys, os, json, shutil, subprocess, datetime, email.utils
from xml.sax.saxutils import escape

KEEP = 14
repo, base, mp3, title, desc = sys.argv[1:6]
date = sys.argv[6] if len(sys.argv) > 6 else datetime.date.today().isoformat()
base = base.rstrip("/")
os.makedirs(f"{repo}/episodes", exist_ok=True)

name = f"Bank_Briefing_{date}.mp3"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "44100", "-b:a", "64k",
                f"{repo}/episodes/{name}"], check=True)
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                     "-of", "csv=p=0", f"{repo}/episodes/{name}"]).decode().strip())

db_path = f"{repo}/episodes.json"
eps = json.load(open(db_path)) if os.path.exists(db_path) else []
eps = [e for e in eps if e["file"] != name]
pub = datetime.datetime.now(datetime.timezone.utc)
eps.append({"file": name, "title": title, "desc": desc, "date": date,
            "pub": email.utils.format_datetime(pub), "bytes": os.path.getsize(f"{repo}/episodes/{name}"),
            "dur": int(dur)})
eps.sort(key=lambda e: e["date"], reverse=True)
for old in eps[KEEP:]:
    p = f"{repo}/episodes/{old['file']}"
    if os.path.exists(p): os.remove(p)
eps = eps[:KEEP]
json.dump(eps, open(db_path, "w"), indent=1)

def hms(s): return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
items = "\n".join(f"""  <item>
   <title>{escape(e['title'])}</title>
   <description>{escape(e['desc'])}</description>
   <itunes:summary>{escape(e['desc'])}</itunes:summary>
   <enclosure url="{base}/episodes/{e['file']}" length="{e['bytes']}" type="audio/mpeg"/>
   <guid isPermaLink="false">bank-credit-briefing-{e['date']}</guid>
   <pubDate>{e['pub']}</pubDate>
   <itunes:duration>{hms(e['dur'])}</itunes:duration>
   <itunes:explicit>false</itunes:explicit>
  </item>""" for e in eps)

feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
 <channel>
  <title>Bank Credit Briefing</title>
  <link>{base}/</link>
  <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
  <language>en-gb</language>
  <description>Private daily briefing on European, US and Asian banks through a credit lens, with IPOs, a cross-asset wrap and market history. AI-generated from public sources; not investment advice.</description>
  <itunes:author>Bank Credit Briefing</itunes:author>
  <itunes:image href="{base}/cover.jpg"/>
  <itunes:category text="Business"><itunes:category text="Investing"/></itunes:category>
  <itunes:explicit>false</itunes:explicit>
  <itunes:block>Yes</itunes:block>
  <itunes:type>episodic</itunes:type>
{items}
 </channel>
</rss>
"""
open(f"{repo}/feed.xml", "w", encoding="utf-8").write(feed)
open(f"{repo}/index.html", "w").write('<!doctype html><meta charset="utf-8"><title>Bank Credit Briefing</title>'
                                      '<p>Private feed. In Apple Podcasts: Library &rarr; &hellip; &rarr; Follow a Show by URL &rarr; '
                                      f'<code>{base}/feed.xml</code></p>')
open(f"{repo}/.nojekyll", "w").close()
print("feed rebuilt:", len(eps), "episodes;", f"{base}/feed.xml")
