"""
Optional authenticated PMS FHIR read (Write PMS IG) — Phase 2+.
GET MedicinalProductDefinition/{pmsId}/$everything when EMA_PMS_BASE_URL is configured.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

FHIR_ACCEPT = "application/fhir+json"


class EmaPmsClient:
    async def read_medicinal_product_everything(self, pms_id: str) -> Optional[Dict[str, Any]]:
        if not settings.EMA_PMS_READ_ENABLED or not settings.EMA_PMS_BASE_URL.strip():
            logger.debug("PMS read disabled or EMA_PMS_BASE_URL unset")
            return None
        base = settings.EMA_PMS_BASE_URL.rstrip("/")
        url = f"{base}/MedicinalProductDefinition/{pms_id}/$everything"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                r = await client.get(url, headers={"Accept": FHIR_ACCEPT})
                if r.status_code != 200:
                    logger.warning("PMS $everything %s -> %s", pms_id, r.status_code)
                    return None
                return r.json()
        except Exception as e:
            logger.warning("PMS read failed: %s", e)
            return None


ema_pms_client = EmaPmsClient()
