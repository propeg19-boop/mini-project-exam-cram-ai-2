import os
import requests

SERPAPI_KEY = os.getenv('SERPAPI_KEY', '')

def fetch_images(topic):
    """Fetch diagram images for a topic via SerpAPI Google Images."""
    if not SERPAPI_KEY or not topic:
        return _fallback_images(topic)

    try:
        query = f"{topic} diagram labeled"
        url = "https://serpapi.com/search.json"
        params = {
            'engine': 'google_images',
            'q': query,
            'api_key': SERPAPI_KEY,
            'num': 10
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        images = []
        for img in data.get('images_results', [])[:3]:
            img_url = img.get('original') or img.get('thumbnail')
            if img_url and img_url.startswith('http'):
                images.append(img_url)

        if len(images) >= 3:
            return images
        return images + _fallback_images(topic)[len(images):]

    except Exception as e:
        print(f'[ImageFetchError: {str(e)}]')
        return _fallback_images(topic)

def _fallback_images(topic):
    """Return placeholder images when SerpAPI fails."""
    safe_topic = topic[:25].replace(' ', '+')
    return [
        f'https://placehold.co/400x250/1a1a2e/8b5cf6?text={safe_topic}+Diagram+1',
        f'https://placehold.co/400x250/1a1a2e/06b6d4?text={safe_topic}+Diagram+2',
        f'https://placehold.co/400x250/1a1a2e/ec4899?text={safe_topic}+Diagram+3'
    ]
