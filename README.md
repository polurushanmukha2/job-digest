# job-digest
Daily scanner for DevOps/SRE roles at H-1B-friendly companies

# Daily DevOps Job Digest

Scans H-1B-friendly companies' public job boards every morning and writes a
filtered list of DevOps / SRE / Platform / Cloud roles. Built from the company
target list.

## What it does

1. Hits the **public** job-board APIs for Greenhouse, Lever, and Ashby boards.
2. Keeps only roles whose title/department match your keywords
   (DevOps, SRE, Platform, Kubernetes, Terraform, etc.).
3. Drops roles that say "no sponsorship", "US citizen", "clearance required", etc.
4. Optionally drops non-US roles.
5. Writes `results/jobs_YYYY-MM-DD.csv` and a readable `.md` digest.

No API keys required.

## Run it locally

```bash
python daily_devops_jobs.py
# -> results/jobs_2026-06-03.csv  and  results/jobs_2026-06-03.md
```

Needs Python 3.9+ (standard library only, nothing to pip install).

## Run it automatically every day (recommended: GitHub Actions)

1. Create a new GitHub repo, e.g. `job-digest`.
2. Put `daily_devops_jobs.py` in the root.
3. Put `job-digest.yml` in `.github/workflows/`.
4. Push. The workflow runs weekday mornings (13:00 UTC) and on manual trigger.
   Each run uploads the results as an artifact and commits them into the repo.

Other schedulers:
- **macOS/Linux:** `crontab -e` then `0 8 * * 1-5 cd /path && python3 daily_devops_jobs.py`
- **Windows:** Task Scheduler -> daily trigger -> action `python C:\path\daily_devops_jobs.py`

## ATS coverage (important)

| ATS         | Status        | Endpoint used                                              |
|-------------|---------------|------------------------------------------------------------|
| Greenhouse  | Working (v1)  | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`           |
| Lever       | Working (v1)  | `api.lever.co/v0/postings/{slug}?mode=json`                |
| Ashby       | Working (v1)  | `api.ashbyhq.com/posting-api/job-board/{slug}`             |
| Workday     | Not yet       | Each tenant has its own host + POST-based API (per-company)|
| Custom/FAANG| Not yet       | Amazon/Google/Apple/Microsoft pages need bespoke handling  |

Most big enterprises (Microsoft, Salesforce, many banks/healthcare) run
**Workday**, and FAANG run custom portals. Those need a separate, heavier flow
(often a headless browser). v1 deliberately covers the boards with clean,
free JSON APIs first.

## How to add a company

You need the company's ATS **slug**, not its branded careers URL.

- **Greenhouse:** open the careers page, find the board URL like
  `job-boards.greenhouse.io/COMPANYSLUG` -> add `COMPANYSLUG` to the
  `GREENHOUSE` list.
- **Lever:** board looks like `jobs.lever.co/COMPANYSLUG` -> add to `LEVER`.
- **Ashby:** board looks like `jobs.ashbyhq.com/COMPANYSLUG` -> add to `ASHBY`.

Tip: view-source or check the network tab on a company's careers page to see
which ATS it uses and what the slug is.

## Tune the filters

Edit the lists at the top of `daily_devops_jobs.py`:
- `INCLUDE` - titles you want
- `EXCLUDE` - kill-words (sponsorship/clearance/non-eng roles)
- `US_ONLY` - set `False` to include international roles

## What this does NOT do (on purpose)

- It does not tailor your resume per role - do that thoughtfully per application.
- It does not auto-apply - most sites reject bot applications, and targeted
  applications win, especially for sponsorship roles.
