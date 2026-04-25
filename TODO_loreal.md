# L'Oréal Adapter — Discovery Notes

## Current status
Stubbed. Returns 0 jobs with a warning log. No fake data.

## What we found

Careers site: `https://careers.loreal.com/es_ES/jobs/`

AJAX search endpoint:
```
GET https://careers.loreal.com/es_ES/jobs/SearchJobsAJAX/
  ?3_110_3=18000        ← Argentina filter (L'Oréal internal country code)
```

- `3_110_3=18000` confirmed to return exactly 3 Argentina jobs in one response — no pagination.
- For global results: drop the filter and use `?p=2`, `?p=3`, etc. for page navigation (20/page).
- Response is HTML fragments, not JSON. `<article class="... article--result ...">` per job.

### HTML structure per job
```html
<article class="column column--pad column--stretch article--result">
  <div class="article__header__text">
    <h3><a href="https://careers.loreal.com/es_ES/jobs/JobDetail/.../JOB_ID">TITLE</a></h3>
    <div class="article__header__text__subtitle serif">
      <span>LOCATION</span>
      <span>Publicado DD-Mon-YYYY</span>
    </div>
  </div>
  <div class="article__content">SHORT DESCRIPTION...</div>
  <div class="article__header__actions row" id="jobIdJOB_ID">...</div>
</article>
```

### BeautifulSoup parsing code (ready to use once unblocked)
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
for article in soup.select("article.article--result"):
    title_link = article.select_one("h3 a")
    title = title_link.get_text(strip=True)
    apply_url = title_link["href"]
    spans = (article.select_one(".article__header__text__subtitle") or {}).find_all("span")
    location = spans[0].get_text(strip=True) if spans else ""
    posted_raw = spans[1].get_text(strip=True) if len(spans) > 1 else None
    description = (article.select_one(".article__content") or object()).get_text(" ", strip=True)
    id_div = article.select_one("[id^='jobId']")
    job_id = id_div["id"].replace("jobId", "") if id_div else ""
```

## What blocks us

Cloudflare Bot Management is active on `careers.loreal.com`. It:
1. Issues a `__cf_bm` cookie on first request
2. Serves a "Just a moment..." JS challenge page (HTTP 200 with challenge HTML, or 403)
3. The challenge requires JavaScript to solve — `requests` cannot do this

The first cold request to the AJAX endpoint succeeds (we confirmed 3 Argentina jobs in
discovery). But subsequent requests — as would happen in any real run — are blocked.

## Next steps

**Option A — `curl_cffi` (recommended, keeps requests-only spirit):**
```bash
pip install curl-cffi
```
```python
from curl_cffi import requests as cffi_requests
r = cffi_requests.get(url, impersonate="chrome124")
```
`curl_cffi` impersonates a real browser's TLS fingerprint, which passes Cloudflare's
bot check without needing JavaScript. Drop-in replacement for `requests`.

**Option B — Playwright (headless browser, heavier):**
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://careers.loreal.com/es_ES/jobs/")
    # trigger the search, intercept the AJAX response
```

**Option C — Manual cookie capture:**
Open Chrome → careers.loreal.com → copy `__cf_bm` + `cf_clearance` cookies →
hardcode them as env vars. Fragile (expires in ~30 min) but works for a demo run.

## Robots.txt
L'Oréal uses `Allow` + `noindex` strategy — the AJAX endpoint is NOT in Disallow.
Crawling is permitted; the CF block is a bot-detection measure, not a legal one.
