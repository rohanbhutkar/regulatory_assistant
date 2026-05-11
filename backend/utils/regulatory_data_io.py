"""Load regulatory static files from repo ``data/`` or S3 (``DATA_S3_BUCKET`` + ``DATA_S3_PREFIX``)."""

from __future__ import annotations

import io
import logging
import os
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Optional

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def regulatory_data_local_dir() -> Path:
    override = (getattr(settings, "REGULATORY_DATA_DIR", None) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    repo_data = _BACKEND_ROOT.parent / "data"
    if repo_data.is_dir():
        return repo_data.resolve()
    return (_BACKEND_ROOT / "data").resolve()


def _use_s3() -> bool:
    return bool((getattr(settings, "DATA_S3_BUCKET", None) or "").strip())


def _s3_prefix_norm() -> str:
    return (getattr(settings, "DATA_S3_PREFIX", None) or "regulatory-app-data").strip().strip("/")


def s3_object_key(relative: str) -> str:
    rel = relative.strip().lstrip("/").replace("\\", "/")
    pfx = _s3_prefix_norm()
    return f"{pfx}/{rel}" if pfx else rel


@lru_cache(maxsize=1)
def _s3_client():
    import boto3

    region = (
        (getattr(settings, "AWS_REGION", None) or "").strip()
        or os.environ.get("AWS_REGION", "").strip()
        or None
    )
    endpoint = (getattr(settings, "AWS_ENDPOINT_URL_S3", None) or "").strip() or None
    kwargs: dict[str, Any] = {}
    if region:
        kwargs["region_name"] = region
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def regulatory_file_exists(relative: str) -> bool:
    rel = relative.strip().lstrip("/").replace("\\", "/")
    if _use_s3():
        try:
            _s3_client().head_object(Bucket=settings.DATA_S3_BUCKET.strip(), Key=s3_object_key(rel))
            return True
        except Exception:
            return False
    return (regulatory_data_local_dir() / rel).is_file()


def read_regulatory_bytes(relative: str) -> Optional[bytes]:
    rel = relative.strip().lstrip("/").replace("\\", "/")
    if _use_s3():
        try:
            obj = _s3_client().get_object(
                Bucket=settings.DATA_S3_BUCKET.strip(),
                Key=s3_object_key(rel),
            )
            return obj["Body"].read()
        except Exception as e:
            logger.warning("S3 read failed for %s: %s", rel, e)
            return None
    path = regulatory_data_local_dir() / rel
    if not path.is_file():
        return None
    return path.read_bytes()


def read_regulatory_csv(relative: str, **kwargs: Any) -> pd.DataFrame:
    rel = relative.strip().lstrip("/").replace("\\", "/")
    raw = read_regulatory_bytes(rel)
    if raw is None:
        raise FileNotFoundError(rel)
    return pd.read_csv(io.BytesIO(raw), **kwargs)


def read_regulatory_excel(relative: str, **kwargs: Any) -> pd.DataFrame:
    rel = relative.strip().lstrip("/").replace("\\", "/")
    raw = read_regulatory_bytes(rel)
    if raw is None:
        raise FileNotFoundError(rel)
    return pd.read_excel(io.BytesIO(raw), **kwargs)


def list_regulatory_dir(subdir: str, suffix: str = ".csv") -> list[str]:
    """File paths relative to the data root (posix), e.g. ``payer_data/Foo.csv``."""
    sub = subdir.strip().strip("/").replace("\\", "/")
    root = regulatory_data_local_dir()
    if _use_s3():
        prefix = s3_object_key(f"{sub}/") if sub else f"{_s3_prefix_norm()}/"
        data_prefix = _s3_prefix_norm()
        out: list[str] = []
        paginator = _s3_client().get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=settings.DATA_S3_BUCKET.strip(),
            Prefix=prefix,
        ):
            for obj in page.get("Contents") or []:
                key = obj["Key"]
                if suffix and not key.endswith(suffix):
                    continue
                if data_prefix and key.startswith(data_prefix + "/"):
                    rel_path = key[len(data_prefix) + 1 :]
                else:
                    rel_path = key
                if rel_path and not rel_path.endswith("/"):
                    out.append(rel_path)
        return sorted(out)

    base = root / sub if sub else root
    if not base.is_dir():
        return []
    pattern = f"*{suffix}" if suffix else "*"
    rels: list[str] = []
    for p in sorted(base.glob(pattern)):
        if p.is_file():
            rels.append(p.relative_to(root).as_posix())
    return rels
