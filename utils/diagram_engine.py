"""
Diagram Engine — fetches labeled diagram images using SerpAPI (Google Images).
Always returns 3 image URLs. Falls back to placeholder images on failure.
"""

import os
import requests

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
SERPAPI_URL = "https://serpapi.com/search.json"

PLACEHOLDER_IMAGES = [
    "https://placehold.co/600x400/111114/8B5CF6?text=Diagram+Loading",
    "https://placehold.co/600x400/111114/EC4899?text=Visual+Aid",
    "https://placehold.co/600x400/111114/F97316?text=Reference+Image",
]


def get_diagrams(query: str) -> list[str]:
    """
    Fetch 3 diagram image URLs for the given query.
    Returns a list of 3 URLs (real or placeholder).
    """
    if not SERPAPI_KEY:
        return PLACEHOLDER_IMAGES

    try:
        return _serpapi_search(query)
    except Exception:
        return PLACEHOLDER_IMAGES


def _serpapi_search(query: str) -> list[str]:
    """Call SerpAPI Google Images endpoint."""
    params = {
        "engine": "google_images",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 5,
        "safe": "active",
    }

    response = requests.get(SERPAPI_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    images_raw = data.get("images_results", [])
    urls = []

    for img in images_raw:
        original = img.get("original") or img.get("thumbnail")
        if original and original.startswith("http"):
            urls.append(original)
        if len(urls) >= 3:
            break

    # Pad with placeholders if fewer than 3 results
    while len(urls) < 3:
        urls.append(PLACEHOLDER_IMAGES[len(urls) % len(PLACEHOLDER_IMAGES)])

    return urls[:3]
