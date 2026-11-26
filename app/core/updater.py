"""
Lightweight, non-blocking release update checker for Gemini AI Plus Portal.
Checks the Cloudflare R2 latest.json manifest first (zero API rate limits) and
falls back to the public GitHub Releases API if needed.
Uses only Python's standard library and fails silently when offline.
"""

import json
import re
import urllib.request
from typing import Dict, Optional, Tuple

from app.config import (
    APP_NAME,
    APP_VERSION,
    DOWNLOAD_PAGE_URL,
    RELEASES_API_URL,
    SERVICE_STATUS_URL,
    UPDATE_MANIFEST_URL,
)


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


def _fetch_json(url: str, current_version: str, timeout: float) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/vnd.github+json",
            "Cache-Control": "no-cache",
            "User-Agent": f"{APP_NAME}/{current_version}",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if getattr(resp, "status", 200) != 200:
            return None
        payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    return payload if isinstance(payload, dict) else None


def check_service_status(
    status_url: str = SERVICE_STATUS_URL,
    current_version: str = APP_VERSION,
    timeout: float = 4.0,
) -> Optional[Dict[str, object]]:
    """
    Fetches the remote Cloudflare R2 status.json switch.
    Returns a dict {'status', 'title', 'message', 'disable_actions'} when status
    is 'paused' or 'notice'. Fails open (returns None) when status is 'active',
    missing (404), or unreachable.
    """
    if not status_url:
        return None
    try:
        payload = _fetch_json(status_url, current_version, timeout)
        if not payload:
            return None

        state = str(payload.get("status") or "active").strip().lower()
        if state not in ("paused", "notice"):
            return None

        default_title = (
            "Promotion Temporarily Paused" if state == "paused" else "Service Notice"
        )
        default_msg = (
            "The promotional gateway is temporarily paused due to high demand. "
            "Provisioning is disabled so you do not waste your Gmail account. Please check back later."
            if state == "paused"
            else "The promotional gateway is currently experiencing delays."
        )
        disable_actions = bool(
            payload.get("disable_actions", state == "paused")
        )
        return {
            "status": state,
            "title": str(payload.get("title") or default_title).strip(),
            "message": str(payload.get("message") or default_msg).strip(),
            "disable_actions": disable_actions,
        }
    except Exception:
        return None


def check_for_update(
    current_version: str = APP_VERSION,
    manifest_url: str = UPDATE_MANIFEST_URL,
    api_url: str = RELEASES_API_URL,
    download_url: str = DOWNLOAD_PAGE_URL,
    timeout: float = 4.0,
) -> Optional[Dict[str, str]]:
    """
    Checks for a newer published release using Cloudflare R2 latest.json first,
    falling back to the GitHub Releases API.
    Returns {'latest_version', 'download_url'} if a newer release exists, else None.
    Never raises on network, HTTP, or parsing errors.
    """
    # 1. Primary: Cloudflare R2 latest.json manifest (no API rate limits)
    if manifest_url:
        try:
            payload = _fetch_json(manifest_url, current_version, timeout)
            if payload:
                latest_tag = str(payload.get("version") or payload.get("tag_name") or "").strip()
                if latest_tag:
                    if is_newer_version(latest_tag, current_version):
                        target_url = download_url or str(payload.get("download_url") or "")
                        return {
                            "latest_version": latest_tag,
                            "download_url": target_url,
                        }
                    return None
        except Exception:
            pass

    # 2. Fallback: Public GitHub Releases API
    if api_url:
        try:
            payload = _fetch_json(api_url, current_version, timeout)
            if payload and not (payload.get("draft") or payload.get("prerelease")):
                latest_tag = str(payload.get("tag_name") or "").strip()
                if latest_tag and is_newer_version(latest_tag, current_version):
                    target_url = download_url or str(payload.get("html_url") or "")
                    return {
                        "latest_version": latest_tag,
                        "download_url": target_url,
                    }
        except Exception:
            return None
    return None
