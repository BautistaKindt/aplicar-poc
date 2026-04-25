"""
Mercado Libre Adapter — STUB (endpoint discovery blocked)
==========================================================
Status: NOT WORKING — requires browser DevTools to capture CSRF token.
See TODO_meli.md for next steps.

What we know:
  ATS:      Eightfold.ai
  Tenant:   mercadolibre.eightfold.ai
  Jobs API: GET https://mercadolibre.eightfold.ai/api/apply/v2/jobs
              ?domain=mercadolibre.com&start=0&num=25&location=Argentina

What blocks us:
  Eightfold's "PCSX" CSRF protection returns 403 on all direct requests.
  The token is computed client-side in JS and cannot be derived from the
  session cookie alone. requests cannot execute JavaScript.
"""

import logging

from models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(company_config: dict) -> list[Job]:
    logger.warning(
        "Mercado Libre adapter is a stub — endpoint discovery required via browser DevTools. "
        "See TODO_meli.md for next steps."
    )
    return []
