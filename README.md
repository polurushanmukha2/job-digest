# DevOps Job Digest

A lightweight automation project that scans public job-board APIs and creates a daily digest of DevOps, SRE, Platform, Cloud, Kubernetes, and Terraform roles.

I built this because job searching can get repetitive very quickly. Instead of manually checking the same company career pages every day, this script pulls matching roles into a clean CSV and Markdown digest so I can review relevant openings faster and apply more intentionally.

The project is intentionally simple: no API keys, no paid services, and no auto-apply behavior.

## What it does

* Scans public job-board APIs for Greenhouse, Lever, Ashby, and configurable Workday boards
* Filters roles by DevOps, SRE, Platform, Cloud, Kubernetes, Terraform, observability, and release engineering keywords
* Removes roles that clearly mention no sponsorship, citizenship-only, clearance-only, or non-engineering functions
* Optionally filters for US-based roles
* Writes timestamped CSV and Markdown output under `results/`
* Maintains a `seen.json` file so the same job is not reported repeatedly
* Runs locally or automatically through GitHub Actions

## Why I built it

When applying for DevOps and Platform Engineering roles, I noticed that many good roles disappear quickly. I wanted a simple way to check target companies consistently without spending the first hour of every day opening the same career pages manually.

This project helps separate job discovery from job application. The script finds relevant openings, but I still review each role manually before applying and tailoring my resume.

## Tech stack

* Python 3.9+
* GitHub Actions
* Public Greenhouse, Lever, Ashby, and Workday-style APIs
* CSV and Markdown output
* Standard library only

## Run locally

```bash
python daily_devops_jobs.py
```

Example output:

```text
results/jobs_2026-06-03_1300Z.csv
results/jobs_2026-06-03_1300Z.md
```

## Run with GitHub Actions

The workflow runs on weekdays and can also be triggered manually.

```yaml
on:
  schedule:
    - cron: "17 12 * * 1-5"
    - cron: "43 16 * * 1-5"
    - cron: "43 20 * * 1-5"
  workflow_dispatch: {}
```

I avoid scheduling exactly at the top of the hour because scheduled GitHub Actions can be delayed during high-load periods.

## ATS coverage

| ATS            | Status           | Notes                                            |
| -------------- | ---------------- | ------------------------------------------------ |
| Greenhouse     | Supported        | Uses the public boards API                       |
| Lever          | Supported        | Uses the public postings API                     |
| Ashby          | Supported        | Uses the public job-board API                    |
| Workday        | Partial          | Requires per-company host and site configuration |
| Custom portals | Not included yet | Larger companies often need custom handling      |

## How to add a company

You need the company’s ATS slug, not just the branded careers URL.

For example:

* Greenhouse: `job-boards.greenhouse.io/companyslug`
* Lever: `jobs.lever.co/companyslug`
* Ashby: `jobs.ashbyhq.com/companyslug`

Add the slug to the matching list in `daily_devops_jobs.py`.

## What this project does not do

This project does not auto-apply to jobs.

That is intentional. For DevOps and sponsorship-focused roles, targeted applications usually work better than mass automation. This tool helps with discovery, but resume tailoring, outreach, and application quality still matter.

## Future improvements

* Add more company board slugs
* Improve Workday support
* Add email or Slack digest delivery
* Add a small dashboard for reviewing roles
* Add tags for company type, remote status, and sponsorship friendliness
* Improve duplicate detection across similar postings
