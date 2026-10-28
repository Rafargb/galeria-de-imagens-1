import json
import urllib.request
import concurrent.futures
import os
import mimetypes
import hashlib

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

with open('/Users/apple/.gemini/antigravity/scratch/celebmaker-gallery/discovered_media.json') as f:
    data = json.load(f)

media_urls = data['media_urls']
video_candidates = data['video_candidates']

all_candidates = set(media_urls + video_candidates)
print(f"Total candidate URLs to check: {len(all_candidates)}")

valid_media = []

def check_url(url):
    # filter out obvious non-media
    if url.endswith('.js') or url.endswith('.css') or url.endswith('.json') or url.endswith('.html'):
        return None
    req = urllib.request.Request(url, headers=headers, method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            content_type = resp.headers.get('Content-Type', '')
            content_length = resp.headers.get('Content-Length', '0')
            if resp.status == 200 and ('image' in content_type or 'video' in content_type or 'audio' in content_type or 'octet-stream' in content_type):
                return {
                    'url': url,
                    'content_type': content_type,
                    'size': int(content_length) if content_length.isdigit() else 0,
                    'status': resp.status
                }
    except Exception:
        # Some servers don't like HEAD, try GET with range: bytes=0-1024
        try:
            req_get = urllib.request.Request(url, headers={**headers, 'Range': 'bytes=0-1024'})
            with urllib.request.urlopen(req_get, timeout=8) as resp:
                content_type = resp.headers.get('Content-Type', '')
                content_length = resp.headers.get('Content-Length', '0')
                if resp.status in (200, 206) and ('image' in content_type or 'video' in content_type or 'audio' in content_type):
                    return {
                        'url': url,
                        'content_type': content_type,
                        'size': int(content_length) if content_length.isdigit() else 0,
                        'status': resp.status
                    }
        except Exception:
            pass
    return None

print("Checking candidate URLs for validity...")
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
    futures = {executor.submit(check_url, u): u for u in all_candidates}
    for f in concurrent.futures.as_completed(futures):
        res = f.result()
        if res:
            valid_media.append(res)

print(f"Total confirmed live media items: {len(valid_media)}")

# Categorize media items
for item in valid_media:
    u = item['url']
    ct = item['content_type']
    if 'video' in ct or u.endswith('.mp4') or u.endswith('.webm'):
        item['category'] = 'Vídeos & Animações'
        item['type'] = 'video'
    elif 'face-swap' in u:
        item['category'] = 'Face Swap & Demonstrações'
        item['type'] = 'image'
    elif 'zit-showcase' in u or 'eden' in u or 'katya-x-hart' in u:
        item['category'] = 'Modelos & Influencers'
        item['type'] = 'image'
    elif 'home-banners' in u or 'banners' in u:
        item['category'] = 'Banners & Destaques'
        item['type'] = 'image'
    elif 'logo' in u or 'icon' in u or 'favicon' in u or u.endswith('.svg'):
        item['category'] = 'Logos & Ícones'
        item['type'] = 'image'
    elif 'image-edit' in u or 'posters' in u:
        item['category'] = 'Edições & Previews'
        item['type'] = 'image'
    else:
        item['category'] = 'Galeria Geral'
        item['type'] = 'image'

with open('/Users/apple/.gemini/antigravity/scratch/celebmaker-gallery/valid_media.json', 'w') as f:
    json.dump(valid_media, f, indent=2)

print("Saved valid_media.json")
