import json
import os
import urllib.request
import urllib.parse
import concurrent.futures
import zipfile
import re
import mimetypes

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

base_dir = "/Users/apple/.gemini/antigravity/scratch/celebmaker-gallery"
out_dir = os.path.join(base_dir, "downloaded_media")
os.makedirs(out_dir, exist_ok=True)

with open(os.path.join(base_dir, "valid_media.json")) as f:
    items = json.load(f)

# Category folder names (slugified for filesystem safety)
cat_slugs = {
    'Vídeos & Animações': 'videos',
    'Face Swap & Demonstrações': 'face_swap',
    'Modelos & Influencers': 'modelos',
    'Banners & Destaques': 'banners',
    'Logos & Ícones': 'logos',
    'Edições & Previews': 'edicoes',
    'Galeria Geral': 'geral'
}

for slug in cat_slugs.values():
    os.makedirs(os.path.join(out_dir, slug), exist_ok=True)

downloaded_items = []
used_filenames = set()

def get_filename(url, content_type, idx):
    # Parse path from URL
    parsed = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed.path)
    
    # If no filename or generic, create one
    if not filename or len(filename) < 3 or filename == 'w=1024,q=100' or filename == 'w=2048,q=100':
        ext = '.webp'
        if 'video' in content_type:
            ext = '.mp4'
        elif 'png' in content_type:
            ext = '.png'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            ext = '.jpg'
        elif 'svg' in content_type:
            ext = '.svg'
        filename = f"media_{idx:03d}{ext}"
    else:
        # Sanitize filename
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        # Ensure has proper extension
        if '.' not in filename:
            ext = mimetypes.guess_extension(content_type) or '.webp'
            filename += ext

    return filename

def download_one(idx, item):
    url = item['url']
    cat = item['category']
    folder = cat_slugs.get(cat, 'geral')
    fname = get_filename(url, item['content_type'], idx)
    
    # Disambiguate if needed
    base, ext = os.path.splitext(fname)
    candidate_fname = f"{idx:03d}_{fname}"
    file_path = os.path.join(out_dir, folder, candidate_fname)
    rel_path = f"downloaded_media/{folder}/{candidate_fname}"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            size_bytes = len(content)
            return {
                'id': idx,
                'title': base.replace('_', ' ').replace('-', ' ').title(),
                'filename': candidate_fname,
                'category': cat,
                'folder': folder,
                'type': item['type'],
                'url': url,
                'local_path': file_path,
                'rel_path': rel_path,
                'size_bytes': size_bytes,
                'size_formatted': f"{size_bytes / (1024 * 1024):.2f} MB" if size_bytes >= 1048576 else f"{size_bytes / 1024:.1f} KB"
            }
    except Exception as e:
        print(f"Failed [{idx}] {url}: {e}")
        return None

print(f"Starting parallel download of {len(items)} files...")
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
    futures = [executor.submit(download_one, i+1, item) for i, item in enumerate(items)]
    for f in concurrent.futures.as_completed(futures):
        res = f.result()
        if res:
            downloaded_items.append(res)

print(f"Successfully downloaded {len(downloaded_items)} files.")

# Sort by id
downloaded_items.sort(key=lambda x: x['id'])

# Save manifest
manifest_path = os.path.join(base_dir, "media_manifest.json")
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(downloaded_items, f, indent=2, ensure_ascii=False)
print("Saved media_manifest.json")

# Create complete ZIP archive for instant 1-click download of all files
zip_file_path = os.path.join(base_dir, "celebmaker_todas_as_midias.zip")
print(f"Packaging all files into ZIP: {zip_file_path}...")

with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for item in downloaded_items:
        archive_name = os.path.join(item['folder'], item['filename'])
        zipf.write(item['local_path'], arcname=archive_name)

zip_size = os.path.getsize(zip_file_path)
print(f"ZIP created successfully! Total size: {zip_size / (1024*1024):.2f} MB")
