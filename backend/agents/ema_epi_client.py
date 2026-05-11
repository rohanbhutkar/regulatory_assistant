"""
EMA.EPI.Consuming API — official paths (see EMA API definition).

- ListBySearchParameter: GET {base}/consuming/api/fhir/List?title=&regulatoryAgency=
- ListById:            GET {base}/consuming/api/fhir/List/{id}
- BundleBySearchParameter: GET {base}/consuming/api/fhir/Bundle?carrierValue=&pms=&lang=
- BundleById:          GET {base}/consuming/api/fhir/Bundle/{id}

Docs: application/json responses; Accept includes json + fhir+json.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from config import settings

logger = logging.getLogger(__name__)

# EMA spec: JSON; fhir+json kept for interoperability
ACCEPT_EPI = "application/json, application/fhir+json;q=0.9"


def _fhir_text_from_resource(obj: Any, out: List[str], cap: int) -> None:
    if len("".join(out)) >= cap:
        return
    if isinstance(obj, dict):
        if "div" in obj and isinstance(obj["div"], str):
            chunk = re.sub(r"<[^>]+>", " ", obj["div"])
            chunk = re.sub(r"\s+", " ", chunk).strip()
            if chunk:
                out.append(chunk)
        for v in obj.values():
            _fhir_text_from_resource(v, out, cap)
    elif isinstance(obj, list):
        for v in obj:
            _fhir_text_from_resource(v, out, cap)


def extract_bundle_excerpt(bundle: Dict[str, Any], max_chars: int) -> str:
    parts: List[str] = []
    _fhir_text_from_resource(bundle, parts, max_chars)
    text = " ".join(parts)[:max_chars]
    return text.strip()


def bundle_ids_from_list_resource(resource: Dict[str, Any]) -> List[str]:
    """Extract Bundle logical ids from an ePI List resource (entry.item.reference)."""
    ids: List[str] = []
    for e in resource.get("entry") or []:
        if not isinstance(e, dict):
            continue
        item = e.get("item")
        if not isinstance(item, dict):
            continue
        ref = item.get("reference") or ""
        if isinstance(ref, str) and "Bundle/" in ref:
            part = ref.split("Bundle/", 1)[-1]
            bid = part.split("/")[0].strip()
            if bid:
                ids.append(bid)
    return ids


class EmaEpiClient:
    def _root(self) -> str:
        return settings.EMA_EPI_FHIR_ROOT.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": ACCEPT_EPI}
        if settings.EMA_EPI_SUBSCRIPTION_KEY:
            h["Ocp-Apim-Subscription-Key"] = settings.EMA_EPI_SUBSCRIPTION_KEY
        return h

    def _abs_url(self, path: str) -> str:
        base = settings.EMA_EPI_BASE_URL.rstrip("/")
        path = path if path.startswith("/") else f"/{path}"
        return f"{base}{path}"

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        url = self._abs_url(path)
        try:
            r = await client.get(url, params=params or {}, headers=self._headers())
            if r.status_code != 200:
                logger.debug("EMA ePI %s %s -> %s", path, params, r.status_code)
                return None
            return r.json()
        except Exception as e:
            logger.warning("EMA ePI GET failed %s: %s", url, e)
            return None

    async def search_by_title(self, title: str) -> List[Dict[str, Any]]:
        if not settings.EMA_EPI_ENABLED or not title.strip():
            return []
        root = self._root()
        path = f"{root}/List"
        timeout = httpx.Timeout(settings.EMA_EPI_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            data = await self._get(client, path, {"title": title.strip()})
            if not data:
                for legacy in _parse_legacy_list_search_paths():
                    data = await self._get(client, legacy, {"title": title.strip()})
                    if data:
                        break
            if not data:
                return []
            return self._normalize_bundle_or_list_response(data)

    async def fetch_list_by_id(self, list_id: str) -> Optional[Dict[str, Any]]:
        if not settings.EMA_EPI_ENABLED or not list_id.strip():
            return None
        lid = list_id.strip()
        root = self._root()
        path = f"{root}/List/{quote(lid, safe='')}"
        timeout = httpx.Timeout(settings.EMA_EPI_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            data = await self._get(client, path)
            if data:
                return data
            for legacy in _parse_legacy_list_by_id_paths(lid):
                data = await self._get(client, legacy)
                if data:
                    return data
            return None

    async def search_by_bundle_params(
        self,
        pms_id: Optional[str] = None,
        gtin: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not settings.EMA_EPI_ENABLED:
            return []
        params: Dict[str, str] = {}
        if pms_id:
            params["pms"] = pms_id
        if gtin:
            params["carrierValue"] = gtin
        if language:
            params["lang"] = language
        if not params:
            return []
        root = self._root()
        path = f"{root}/Bundle"
        timeout = httpx.Timeout(settings.EMA_EPI_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            data = await self._get(client, path, params)
            if not data:
                for legacy in _parse_legacy_bundle_search_paths():
                    data = await self._get(
                        client,
                        legacy,
                        _legacy_bundle_params_map(params),
                    )
                    if data:
                        break
            if not data:
                return []
            if isinstance(data, dict) and (
                data.get("resourceType") == "Bundle" or isinstance(data.get("entry"), list)
            ):
                return [data]
            return EmaEpiClient._normalize_bundle_or_list_response(data)

    async def fetch_bundle_by_id(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        if not settings.EMA_EPI_ENABLED or not bundle_id.strip():
            return None
        bid = bundle_id.strip()
        root = self._root()
        path = f"{root}/Bundle/{quote(bid, safe='')}"
        timeout = httpx.Timeout(settings.EMA_EPI_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            data = await self._get(client, path)
            if data:
                return data
            for legacy in _parse_legacy_bundle_by_id_paths(bid):
                data = await self._get(client, legacy)
                if data:
                    return data
            return None

    @staticmethod
    def _normalize_bundle_or_list_response(data: Any) -> List[Dict[str, Any]]:
        """BundleListResponse / Bundle: entry[].resource -> list of inner resources (e.g. List)."""
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if not isinstance(data, dict):
            return []
        if isinstance(data.get("entry"), list):
            out: List[Dict[str, Any]] = []
            for e in data["entry"]:
                if isinstance(e, dict) and isinstance(e.get("resource"), dict):
                    r = e["resource"]
                    if r.get("resourceType") == "OperationOutcome":
                        continue
                    out.append(r)
            if out:
                return out
        if data.get("resourceType") in ("List", "Bundle", "Composition"):
            return [data]
        return [data]


def _parse_csv(csv: str) -> List[str]:
    return [p.strip() for p in (csv or "").split(",") if p.strip()]


def _parse_legacy_list_search_paths() -> List[str]:
    return _parse_csv(getattr(settings, "EMA_EPI_LIST_PATH_CANDIDATES", ""))


def _parse_legacy_list_by_id_paths(list_id: str) -> List[str]:
    qid = quote(list_id.strip(), safe="")
    paths = []
    for tmpl in _parse_csv(getattr(settings, "EMA_EPI_LIST_BY_ID_PATH_CANDIDATES", "")):
        if "{id}" in tmpl:
            paths.append(tmpl.replace("{id}", qid))
        elif tmpl.endswith("/"):
            paths.append(f"{tmpl}{qid}")
    return paths


def _parse_legacy_bundle_search_paths() -> List[str]:
    return _parse_csv(getattr(settings, "EMA_EPI_BUNDLE_BY_SEARCH_PATH_CANDIDATES", ""))


def _legacy_bundle_params_map(params: Dict[str, str]) -> Dict[str, str]:
    out = dict(params)
    if "pms" in out and "pmsId" not in out:
        out["pmsId"] = out["pms"]
    if "carrierValue" in out and "dataCarrierIdentifierValue" not in out:
        out["dataCarrierIdentifierValue"] = out["carrierValue"]
    if "lang" in out and "language" not in out:
        out["language"] = out["lang"]
    return out


def _parse_legacy_bundle_by_id_paths(bundle_id: str) -> List[str]:
    qid = quote(bundle_id.strip(), safe="")
    paths = []
    for tmpl in _parse_csv(getattr(settings, "EMA_EPI_BUNDLE_BY_ID_PATH_CANDIDATES", "")):
        if "{id}" in tmpl:
            paths.append(tmpl.replace("{id}", qid))
        elif tmpl.endswith("/"):
            paths.append(f"{tmpl}{qid}")
    return paths


ema_epi_client = EmaEpiClient()
