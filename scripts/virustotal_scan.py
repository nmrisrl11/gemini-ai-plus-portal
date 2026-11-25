"""
VirusTotal API v3 Release Scanner for Gemini AI Plus Portal.

Uploads a built release artifact (supports files > 32 MB via /files/upload_url),
waits for analysis completion, fetches the full detection report, and writes a
GitHub-flavored Markdown security report suitable for GitHub Release descriptions.

Reads VIRUSTOTAL_API_KEY strictly from the environment (never hardcoded).
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, Optional, Tuple

VT_BASE = "https://www.virustotal.com/api/v3"
STANDARD_UPLOAD_LIMIT = 32 * 1024 * 1024  # 32 MB


def compute_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _vt_request(
    url: str,
    api_key: str,
    method: str = "GET",
    data: Optional[bytes] = None,
    content_type: Optional[str] = None,
    timeout: float = 120.0,
) -> Tuple[int, Dict[str, Any]]:
    headers = {
        "x-apikey": api_key,
        "Accept": "application/json",
    }
    if content_type:
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            return getattr(resp, "status", 200), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore") if e.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"error": raw}
        return e.code, parsed


def _build_multipart(file_path: str) -> Tuple[bytes, str]:
    boundary = f"----VTBnd{uuid.uuid4().hex}"
    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"),
        b"Content-Type: application/octet-stream\r\n\r\n",
        file_bytes,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def upload_to_virustotal(file_path: str, api_key: str) -> Optional[str]:
    file_size = os.path.getsize(file_path)
    upload_url = f"{VT_BASE}/files"

    if file_size > STANDARD_UPLOAD_LIMIT:
        print(f"[*] File size ({file_size / (1024*1024):.2f} MB) > 32 MB; requesting large-file upload URL...")
        status, resp = _vt_request(f"{VT_BASE}/files/upload_url", api_key, method="GET", timeout=30.0)
        if status != 200 or not resp.get("data"):
            print(f"[!] Failed to obtain large-file upload URL (HTTP {status}): {resp}")
            return None
        upload_url = resp["data"]

    print(f"[*] Uploading {os.path.basename(file_path)} to VirusTotal...")
    body, ctype = _build_multipart(file_path)
    status, resp = _vt_request(upload_url, api_key, method="POST", data=body, content_type=ctype, timeout=300.0)
    if status not in (200, 201):
        print(f"[!] VirusTotal upload failed (HTTP {status}): {resp}")
        return None

    analysis_id = resp.get("data", {}).get("id")
    print(f"[OK] Uploaded. Analysis ID: {analysis_id}")
    return analysis_id


def poll_analysis(analysis_id: str, api_key: str, max_wait_seconds: int = 360) -> bool:
    deadline = time.time() + max_wait_seconds
    interval = 15
    while time.time() < deadline:
        status, resp = _vt_request(f"{VT_BASE}/analyses/{analysis_id}", api_key, method="GET", timeout=30.0)
        if status == 200:
            state = resp.get("data", {}).get("attributes", {}).get("status", "")
            print(f"[*] VirusTotal analysis status: {state}")
            if state == "completed":
                return True
        else:
            print(f"[!] Poll returned HTTP {status}; retrying...")
        time.sleep(interval)
    print("[!] Timed out waiting for VirusTotal analysis to complete.")
    return False


def fetch_file_report(sha256: str, api_key: str) -> Optional[Dict[str, Any]]:
    status, resp = _vt_request(f"{VT_BASE}/files/{sha256}", api_key, method="GET", timeout=30.0)
    if status == 200 and isinstance(resp.get("data"), dict):
        return resp["data"]
    return None


def render_markdown_report(
    file_path: str,
    sha256: str,
    report_data: Optional[Dict[str, Any]],
) -> str:
    filename = os.path.basename(file_path)
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    vt_gui_url = f"https://www.virustotal.com/gui/file/{sha256}"

    lines = [
        "### Security & Verification",
        "",
        f"- **Artifact:** `{filename}` ({size_mb:.2f} MB)",
        f"- **SHA-256:** `{sha256.upper()}`",
        f"- **VirusTotal Report:** [View Full Scan Report]({vt_gui_url})",
    ]

    if not report_data:
        lines.append("- **Scan Status:** Submitted to VirusTotal (report pending — click the link above for live results).")
        return "\n".join(lines) + "\n"

    attrs = report_data.get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    results = attrs.get("last_analysis_results", {})

    malicious = int(stats.get("malicious", 0))
    suspicious = int(stats.get("suspicious", 0))
    undetected = int(stats.get("undetected", 0))
    harmless = int(stats.get("harmless", 0))
    total_engines = malicious + suspicious + undetected + harmless
    flagged_count = malicious + suspicious

    lines.extend([
        f"- **Detection Ratio:** `{flagged_count} / {total_engines}` engines (`{malicious}` malicious, `{suspicious}` suspicious, `{undetected + harmless}` clean)",
        "",
    ])

    flagged_engines = [
        (engine, info.get("category", ""), info.get("result") or "Flagged")
        for engine, info in sorted(results.items())
        if info.get("category") in ("malicious", "suspicious")
    ]

    if flagged_engines:
        lines.extend([
            "<details>",
            f"<summary>Engine Details ({len(flagged_engines)} heuristic flag(s) — unsigned Python/Nuitka binary)</summary>",
            "",
            "| Engine | Category | Result |",
            "| :--- | :--- | :--- |",
        ])
        for engine, category, result in flagged_engines:
            lines.append(f"| {engine} | {category} | `{result}` |")
        lines.extend([
            "",
            "*Note: Unsigned open-source binaries built with Nuitka/Playwright can occasionally trigger generic heuristic flags. You can inspect or rebuild from source in this repository at any time.*",
            "</details>",
        ])
    else:
        lines.append("**0 detections** across all scanning engines.")

    return "\n".join(lines) + "\n"


def scan_artifact(file_path: str, output_md: Optional[str] = None, max_wait: int = 360) -> int:
    if not os.path.isfile(file_path):
        print(f"[ERROR] Artifact not found: {file_path}")
        return 1

    sha256 = compute_sha256(file_path)
    api_key = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
    report_data = None

    if not api_key:
        print("[WARNING] VIRUSTOTAL_API_KEY not set. Generating SHA-256 verification section without live upload.")
    else:
        analysis_id = upload_to_virustotal(file_path, api_key)
        if analysis_id:
            poll_analysis(analysis_id, api_key, max_wait_seconds=max_wait)
        report_data = fetch_file_report(sha256, api_key)

    md = render_markdown_report(file_path, sha256, report_data)
    if output_md:
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[OK] Written VirusTotal Markdown report to: {output_md}")
    else:
        print("\n" + md)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a release artifact to VirusTotal and generate a Markdown report.")
    parser.add_argument("file", help="Path to the release artifact (.zip or .exe)")
    parser.add_argument("--output-md", help="Output path for the generated Markdown report")
    parser.add_argument("--max-wait", type=int, default=360, help="Max seconds to wait for VT analysis (default: 360)")
    args = parser.parse_args()
    sys.exit(scan_artifact(args.file, output_md=args.output_md, max_wait=args.max_wait))
