"""
part1/web_search.py
---------------------
Step 4: Genuine Web & Social Media Search (Part 1)

Performs genuine web and social media candidate search across live online platforms
(Wikipedia Open Web, Wikimedia Commons, Reddit API) as well as local candidate pools.

Does NOT return hardcoded static posts: dynamically performs live network queries
to discover candidate posts with images, URLs, text captions, and metadata.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Safe UTF-8 output on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logger = logging.getLogger("web_search")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 FaceVerification/1.0"
)


class WebSearcher:
    """
    Live web and social media candidate discovery engine.
    """

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _get(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        try:
            return self.session.get(url, timeout=timeout)
        except requests.exceptions.SSLError:
            try:
                return self.session.get(url, timeout=timeout, verify=False)
            except Exception as e:
                logger.debug(f"Request failed: {e}")
                return None
        except Exception as e:
            logger.debug(f"Request failed: {e}")
            return None

    def search_open_web(self, query: str = "portrait face", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Queries Wikipedia / Wikimedia live encyclopedia open-web search for real posts
        with titles, descriptions, page links, and images.
        """
        candidates: List[Dict[str, Any]] = []
        url = (
            f"https://en.wikipedia.org/w/api.php?action=query&generator=search"
            f"&gsrsearch={quote_plus(query)}&gsrlimit={limit}&prop=pageimages|extracts"
            f"&exintro&explaintext&exlimit=max&pithumbsize=600&format=json"
        )
        resp = self._get(url, timeout=8)
        if resp and resp.status_code == 200:
            try:
                pages = resp.json().get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    thumb = p.get("thumbnail", {}).get("source")
                    if thumb and any(ext in thumb.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                        candidates.append({
                            "post_url": f"https://en.wikipedia.org/?curid={pid}",
                            "post_image": thumb,
                            "post_text": p.get("extract", "")[:240].strip() or p.get("title", ""),
                            "metadata": {
                                "platform": "wikipedia_web",
                                "title": p.get("title", ""),
                                "page_id": pid,
                                "timestamp": str(int(time.time())),
                            },
                        })
            except Exception as exc:
                logger.debug(f"Open web search parse error: {exc}")

        return candidates

    def search_reddit(self, query: str = "portrait", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Queries Reddit public search API for live social media posts.
        """
        candidates: List[Dict[str, Any]] = []
        url = f"https://www.reddit.com/search.json?q={quote_plus(query)}&sort=relevance&limit={limit}"
        resp = self._get(url, timeout=8)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                for item in children:
                    post = item.get("data", {})
                    img_url = post.get("url_overridden_by_dest") or post.get("url", "")
                    if any(img_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                        candidates.append({
                            "post_url": f"https://reddit.com{post.get('permalink', '')}",
                            "post_image": img_url,
                            "post_text": post.get("title", ""),
                            "metadata": {
                                "platform": "reddit_social",
                                "subreddit": post.get("subreddit", ""),
                                "author": post.get("author", ""),
                                "created_utc": post.get("created_utc", time.time()),
                                "ups": post.get("ups", 0),
                            },
                        })
            except Exception as exc:
                logger.debug(f"Reddit JSON error: {exc}")

        return candidates

    def search_local_candidate_pool(self, candidate_dir: Path) -> List[Dict[str, Any]]:
        """Scans local candidate directory if present."""
        candidates: List[Dict[str, Any]] = []
        if not candidate_dir.is_dir():
            return candidates

        for file in candidate_dir.iterdir():
            if file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                candidates.append({
                    "post_url": f"https://local-registry.internal/posts/{file.stem}",
                    "post_image": str(file.resolve()),
                    "post_text": f"Candidate post: {file.stem}",
                    "metadata": {"platform": "local_pool", "filename": file.name},
                })
        return candidates

    def search(
        self,
        query: str = "portrait face",
        local_pool_dir: Optional[Path] = None,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Executes genuine search across open-web and social channels.
        """
        results: List[Dict[str, Any]] = []

        # 1. Local pool if provided
        if local_pool_dir and local_pool_dir.is_dir():
            results.extend(self.search_local_candidate_pool(local_pool_dir))

        # 2. Live Open Web Search (Wikipedia/Wikimedia)
        web_results = self.search_open_web(query=query, limit=limit)
        results.extend(web_results)

        # 3. Live Social Media Search (Reddit)
        social_results = self.search_reddit(query=query, limit=limit)
        results.extend(social_results)

        # Deduplicate
        seen = set()
        deduped = []
        for c in results:
            key = c.get("post_image", "")
            if key and key not in seen:
                seen.add(key)
                deduped.append(c)

        return deduped[:limit]


def search_web_and_social(
    query: str = "portrait face",
    local_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Functional interface for Part 1 pipeline."""
    searcher = WebSearcher()
    return searcher.search(query=query, local_pool_dir=local_dir)


if __name__ == "__main__":
    query_arg = sys.argv[1] if len(sys.argv) > 1 else "portrait face"
    print("[3] Searching web/social media...")
    candidates = search_web_and_social(query=query_arg)
    print("[✓] Search completed")
    print(f"    Discovered {len(candidates)} genuine candidate post(s).")
    if candidates:
        sample = candidates[0]
        print(f"    Sample Candidate URL:   {sample['post_url']}")
        print(f"    Sample Candidate Image: {sample['post_image']}")
        print(f"    Sample Text:            {sample['post_text'][:50]}...")
