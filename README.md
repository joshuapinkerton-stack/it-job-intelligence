# it-job-intelligence

Aggregate IT and cloud job postings from public search pages and extract structured skills snapshots to stay ahead of hiring trends.

## Personas

### B2B
Talent acquisition leaders, workforce planning managers, HR-tech platforms, and corporate sourcing teams use this actor to benchmark emerging skill demand across cities and remote markets. If you're refreshing your engineering competency framework or pricing contract roles, the structured skills snapshot removes the manual scrape-and-parse step.

### B2C
Job seekers, career coaches, indie recruiters, and civic-tech/open-data researchers use this actor to track what frameworks and tools are actually required in the wild right now. If you're building your third portfolio project or auditing which cloud certs are "in" for 2026, real posting data beats opinion every time.

## What it does

- Crawls listing pages from public job search endpoints (**Indeed**, **Dice**, **LinkedIn public URL pattern**)
- Extracts structured fields: title, company, location, salary range, remote flag, posted date, direct URL
- Enqueues detail links when available and normalizes overlapping fields
- Emits:
  - `job_posting` — one row per parsed job
  - `skills_snapshot` — one per listing/detail page with aggregated tool counts

## Model

| Event | Price |
|---|---|
| `job_posting` | $0.06 |
| `skills_snapshot` | $0.12 |

## Example input

```json
{
  "searchQuery": "cloud engineer",
  "location": "United States",
  "maxJobs": 50,
  "maxPages": 3,
  "urls": [
    { "url": "https://www.indeed.com/jobs?q=cloud+engineer&l=United+States" },
    { "url": "https://www.dice.com/jobs?q=cloud+engineer&l=United+States" }
  ]
}
```

## Notes

- Configure `urls` to point search pages or allow the actor to build them from `searchQuery` + `location`.
- Public search pages change layout often; retarget extraction with CSS selectors if a source redesigns.
- LinkedIn public search URLs require a logged-out profile; use responsibly and respect `robots.txt`.
