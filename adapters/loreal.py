"""
L'Oréal HTML-Parsing Adapter — STUB (Cloudflare-blocked)
==========================================================
Status: NOT WORKING — Cloudflare Bot Management blocks automated requests.
See TODO_loreal.md for next steps.

What we know:
  Endpoint: GET https://careers.loreal.com/es_ES/jobs/SearchJobsAJAX/
  Argentina filter: ?3_110_3=18000   (confirmed to return Argentina-only jobs)
  HTML structure: <article class="... article--result ..."> blocks, one per job.

What blocks us:
  Cloudflare sets a __cf_bm cookie and serves a JS challenge page ("Just a moment...")
  on repeated requests. The first cold request succeeds, but subsequent ones (as would
  happen in production) are blocked with 403. Solving the CF challenge requires JS execution.

Parsing code is in TODO_loreal.md — fully drafted, just needs a bypass mechanism.
"""

import logging

from models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(company_config: dict) -> list[Job]:
    logger.warning(
        "L'Oréal adapter is a stub — Cloudflare bot protection blocks automated requests. "
        "See TODO_loreal.md for next steps."
    )
    return []
