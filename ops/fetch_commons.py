#!/usr/bin/env python3
"""Fetch stock video from Wikimedia Commons for lane B-roll (saved process).

Provenance-first: every clip keeps author + license (mostly CC BY / BY-SA
— attribution REQUIRED, unlike Pixabay). Pipeline: search -> download ->
transcode to H264 mp4 -> contact sheet -> registry draft (owner approves,
nothing auto-banks).

Usage:
    python3 ops/fetch_commons.py search "Naga Sadhu" --limit 6
    python3 ops/fetch_commons.py fetch --titles-file /tmp/titles.txt --out /tmp/commons/
    python3 ops/fetch_commons.py sheet --dir /tmp/commons/ --out /tmp/commons/sheet.png

Be polite: descriptive User-Agent, ~6s between requests (429s mean back off).
Transcode everything (webm/ogv sources) — the pipeline only eats mp4:
    ffmpeg -y -v error -i in.webm -c:v libx264 -pix_fmt yuv420p -crf 20 out.mp4
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

UA = "videofactory/1.0 (research)"
API = "https://commons.wikimedia.org/w/api.php?"


def _get(params, timeout=60):
    req = urllib.request.Request(API + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def cmd_search(args):
    q = args[0]
    limit = int(args[1]) if len(args) > 1 else 8
    d = _get({"action": "query", "format": "json", "generator": "search",
              "gsrsearch": q + " filetype:video", "gsrlimit": limit,
              "gsrnamespace": 6, "prop": "imageinfo",
              "iiprop": "url|size|extmetadata",
              "iiextmetadatafilter": "LicenseShortName|Artist", "iiurlwidth": 640})
    for pid, pg in list(d.get("query", {}).get("pages", {}).items()):
        ii = (pg.get("imageinfo") or [{}])[0]
        lic = (ii.get("extmetadata") or {}).get("LicenseShortName", {}).get("value", "?")
        print(f"{pg.get('title', '')[5:80]:75s} {ii.get('width')}x{ii.get('height')} [{lic[:28]}]")


def _fileinfo(title):
    d = _get({"action": "query", "format": "json", "titles": "File:" + title,
              "prop": "imageinfo", "iiprop": "url|size|extmetadata",
              "iiextmetadatafilter": "LicenseShortName|Artist"})
    return list(d["query"]["pages"].values())[0].get("imageinfo", [{}])[0]


def cmd_fetch(args):
    out, titles = "/tmp/commons", [a for a in args if not a.startswith("--")]
    if "--out" in args:
        out = args[args.index("--out") + 1]
    if "--titles-file" in args:
        titles = [l.strip() for l in
                  open(args[args.index("--titles-file")]).read().splitlines() if l.strip()]
    os.makedirs(out, exist_ok=True)
    rec_path = os.path.join(out, "rec.json")
    rec = json.load(open(rec_path)) if os.path.exists(rec_path) else []
    for t in titles:
        time.sleep(6)
        try:
            ii = _fileinfo(t)
            u = ii.get("url")
            if not u:
                print("nourl", t[:50])
                continue
            ext = u.split(".")[-1].split("?")[0][:4]
            dst = os.path.join(out, f"{abs(hash(t)) % 10 ** 8}.{ext}")
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=900) as r, open(dst, "wb") as f:
                f.write(r.read())
            lic = (ii.get("extmetadata") or {}).get("LicenseShortName", {}).get("value", "?")
            art = (ii.get("extmetadata") or {}).get("Artist", {}).get("value", "?")[:80]
            print(f"got {t[:45]:46s} {os.path.getsize(dst) // 1024}kB "
                  f"{ii.get('width')}x{ii.get('height')} [{lic[:24]}]")
            rec.append([t, dst, lic, art])
        except Exception as e:
            print("fail", t[:45], str(e)[:100])
    json.dump(rec, open(rec_path, "w"))
    print("registry draft:", rec_path, f"({len(rec)} entries)")


def cmd_sheet(args):
    import glob
    from PIL import Image, ImageDraw
    d = args[0] if args else "/tmp/commons"
    files = [p for p in sorted(glob.glob(os.path.join(d, "*")))
             if os.path.splitext(p)[1].lower() in (".mp4", ".webm", ".ogv", ".mov")]
    thumbs = []
    for p in files:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=noprint_wrappers=1", p],
                           capture_output=True, text=True)
        try:
            dur = float(r.stdout.strip().split("=")[1])
        except Exception:
            continue
        t = p + ".sheet.png"
        if subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(dur / 2),
                           "-i", p, "-vframes", "1", t]).returncode != 0:
            continue
        thumbs.append((p, dur, t))
    cols = 5
    tw, th = 300, 200
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    for i, (p, dur, t) in enumerate(thumbs):
        f = Image.open(t).convert("RGB")
        f.thumbnail((tw, th - 30))
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(f, (x + (tw - f.size[0]) // 2, y))
        dr.text((x + 4, y + th - 32), os.path.basename(p)[:30], fill=(0, 0, 0))
        dr.text((x + 4, y + th - 18), f"{dur:.0f}s", fill=(100, 100, 100))
    out = os.path.join(d, "sheet.png")
    sheet.save(out)
    print(f"sheet: {out} ({len(thumbs)} frames)")


CMDS = {"search": cmd_search, "fetch": cmd_fetch, "sheet": cmd_sheet}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        return 2
    CMDS[sys.argv[1]](sys.argv[2:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
