"""
blockchain/hash_generator.py
----------------------------
Deterministic SHA-256 fingerprinting of social/web post data.

The canonicalization strategy guarantees that identical logical data
always produces exactly the same hash, regardless of Python dictionary
ordering or whitespace variations.

Pipeline
--------
1.  Normalise each field (strip, lower-case URLs, sort metadata keys).
2.  If ``post_image`` points to a readable local file -> SHA-256 its bytes.
    If it is a URL -> attempt to download, then SHA-256.
    On failure -> record a clear marker so the caller knows.
3.  Build a canonical pipe-delimited string.
4.  SHA-256 the canonical string.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import requests


# -----------------------------------------------
#  Image hashing
# -----------------------------------------------

def hash_image(path_or_url: str) -> dict[str, str]:
    """
    Compute the SHA-256 of an image from a local path or URL.

    Returns
    -------
    dict with keys:
        ``sha256``  - hex digest on success, empty string on failure
        ``status``  - ``"ok"`` | ``"unavailable"``
        ``detail``  - human-readable explanation
    """
    if not path_or_url or not path_or_url.strip():
        return {
            "sha256": "",
            "status": "unavailable",
            "detail": "No image path/URL provided.",
        }

    path_or_url = path_or_url.strip()

    # ---- Local file ----
    if not path_or_url.startswith(("http://", "https://")):
        p = Path(path_or_url)
        if not p.is_absolute():
            # Try relative to CWD
            p = Path.cwd() / p
        if p.is_file():
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            return {"sha256": sha, "status": "ok", "detail": f"Local file: {p}"}
        return {
            "sha256": "",
            "status": "unavailable",
            "detail": f"Local file not found: {path_or_url}",
        }

    # ---- URL ----
    try:
        resp = requests.get(path_or_url, timeout=15, stream=True)
        resp.raise_for_status()
        h = hashlib.sha256()
        for chunk in resp.iter_content(8192):
            h.update(chunk)
        return {"sha256": h.hexdigest(), "status": "ok", "detail": f"URL: {path_or_url}"}
    except Exception as exc:
        return {
            "sha256": "",
            "status": "unavailable",
            "detail": f"Could not download image: {exc}",
        }


# -----------------------------------------------
#  Canonicalization
# -----------------------------------------------

def _normalize_url(url: str | None) -> str:
    """Strip and lower-case a URL (or return empty string)."""
    if not url:
        return ""
    return url.strip().lower().rstrip("/")


def _normalize_text(text: str | None) -> str:
    """Strip leading/trailing whitespace; collapse inner runs."""
    if not text:
        return ""
    return " ".join(text.strip().split())


def _normalize_metadata(meta: Any) -> str:
    """
    Convert metadata to a deterministic JSON string.
    Handles dict, list, string, number, and None.
    """
    if meta is None:
        return ""
    if isinstance(meta, str):
        return meta.strip()
    # For any JSON-serialisable structure, sort keys for determinism.
    return json.dumps(meta, sort_keys=True, separators=(",", ":"))


def canonicalize(post_data: dict) -> str:
    """
    Build a deterministic canonical string from post data.

    Format (pipe-delimited):
        url|image_ref|text|metadata

    ``image_ref`` is the SHA-256 of the image bytes when available,
    otherwise the raw ``post_image`` value (normalised) so that the
    fingerprint still covers it.
    """
    url = _normalize_url(post_data.get("post_url"))
    text = _normalize_text(post_data.get("post_text"))
    meta = _normalize_metadata(post_data.get("metadata"))

    # Image reference - prefer file/URL hash, fall back to raw value.
    raw_image = (post_data.get("post_image") or "").strip()
    img_result = hash_image(raw_image)
    image_ref = img_result["sha256"] if img_result["status"] == "ok" else raw_image.lower()

    return f"{url}|{image_ref}|{text}|{meta}"


# -----------------------------------------------
#  Fingerprint generation
# -----------------------------------------------

def generate_fingerprint(post_data: dict) -> dict:
    """
    Generate a SHA-256 fingerprint of the post data.

    Returns
    -------
    dict with keys:
        ``canonical_data`` - the deterministic string that was hashed
        ``sha256``         - hex-encoded SHA-256 digest
        ``image_info``     - result of image hashing (status, detail)
    """
    canonical = canonicalize(post_data)
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    img_info = hash_image((post_data.get("post_image") or "").strip())
    return {
        "canonical_data": canonical,
        "sha256": sha,
        "image_info": {
            "status": img_info["status"],
            "detail": img_info["detail"],
        },
    }
