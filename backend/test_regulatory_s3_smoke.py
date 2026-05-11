"""
Smoke-test S3 wiring for regulatory data (optional).

Run from repo root or backend/ with credentials that can read the bucket:

  cd backend
  export DATA_S3_BUCKET=lotor-regulatory-assistant-dev-runtime-data-<account-id>
  export DATA_S3_PREFIX=regulatory-app-data
  export AWS_REGION=us-east-2
  PYTHONPATH=. pytest test_regulatory_s3_smoke.py -v
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("DATA_S3_BUCKET") or "").strip(),
    reason="Set DATA_S3_BUCKET (and AWS_REGION) to run S3 smoke tests",
)


def test_s3_key_matches_prefix_layout():
    from utils import regulatory_data_io as rio

    rio._s3_client.cache_clear()
    pfx = (os.environ.get("DATA_S3_PREFIX") or "regulatory-app-data").strip().strip("/")
    key = rio.s3_object_key("payer_data/Productndc_Dim.csv")
    assert key.startswith(pfx + "/")
    assert "payer_data/Productndc_Dim.csv" in key


def _fail_s3_access_with_hints(exc: BaseException) -> None:
    from utils import regulatory_data_io as rio

    bucket = os.environ["DATA_S3_BUCKET"].strip()
    key = rio.s3_object_key("payer_data/Productndc_Dim.csv")
    region = (os.environ.get("AWS_REGION") or "us-east-2").strip()
    pytest.fail(
        f"{type(exc).__name__}: {exc}\n"
        f"  Bucket/key: s3://{bucket}/{key}\n"
        f"  Compare CLI (same shell / AWS_PROFILE):\n"
        f"    aws sts get-caller-identity\n"
        f"    aws s3api head-object --bucket {bucket} --key {key} --region {region}\n"
        f"  Upload (PutObject) can work without GetObject on your IAM principal. The EKS backend role\n"
        f"  has s3:GetObject in platform-dev.yml; your SSO user may need the same on regulatory-app-data/*.\n"
        f"  See infra/aws/README.md (local S3 read for developers)."
    )


def test_head_object_known_file():
    pytest.importorskip("boto3", reason="pip install -r requirements.txt (boto3 needed for S3)")
    from botocore.exceptions import ClientError

    from utils import regulatory_data_io as rio

    rio._s3_client.cache_clear()
    bucket = os.environ["DATA_S3_BUCKET"].strip()
    key = rio.s3_object_key("payer_data/Productndc_Dim.csv")
    try:
        rio._s3_client().head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        _fail_s3_access_with_hints(e)
    assert rio.regulatory_file_exists("payer_data/Productndc_Dim.csv")


def test_read_csv_snippet():
    pytest.importorskip("boto3", reason="pip install -r requirements.txt (boto3 needed for S3)")
    from botocore.exceptions import ClientError

    from utils import regulatory_data_io as rio

    rio._s3_client.cache_clear()
    bucket = os.environ["DATA_S3_BUCKET"].strip()
    key = rio.s3_object_key("payer_data/Productndc_Dim.csv")
    try:
        rio._s3_client().head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        _fail_s3_access_with_hints(e)
    try:
        df = rio.read_regulatory_csv("payer_data/Productndc_Dim.csv", nrows=3)
    except FileNotFoundError as e:
        _fail_s3_access_with_hints(e)
    assert len(df) <= 3
    assert len(df.columns) > 0
