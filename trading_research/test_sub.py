import subprocess
import json
import os
import glob
import re

def clean_vtt(vtt_text):
    lines = vtt_text.splitlines()
    cleaned = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '-->' in line:
            continue
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        # Remove HTML-like tags (e.g. <c>, </c>, <00:00:01.000>)
        line = re.sub(r'<[^>]+>', '', line).strip()
        if not line:
            continue
        # Deduplicate consecutive identical lines
        if cleaned and cleaned[-1] == line:
            continue
        cleaned.append(line)
    return ' '.join(cleaned)

def download_subtitles(video_id, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    txt_path = os.path.join(output_dir, f"{video_id}.txt")
    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
        return True, "Already exists"

    url = f"https://www.youtube.com/watch?v=f{video_id}"
    base_out = os.path.join(output_dir, video_id)
    cmd = [
        'yt-dlp',
        '--skip-download',
        '--write-sub',
        '--write-auto-sub',
        '--sub-lang', 'es,en',
        '--sub-format', 'vtt',
        '-o', f"{base_out}.%(ext)s",
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    # Check for downloaded vtt files
    vtt_files = glob.glob(f"{base_out}*.vtt")
    if not vtt_files:
        return False, f"No subtitles found: {res.stderr[:100]}"
    
    # Prefer Spanish, then English
    chosen_vtt = None
    for vf in vtt_files:
        if '.es.' in vf:
            chosen_vtt = vf
            break
    if not chosen_vtt:
        chosen_vtt = vtt_files[0]
        
    with open(chosen_vtt, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    text = clean_vtt(content)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # Clean up vtt files to save space
    for vf in vtt_files:
        try:
            os.remove(vf)
        except:
            pass
            
    return True, f"Saved ({len(text)} chars)"

if __name__ == '__main__':
    # Test on first video of bootcamp_2
    res, msg = download_subtitles('o_SdawM3DIE', 'e:/Gravi/trading_research/test_sub')
    print("Test result:", res, msg)
