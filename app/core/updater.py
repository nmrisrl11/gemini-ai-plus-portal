"""
Lightweight, non-blocking GitHub Releases update checker for Gemini AI Plus Portal.
Uses only Python's standard library and fails silently when offline or rate-limited.
"""

import json
import re
import urllib.request
from typing import Dict, Optional, Tuple

from app.config import APP_NAME, APP_VERSION, DOWNLOAD_PAGE_URL, RELEASES_API_URL


def parse_semver(version_str: str) -> Tuple[int, ...]:
    """Parses a version tag like 'v1.0.2' or '1.2.0-beta' into an integer tuple."""
    if not version_str:
        return (0, 0, 0)
    match = re.search(r"(\d+(?:\.\d+)*)", str(version_str).strip())
    if not match:
        return (0, 0, 0)
    parts = [int(p) for p in match.group(1).split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(latest_tag: str, current_tag: str = APP_VERSION) -> bool:
    """Returns True if latest_tag represents a strictly newer version than current_tag."""
    return parse_semver(latest_tag) > parse_semver(current_tag)


def check_for_update(
    current_version: str = APP_VERSION,
    api_url: str = RELEASES_API_URL,
    download_url: str = DOWNLOAD_PAGE_URL,
    timeout: float = 4.0,
) -> Optional[Dict[str, str]]:
    """
    Queries the public GitHub Releases API for the latest published release.
    Returns a dict with {'latest_version', 'download_url'} if a newer release exists,
    otherwise returns None. Never raises on network, HTTP, or parsing errors.
    """
    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"{APP_NAME}/{current_version}",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                return None
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))

        if not isinstance(payload, dict):
            return None
        if payload.get("draft") or payload.get("prerelease"):
            return None

        latest_tag = str(payload.get("tag_name") or "").strip()
        if not latest_tag:
            return None

        if is_newer_version(latest_tag, current_version):
            target_url = download_url or str(payload.get("html_url") or "")
            return {
                "latest_version": latest_tag,
                "download_url": target_url,
            }
    except Exception:
        return None
    return None
