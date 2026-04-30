"""
image_fetcher.py — SerpAPI Google Images integration
Returns up to 3 valid image URLs for a given topic.
"""

import os
import re
import requests

SERPAPI_BASE = "https://serpapi.com/search.json"

# Fallback images if SerpAPI fails or returns nothing useful
FALLBACK_IMAGES = [
    "https://placehold.co/640x400/13131f/9333ea?text=Diagram+Not+Found",
    "https://placehold.co/640x400/13131f/06b6d4?text=No+Image+Available",
    "https://placehold.co/640x400/13131f/ec4899?text=Search+Unavailable",
]


def _is_valid_url(url: str) -> bool:
    """Basic check that a URL looks usable."""
    return isinstance(url, str) and url.startswith("http") and len(url) > 20


def fetch_images(topic: str) -> list[str]:
    """
    Search SerpAPI for images of the given topic.
    Returns a list of up to 3 image URLs.
    Falls back to placeholder images on any failure.
    """
    api_key = os.getenv("SERPAPI_KEY", "")
    if not api_key:
        print("[Images] SERPAPI_KEY not set — returning fallbacks")
        return FALLBACK_IMAGES

    # Build a search query that targets educational diagrams
    query = f"{topic} diagram labeled"

    params = {
        "engine":  "google_images",
        "q":       query,
        "api_key": api_key,
        "num":     10,          # fetch more than needed so we can filter
        "safe":    "active",    # keep results clean
    }

    try:
        print(f"[Images] Searching SerpAPI for: {query}")
        resp = requests.get(SERPAPI_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("images_results", [])
        if not results:
            print("[Images] No results from SerpAPI — using fallbacks")
            return FALLBACK_IMAGES

        # Extract valid "original" URLs
        valid_urls = []
        for item in results:
            url = item.get("original", "")
            if _is_valid_url(url) and len(valid_urls) < 3:
                valid_urls.append(url)

        if not valid_urls:
            print("[Images] Filtered to 0 valid URLs — using fallbacks")
            return FALLBACK_IMAGES

        # Pad with fallbacks if fewer than 3 valid results
        while len(valid_urls) < 3:
            valid_urls.append(FALLBACK_IMAGES[len(valid_urls)])

        print(f"[Images] Returning {len(valid_urls)} images")
        return valid_urls

    except requests.exceptions.Timeout:
        print("[Images] SerpAPI request timed out — using fallbacks")
        return FALLBACK_IMAGES
    except requests.exceptions.RequestException as e:
        print(f"[Images] SerpAPI request failed: {e} — using fallbacks")
        return FALLBACK_IMAGES
    except Exception as e:
        print(f"[Images] Unexpected error: {e} — using fallbacks")
        return FALLBACK_IMAGES
