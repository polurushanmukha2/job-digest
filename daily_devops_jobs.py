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

# Workday tenants. Each company runs its own Workday with a different host,
# data center (wd1/wd3/wd5/...), and site name. You must read all three off
# the company's careers URL. Example careers URL:
#   https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite
#     host = "nvidia.wd5.myworkdayjobs.com"
#     site = "NVIDIAExternalCareerSite"
#   (tenant "nvidia" is auto-derived from the first part of the host)
#
# Add entries as {"host": "...", "site": "..."}. See README for how to find them.
WORKDAY = [
    # {"host": "nvidia.wd5.myworkdayjobs.com", "site": "NVIDIAExternalCareerSite"},
]

US_ONLY = True          # False to include non-US roles too
TIMEOUT = 20
OUTDIR = Path("results")

# --------------------------- HELPERS ------------------------------

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "job-digest/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def post_json(url, payload, referer=""):
    body = json.dumps(payload).encode("utf-8")
    headers = {
        # A realistic browser-ish header set; Workday sits behind Akamai and
        # rejects bare clients. Keep requests slow (see delays in main()).
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0 Safari/537.36"),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
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


def from_workday(entry):
    """entry = {'host': 'tenant.wdN.myworkdayjobs.com', 'site': 'SiteName'}.
    Searches once per INCLUDE keyword (Workday ranks by searchText), paginates
    by offset, and de-dupes locally. Builds public apply URLs from externalPath.
    """
    host = entry["host"].strip().strip("/")
    site = entry["site"].strip().strip("/")
    tenant = host.split(".")[0]                      # subdomain = tenant
    label = entry.get("label", tenant)
    cxs = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    referer = f"https://{host}/en-US/{site}"
    out, seen = [], set()

    # Workday search is keyword-ranked, so query each term and merge results.
    search_terms = ["DevOps", "Site Reliability", "Platform Engineer",
                    "Kubernetes", "Cloud Engineer", "Infrastructure"]
    for term in search_terms:
        offset, limit = 0, 20
        while True:
            payload = {"appliedFacets": {}, "limit": limit,
                       "offset": offset, "searchText": term}
            try:
                data = post_json(cxs, payload, referer=referer)
            except Exception as e:
                print(f"  ! workday/{label} ({term}): {e}", file=sys.stderr)
                break
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for p in postings:
                ext = p.get("externalPath", "")
                if not ext or ext in seen:
                    continue
                seen.add(ext)
                title = p.get("title", "")
                loc = p.get("locationsText", "") or ""
                if matches(title, loc, ""):
                    out.append({
                        "company": label, "source": "workday", "title": title,
                        "location": loc,
                        "url": f"https://{host}/en-US/{site}{ext}",
                        "updated": p.get("postedOn", ""),
                    })
            total = data.get("total", 0)
            offset += limit
            if offset >= total or offset >= 200:   # 200 cap = politeness guard
                break
            time.sleep(0.4)
        time.sleep(0.5)
    return out


# ----------------------------- MAIN -------------------------------

SEEN_PATH = OUTDIR / "seen.json"


def load_seen():
    """Set of job URLs already reported in past runs."""
    try:
        with open(SEEN_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen):
    OUTDIR.mkdir(exist_ok=True)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=0)


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%Y-%m-%d_%H%MZ")   # date + time, so 2 runs/day don't collide
    OUTDIR.mkdir(exist_ok=True)
    rows = []

    print(f"Scanning {len(GREENHOUSE)} Greenhouse + {len(LEVER)} Lever + "
          f"{len(ASHBY)} Ashby + {len(WORKDAY)} Workday boards...")
    for s in GREENHOUSE:
        rows += from_greenhouse(s); time.sleep(0.3)
    for s in LEVER:
        rows += from_lever(s); time.sleep(0.3)
    for s in ASHBY:
        rows += from_ashby(s); time.sleep(0.3)
    for w in WORKDAY:
        rows += from_workday(w); time.sleep(1.0)   # extra pause: Workday is rate-sensitive

    # de-dupe within this run by URL
    dedup, unique = set(), []
    for r in rows:
        if r["url"] and r["url"] not in dedup:
            dedup.add(r["url"]); unique.append(r)

    # keep only roles we have NOT reported in any previous run
    seen = load_seen()
    new_rows = [r for r in unique if r["url"] not in seen]
    new_rows.sort(key=lambda r: (r["company"], r["title"]))

    csv_path = OUTDIR / f"jobs_{stamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["company", "source", "title", "location", "url", "updated"])
        w.writeheader(); w.writerows(new_rows)

    md_path = OUTDIR / f"jobs_{stamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# New roles since last run - {stamp}\n\n"
                f"**{len(new_rows)} new** (of {len(unique)} currently open and matching)\n")
        cur = None
        for r in new_rows:
            if r["company"] != cur:
                cur = r["company"]
                f.write(f"\n## {cur} ({r['source']})\n\n")
            f.write(f"- [{r['title']}]({r['url']}) - {r['location']}\n")
        if not new_rows:
            f.write("\n_Nothing new this run._\n")

    # remember everything we matched this run, so it won't show again
    seen.update(r["url"] for r in unique)
    save_seen(seen)

    print(f"\nDone. {len(new_rows)} NEW of {len(unique)} matching "
          f"-> {csv_path} and {md_path}")


if __name__ == "__main__":
    main()
