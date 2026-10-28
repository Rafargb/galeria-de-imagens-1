import urllib.request
import urllib.parse
import re
import json
import concurrent.futures
import time

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

def fetch_url(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return url, resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return url, ""

# 1. Get sitemap
req = urllib.request.Request("https://celebmakerai.com/sitemap.xml", headers=headers)
sitemap_xml = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
urls = re.findall(r'<loc>(https://celebmakerai\.com[^<]*)</loc>', sitemap_xml)
print(f"Total URLs in sitemap: {len(urls)}")

# Let's fetch pages in parallel
pages = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(fetch_url, u): u for u in urls}
    for f in concurrent.futures.as_completed(futures):
        u, content = f.result()
        if content:
            pages[u] = content

print(f"Successfully fetched {len(pages)} pages.")

# Extract all media items
media_found = set()

for page_url, html in pages.items():
    # Find all direct links to media files (mp4, webm, webp, png, jpg, jpeg, gif, svg)
    # Also find next/image urls
    for m in re.finditer(r'(/_next/image\?url=[^"\'\s&<>]+)', html):
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(m.group(1)).query)
        if 'url' in parsed:
            raw_url = parsed['url'][0]
            if raw_url.startswith('/'):
                media_found.add("https://celebmakerai.com" + raw_url)
            else:
                media_found.add(raw_url)

    # All CDN matches and generic image/video extensions
    for m in re.finditer(r'https?://[^\s"\'<>]+\.(?:mp4|webm|webp|png|jpg|jpeg|gif|svg|avif)', html, re.IGNORECASE):
        media_found.add(m.group(0))

    # Also check JSON strings inside Next.js data scripts
    for m in re.finditer(r'https?://cdn\.celebmakerai\.com/[^\s"\'\\]+', html):
        cleaned = m.group(0).rstrip('\\').rstrip('"').rstrip("'")
        media_found.add(cleaned)

# Also check if video previews exist by checking common video folders or patterns
print(f"Found {len(media_found)} raw candidate media items.")

# Clean up URLs:
# 1) If it has /cdn-cgi/image/..., we can extract the base url
clean_media = {}
for m in media_found:
    # unescape json if needed
    m = m.replace('\\/', '/')
    # remove trailing punctuations
    m = m.rstrip('.,;)"\'')
    
    # Check if it's a cdn-cgi transformed image
    match_cgi = re.search(r'https?://cdn\.celebmakerai\.com/cdn-cgi/image/[^/]+/(.+)', m)
    if match_cgi:
        high_res = f"https://cdn.celebmakerai.com/{match_cgi.group(1)}"
        orig_key = match_cgi.group(1)
        clean_media[orig_key] = high_res
    else:
        clean_media[m] = m

print(f"Found {len(clean_media)} deduplicated high-res media items.")

# Check video extensions or possible video files for any posters
possible_videos = set()
for url in clean_media.values():
    if '/posters/' in url:
        # e.g. /video-action-previews/katya-x-hart/imperial-indigo/v4/posters/missionary.webp
        # could have a video in /videos/ or without posters:
        v1 = url.replace('/posters/', '/videos/').replace('.webp', '.mp4')
        v2 = url.replace('/posters/', '/').replace('.webp', '.mp4')
        possible_videos.add(v1)
        possible_videos.add(v2)

print(f"Generated {len(possible_videos)} video candidates to test.")

# Let's write the results so far to a JSON file
with open('/Users/apple/.gemini/antigravity/scratch/celebmaker-gallery/discovered_media.json', 'w') as f:
    json.dump({
        'pages_crawled': len(pages),
        'media_urls': list(clean_media.values()),
        'video_candidates': list(possible_videos)
    }, f, indent=2)

print("Saved discovered_media.json")
