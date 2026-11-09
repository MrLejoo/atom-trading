import json
import os
import time
from youtube_transcript_api import YouTubeTranscriptApi

ytt = YouTubeTranscriptApi()

playlists = [
    ('bootcamp_2', 'e:/Gravi/trading_research/bootcamp_2_meta.json'),
    ('fede_esses', 'e:/Gravi/trading_research/fede_esses_meta.json'),
    ('trading_strategies', 'e:/Gravi/trading_research/trading_strategies_meta.json')
]

out_base = 'e:/Gravi/trading_research/transcripts'
os.makedirs(out_base, exist_ok=True)

stats = {}

for pl_name, meta_file in playlists:
    print(f"\n=================== Processing {pl_name} ===================")
    pl_dir = os.path.join(out_base, pl_name)
    os.makedirs(pl_dir, exist_ok=True)
    
    with open(meta_file, 'r', encoding='utf-8') as f:
        videos = json.load(f)
        
    stats[pl_name] = {'total': len(videos), 'success': 0, 'failed': 0, 'items': []}
    
    for idx, v in enumerate(videos):
        vid = v.get('id')
        title = v.get('title') or f"Video_{idx+1}"
        if not vid:
            print(f"[{idx+1}/{len(videos)}] Skipping video without ID: {title}")
            continue
            
        txt_path = os.path.join(pl_dir, f"{idx+1:02d}_{vid}.json")
        if os.path.exists(txt_path):
            print(f"[{idx+1}/{len(videos)}] ALREADY EXISTS: {title} ({vid})")
            stats[pl_name]['success'] += 1
            continue
            
        print(f"[{idx+1}/{len(videos)}] Fetching: {title} ({vid})...", end='', flush=True)
        try:
            tl = ytt.list(vid)
            # Try to get Spanish directly or translated
            chosen_transcript = None
            lang_used = None
            
            # Check if Spanish transcript directly exists
            try:
                chosen_transcript = tl.find_transcript(['es', 'es-US', 'es-419', 'es-ES'])
                lang_used = chosen_transcript.language_code
            except:
                pass
                
            if not chosen_transcript:
                # Fallback to English or any available and translate if needed
                try:
                    chosen_transcript = tl.find_transcript(['en', 'en-US'])
                    lang_used = chosen_transcript.language_code
                    # If translatable to Spanish, translate it!
                    if chosen_transcript.is_translatable:
                        chosen_transcript = chosen_transcript.translate('es')
                        lang_used = 'es (translated from en)'
                except:
                    pass
                    
            if not chosen_transcript:
                # Just take the first available
                for t in tl:
                    chosen_transcript = t
                    lang_used = t.language_code
                    if t.is_translatable:
                        chosen_transcript = t.translate('es')
                        lang_used = f"es (translated from {t.language_code})"
                    break
                    
            if chosen_transcript:
                data = chosen_transcript.fetch()
                # Extract text and duration
                full_text = ' '.join([s.text for s in data])
                record = {
                    'index': idx + 1,
                    'id': vid,
                    'title': title,
                    'lang': lang_used,
                    'snippets_count': len(data),
                    'text': full_text,
                    'snippets': [{'start': s.start, 'duration': s.duration, 'text': s.text} for s in data]
                }
                with open(txt_path, 'w', encoding='utf-8') as out_f:
                    json.dump(record, out_f, ensure_ascii=False, indent=2)
                print(f" SUCCESS ({lang_used}, {len(full_text)} chars)")
                stats[pl_name]['success'] += 1
            else:
                print(" NO TRANSCRIPT AVAILABLE")
                stats[pl_name]['failed'] += 1
        except Exception as e:
            print(f" ERROR: {str(e)[:80]}")
            stats[pl_name]['failed'] += 1
            
        time.sleep(0.5)

print("\n\n=================== SUMMARY ===================")
for k, v in stats.items():
    print(f"{k}: {v['success']}/{v['total']} successful, {v['failed']} failed")
