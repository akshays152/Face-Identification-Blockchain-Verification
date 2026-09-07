"""
part1/post_extractor.py
-------------------------
Step 5: Candidate Post Extractor (Part 1)

For candidate search results, collects and canonicalizes:
  - post_url
  - post_image (downloads remote images to local cache for inspection & hashing)
  - post_text
  - metadata (platform, author, timestamp, tags)

Prepares normalized candidate posts for face comparison and handoff.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Safe UTF-8 output on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

CACHE_DIR = _ROOT / "data" / "cache"

logger = logging.getLogger("post_extractor")


class PostExtractor:
    """
    Extracts and downloads candidate post content into a canonical, local format.
    """

    def __init__(self, cache_dir: Path = CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 FaceVerification/1.0"
            )
        })

    def download_image(self, url: str) -> Optional[Path]:
        """
        Downloads a remote image to the local cache directory.
        Uses a hash of the URL as filename to avoid duplicates and collisions.
        """
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        ext = ".jpg"
        clean_url = url.split("?")[0].lower()
        for potential_ext in [".png", ".webp", ".jpeg", ".jpg"]:
            if clean_url.endswith(potential_ext):
                ext = potential_ext
                break

        target_path = self.cache_dir / f"candidate_{url_hash}{ext}"
        if target_path.is_file() and target_path.stat().st_size > 0:
            return target_path

        try:
            try:
                resp = self.session.get(url, timeout=12, stream=True)
            except requests.exceptions.SSLError:
                resp = self.session.get(url, timeout=12, stream=True, verify=False)

            resp.raise_for_status()
            content = resp.content
            if len(content) < 500:
                return None
            target_path.write_bytes(content)
            return target_path
        except Exception as exc:
            logger.debug(f"Failed to download candidate image from {url}: {exc}")
            return None

    def extract_post(self, raw_candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalizes a single candidate post and ensures its image is locally accessible.
        """
        raw_img = raw_candidate.get("post_image", "").strip()
        if not raw_img:
            return None

        local_img_path: Optional[str] = None

        if raw_img.startswith(("http://", "https://")):
            downloaded = self.download_image(raw_img)
            if downloaded and downloaded.is_file():
                local_img_path = str(downloaded.resolve())
            else:
                local_img_path = raw_img
        else:
            p = Path(raw_img)
            if not p.is_absolute():
                p = _ROOT / p
            if p.is_file():
                local_img_path = str(p.resolve())
            else:
                local_img_path = raw_img

        return {
            "post_url": raw_candidate.get("post_url", "").strip(),
            "post_image": local_img_path,
            "post_text": raw_candidate.get("post_text", "").strip(),
            "metadata": raw_candidate.get("metadata", {}),
        }

    def extract_all(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes and normalizes a list of candidate search results."""
        extracted = []
        for cand in candidates:
            item = self.extract_post(cand)
            if item:
                extracted.append(item)
        return extracted


def extract_candidate_posts(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Functional interface for Part 1 pipeline."""
    extractor = PostExtractor()
    return extractor.extract_all(candidates)


if __name__ == "__main__":
    from part1.web_search import search_web_and_social
    print("[3] Searching web/social media...")
    candidates = search_web_and_social("portrait")
    print(f"[✓] Search completed ({len(candidates)} candidates found)")

    print("[5] Extracting candidate posts...")
    results = extract_candidate_posts(candidates[:3])
    print(f"[✓] Extracted {len(results)} candidate post(s)")
    for i, res in enumerate(results, 1):
        print(f"  [{i}] URL:   {res['post_url']}")
        print(f"      Image: {res['post_image']}")
        print(f"      Text:  {res['post_text'][:50]}...")
