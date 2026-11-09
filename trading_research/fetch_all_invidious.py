import json
import os
import re
import time
import urllib.request

INVIDIOUS_API = 'https://yt.chocolatemoo53.com'

playlists = [
    ('bootcamp_2', 'e:/Gravi/trading_research/bootcamp_2_meta.json'),
    ('fede_esses', 'e:/Gravi/trading_research/fede_esses_meta.json'),
    ('trading_strategies', 'e:/Gravi/trading_research/trading_strategies_meta.json')
]

out_base = 'e:/Gravi/trading_research/transcripts'
os.makedirs(out_base, exist_ok=True)

def clean_vtt(vtt_text):
    lines = vtt_text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '-->' in line:
            continue
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        line = re.sub(r'<[^>]+>', '', line).strip()
        if not line:
            continue
        # Avoid immediate duplicate consecutive words/lines
        if cleaned and cleaned[-1] == line:
            continue
        cleaned.append(line)
    return ' '.join(cleaned)

def fetch_via_invidious(vid, title):
    url = f"{INVIDIOUS_API}/api/v1/videos/{vid}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
            captions = data.get('captions', [])
            if not captions:
                return False, "No captions in video data", None, None
                
            # Prefer Spanish if available, else first caption
            chosen = None
            for c in captions:
                lbl = (c.get('label') or '').lower()
                if 'spanish' in lbl or 'español' in lbl or 'es' in lbl:
                    chosen = c
                    break
            if not chosen:
                chosen = captions[0]
                
            sub_url = INVIDIOUS_API + chosen['url']
            sub_req = urllib.request.Request(sub_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(sub_req, timeout=10) as sresp:
                raw_vtt = sresp.read().decode('utf-8', errors='ignore')
                
            text = clean_vtt(raw_vtt)
            lang_label = chosen.get('label', 'unknown')
            return True, "OK", text, lang_label
        except Exception as e:
            time.sleep(2 * (attempt + 1))
            last_err = str(e)
            
    return False, f"Failed after 3 attempts: {last_err}", None, None

stats = {}

for pl_name, meta_file in playlists:
    print(f"\n=================== Processing {pl_name} ===================")
    pl_dir = os.path.join(out_base, pl_name)
    os.makedirs(pl_dir, exist_ok=True)
    
    with open(meta_file, 'r', encoding='utf-8') as f:
        videos = json.load(f)
        
    stats[pl_name] = {'total': len(videos), 'success': 0, 'failed': 0}
    
    for idx, v in enumerate(videos):
        vid = v.get('id')
        title = v.get('title') or f"Video_{idx+1}"
        if not vid:
            print(f"[{idx+1}/{len(videos)}] Skipping video without ID: {title}")
            continue
            
        json_path = os.path.join(pl_dir, f"{idx+1:02d}_{vid}.json")
        if os.path.exists(json_path) and os.path.getsize(json_path) > 200:
            print(f"[{idx+1}/{len(videos)}] ALREADY EXISTS: {title} ({vid})")
            stats[pl_name]['success'] += 1
            continue
            
        print(f"[{idx+1}/{len(videos)}] Fetching: {title} ({vid})...", end='', flush=True)
        ok, msg, text, lang = fetch_via_invidious(vid, title)
        
        if ok and text and len(text) > 50:
            record = {
                'index': idx + 1,
                'id': vid,
                'title': title,
                'lang': lang,
                'length': len(text),
                'text': text
            }
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(record, jf, ensure_ascii=False, indent=2)
            print(f" SUCCESS ({lang}, {len(text)} chars)")
            stats[pl_name]['success'] += 1
        else:
            print(f" FAILED: {msg}")
            stats[pl_name]['failed'] += 1
            
        time.sleep(1)

print("\n\n=================== OVERALL SUMMARY ===================")
for k, v in stats.items():
    print(f"{k}: {v['success']}/{v['total']} successful, {v['failed']} failed")
