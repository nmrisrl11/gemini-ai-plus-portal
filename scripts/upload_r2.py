"""
Cloudflare R2 Release Uploader for Gemini AI Plus Portal.

Uses boto3 (OpenSSL via urllib3) instead of AWS CLI's Windows Schannel client,
avoiding AWS_IO_TLS_ERROR_NEGOTIATION_FAILURE on Windows GitHub Actions runners.
Uploads:
  - releases/<tag>/<safe_filename>
  - releases/<tag>/SHA256SUMS.txt
  - latest/Gemini-AI-Plus-Portal-latest<ext>
  - latest/latest.json
"""

import argparse
import datetime
import json
import os
import sys

import boto3
from botocore.config import Config


def normalize_endpoint(raw_endpoint: str, bucket: str) -> str:
    endpoint = raw_endpoint.strip().rstrip("/")
    if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
        endpoint = f"https://{endpoint}"
    suffix = f"/{bucket}"
    if endpoint.endswith(suffix):
        endpoint = endpoint[: -len(suffix)]
    return endpoint


def upload_release(
    file_path: str,
    tag: str,
    sha256: str,
    checksums_path: str,
    bucket: str,
    endpoint: str,
    access_key: str,
    secret_key: str,
    public_base_url: str = "",
    github_output: str = "",
) -> int:
    if not os.path.isfile(file_path):
        print(f"[ERROR] Artifact not found: {file_path}")
        return 1

    endpoint_url = normalize_endpoint(endpoint, bucket)
    name = os.path.basename(file_path)
    safe_name = name.replace(" ", "-")
    ext = os.path.splitext(name)[1]
    latest_name = f"Gemini-AI-Plus-Portal-latest{ext}"
    size_bytes = os.path.getsize(file_path)

    cfg_kwargs = {
        "signature_version": "s3v4",
        "s3": {"addressing_style": "path"},
    }
    # Compatible with both older and newer botocore (>= 1.36 checksum defaults)
    try:
        s3_config = Config(
            **cfg_kwargs,
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
    except TypeError:
        s3_config = Config(**cfg_kwargs)

    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key.strip(),
        aws_secret_access_key=secret_key.strip(),
        region_name="auto",
        config=s3_config,
    )

    versioned_key = f"releases/{tag}/{safe_name}"
    latest_key = f"latest/{latest_name}"
    checksums_key = f"releases/{tag}/SHA256SUMS.txt"
    manifest_key = "latest/latest.json"

    print(f"[*] Uploading {versioned_key} ({size_bytes / (1024*1024):.2f} MB) to R2 bucket '{bucket}'...")
    client.upload_file(
        file_path,
        bucket,
        versioned_key,
        ExtraArgs={
            "ContentType": "application/octet-stream",
            "CacheControl": "public, max-age=31536000, immutable",
        },
    )

    print(f"[*] Uploading {latest_key}...")
    client.upload_file(
        file_path,
        bucket,
        latest_key,
        ExtraArgs={
            "ContentType": "application/octet-stream",
            "CacheControl": "public, max-age=300",
        },
    )

    if checksums_path and os.path.isfile(checksums_path):
        print(f"[*] Uploading {checksums_key}...")
        client.upload_file(
            checksums_path,
            bucket,
            checksums_key,
            ExtraArgs={
                "ContentType": "text/plain; charset=utf-8",
                "CacheControl": "public, max-age=3600",
            },
        )

    base_url = public_base_url.strip().rstrip("/")
    versioned_url = f"{base_url}/{versioned_key}" if base_url else ""
    latest_url = f"{base_url}/{latest_key}" if base_url else ""

    manifest = {
        "version": tag,
        "filename": safe_name,
        "size_bytes": size_bytes,
        "sha256": sha256.upper(),
        "download_url": versioned_url,
        "latest_url": latest_url,
        "virustotal_url": f"https://www.virustotal.com/gui/file/{sha256.lower()}",
        "released_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")

    print(f"[*] Uploading {manifest_key}...")
    client.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=manifest_bytes,
        ContentType="application/json; charset=utf-8",
        CacheControl="public, max-age=60",
    )

    if github_output:
        with open(github_output, "a", encoding="utf-8") as out:
            out.write(f"download_url={versioned_url}\n")
            out.write(f"latest_url={latest_url}\n")

    print("[OK] Cloudflare R2 upload completed successfully!")
    if versioned_url:
        print(f"     Versioned URL: {versioned_url}")
        print(f"     Latest URL:    {latest_url}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload release artifacts to Cloudflare R2 via boto3")
    parser.add_argument("--file", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--checksums", default="dist/SHA256SUMS.txt")
    parser.add_argument("--bucket", default=os.environ.get("R2_BUCKET", "ai-plus-releases"))
    args = parser.parse_args()

    sys.exit(
        upload_release(
            file_path=args.file,
            tag=args.tag,
            sha256=args.sha256,
            checksums_path=args.checksums,
            bucket=args.bucket or "ai-plus-releases",
            endpoint=os.environ.get("R2_ENDPOINT", ""),
            access_key=os.environ.get("R2_ACCESS_KEY_ID", ""),
            secret_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
            public_base_url=os.environ.get("R2_PUBLIC_BASE_URL", ""),
            github_output=os.environ.get("GITHUB_OUTPUT", ""),
        )
    )
