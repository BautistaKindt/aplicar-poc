# Mercado Libre Adapter — Discovery Notes

## Current status
Stubbed. The adapter returns 0 jobs and logs a warning. No fake data.

## What we found

Meli's careers site (`careers-meli.mercadolibre.com`) is a custom frontend
that redirects job searches to an Eightfold.ai tenant:

```
https://mercadolibre.eightfold.ai/careers
```

The jobs list API endpoint is:
```
GET https://mercadolibre.eightfold.ai/api/apply/v2/jobs
  ?domain=mercadolibre.com
  &start=0
  &num=25
  &location=Argentina
```

This endpoint returns job objects with fields: `id`, `name`, `location`, `department`,
`description`, `apply_url`, `posted_date` — exactly what we need.

## What blocks us

Every request to `/api/apply/v2/jobs` returns:
```json
{"message": "Not authorized for PCSX"}
```

**PCSX** is Eightfold's client-side CSRF protection. The token is generated in the
main application JavaScript bundle (not in the HTML or i18n scripts).
It cannot be derived from the session cookies (`_vs`, `_vscid`) alone — we tried.

Approaches that failed:
- Direct GET with browser User-Agent and Referer
- Loading the careers page first to get session cookies, then calling the API
- Passing `x-csrftoken` header with the raw `_vs` cookie value
- Session-based requests (cookies properly forwarded, still 403)

## Next step for a human

1. Open Chrome and go to `https://mercadolibre.eightfold.ai/careers`
2. Open DevTools → Network tab → filter by `XHR` or `Fetch`
3. Type "Argentina" in the job search box and submit
4. Find the request to `/api/apply/v2/jobs` in the Network tab
5. Click it → Headers tab → look for a custom header (likely `x-csrftoken`,
   `x-vscid`, `x-vs`, or a `Cookie` value that doesn't survive our session)
6. Copy the full request as cURL (right-click → Copy → Copy as cURL)
7. Paste it here — we can reverse-engineer the token generation from that

## Alternative approach

If the PCSX token rotates per-session, a simpler path is to use
`playwright` or `selenium` (headless Chromium) to load the page and
intercept the API call. This would be ~30 lines of code and no reverse-engineering.
Add `playwright` to requirements.txt and build `adapters/mercadolibre_playwright.py`.
This is deliberately out of scope for this POC (no headless browsers) but is
the cleanest production path.
