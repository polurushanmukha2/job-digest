#!/usr/bin/env python3
"""
daily_devops_jobs.py

Pulls DevOps / SRE / Platform / Cloud roles from H-1B-friendly companies'
PUBLIC job-board APIs (Greenhouse, Lever, Ashby), filters by keywords you
care about, drops roles that signal "no sponsorship / clearance", and writes
a dated CSV + Markdown digest you can skim each morning.

No API keys needed. Run it daily via cron, Windows Task Scheduler, or
GitHub Actions (workflow file included separately).

Usage:
    python daily_devops_jobs.py
"""

import csv
import json
import sys
import time
import datetime
import urllib.request
from pathlib import Path

# ----------------------------- CONFIG -----------------------------

# Keep a role only if its title/department contains one of these:
INCLUDE = [
    "devops", "site reliability", "sre", "platform engineer",
    "platform engineering", "infrastructure engineer", "cloud engineer",
    "kubernetes", "terraform", "ci/cd", "observability",
    "developer productivity", "build engineer", "release engineer",
]

# Drop a role if its title/location/department contains any of these:
EXCLUDE = [
    "no sponsorship", "unable to sponsor", "must not require sponsorship",
    "us citizen", "u.s. citizen", "security clearance", "clearance required",
    "ts/sci", "secret clearance", "(cleared)", "secret eligible",
    "secret/top secret", "top secret", "must be a us", "must be us",
    "account executive", "sales", "recruiter", "marketing", "counsel",
    "business development", "customer success",
    "partner manager", "account manager", "product manager",
    "intern",   # remove this line if you DO want internships
]

# Greenhouse board slugs = the part after greenhouse.io/
# (Seeded from your H-1B PDF's Greenhouse section. Add more as you find them.)
GREENHOUSE = [
    "clickhouse", "attentive", "boxinc", "customerio", "planetlabs",
    "recordedfuture", "torq", "transcendinc", "warp", "webflow",
    "amwell", "apptronik", "armada", "beaconbiosignals", "getbuilt",
    "centralreach", "circleso", "crunchyroll", "defenseunicorns",
    "elliginthealth", "ensono", "gallup", "globalityinc",
    "imaginepediatrics", "incode", "momentmarkets", "natera", "openly",
    "perfectserve", "rackner", "relativity", "rise8", "striveworks",
    "wurljobs",
]

# Lever slugs -> api.lever.co/v0/postings/{slug}?mode=json
LEVER = [
    # "example-company",
]

# Ashby job-board names -> api.ashbyhq.com/posting-api/job-board/{slug}
ASHBY = [
    # "example-company",
]

US_ONLY = True          # False to include non-US roles too
TIMEOUT = 20
OUTDIR = Path("results")

# --------------------------- HELPERS ------------------------------

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "job-digest/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def matches(title, location, dept=""):
    """True if the role passes include/exclude/US filters."""
    text = f"{title} {dept}".lower()
    if not any(k in text for k in INCLUDE):
        return False

    blob = f"{title} {location} {dept}".lower()
    if any(b in blob for b in EXCLUDE):
        return False

    if US_ONLY:
        loc = location.lower()
        non_us = [
            "india", "canada", "uk", "united kingdom", "germany", "ireland",
            "france", "australia", "singapore", "poland", "romania", "brazil",
            "mexico", "japan", "netherlands", "spain", "israel", "portugal",
            "colombia", "argentina", "sweden", "serbia", "tel aviv",
            "gothenburg", "amsterdam", "london", "mendoza", "bogota",
            "remote - emea", "remote - apac", "remote-emea", "remote-apac",
        ]
        if any(n in loc for n in non_us):
            return False
    return True


def from_greenhouse(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    out = []
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"  ! greenhouse/{slug}: {e}", file=sys.stderr)
        return out
    for j in data.get("jobs", []):
        title = j.get("title", "")
        loc = (j.get("location") or {}).get("name", "")
        dept = ", ".join(d.get("name", "") for d in j.get("departments", []))
        if matches(title, loc, dept):
            out.append({
                "company": slug, "source": "greenhouse", "title": title,
                "location": loc, "url": j.get("absolute_url", ""),
                "updated": j.get("updated_at", ""),
            })
    return out


def from_lever(slug):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    out = []
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"  ! lever/{slug}: {e}", file=sys.stderr)
        return out
    for j in data:
        title = j.get("text", "")
        cats = j.get("categories", {}) or {}
        loc = cats.get("location", "") or ""
        dept = cats.get("team", "") or ""
        if matches(title, loc, dept):
            out.append({
                "company": slug, "source": "lever", "title": title,
                "location": loc, "url": j.get("hostedUrl", ""), "updated": "",
            })
    return out


def from_ashby(slug):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false"
    out = []
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"  ! ashby/{slug}: {e}", file=sys.stderr)
        return out
    for j in data.get("jobs", []):
        title = j.get("title", "")
        loc = j.get("location", "") or ""
        dept = j.get("department", "") or ""
        if matches(title, loc, dept):
            out.append({
                "company": slug, "source": "ashby", "title": title,
                "location": loc,
                "url": j.get("jobUrl", "") or j.get("applyUrl", ""),
                "updated": "",
            })
    return out


# ----------------------------- MAIN -------------------------------

def main():
    today = datetime.date.today().isoformat()
    OUTDIR.mkdir(exist_ok=True)
    rows = []

    print(f"Scanning {len(GREENHOUSE)} Greenhouse + {len(LEVER)} Lever + "
          f"{len(ASHBY)} Ashby boards...")
    for s in GREENHOUSE:
        rows += from_greenhouse(s); time.sleep(0.3)
    for s in LEVER:
        rows += from_lever(s); time.sleep(0.3)
    for s in ASHBY:
        rows += from_ashby(s); time.sleep(0.3)

    # de-dupe by URL, then sort
    seen, unique = set(), []
    for r in rows:
        if r["url"] and r["url"] not in seen:
            seen.add(r["url"]); unique.append(r)
    unique.sort(key=lambda r: (r["company"], r["title"]))

    csv_path = OUTDIR / f"jobs_{today}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["company", "source", "title", "location", "url", "updated"])
        w.writeheader(); w.writerows(unique)

    md_path = OUTDIR / f"jobs_{today}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Matching roles - {today}\n\n**{len(unique)} roles found**\n")
        cur = None
        for r in unique:
            if r["company"] != cur:
                cur = r["company"]
                f.write(f"\n## {cur} ({r['source']})\n\n")
            f.write(f"- [{r['title']}]({r['url']}) - {r['location']}\n")

    print(f"\nDone. {len(unique)} roles -> {csv_path} and {md_path}")


if __name__ == "__main__":
    main()
