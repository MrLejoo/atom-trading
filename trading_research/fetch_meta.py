import subprocess
import json
import os

playlists = {
    'bootcamp_2': 'https://www.youtube.com/playlist?list=PLKE_22Jx497u8rJX1n6Yq20ROA_A2HrWt',
    'fede_esses': 'https://www.youtube.com/playlist?list=PL4hId-DTkHg50047_yeFJOvPK1rOCrSoR',
    'trading_strategies': 'https://www.youtube.com/playlist?list=PL3wdfj84a2fl8TbxIpdjD7MhfSDRbdGzK'
}

os.makedirs('e:/Gravi/trading_research', exist_ok=True)

for name, url in playlists.items():
    print(f"=== Fetching metadata for {name} ===")
    cmd = ['yt-dlp', '--flat-playlist', '-J', url]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if res.returncode == 0:
        data = json.loads(res.stdout)
        entries = data.get('entries', [])
        title = data.get('title', '')
        print(f"{name}: {len(entries)} videos found. Playlist title: {title}")
        for idx, e in enumerate(entries):
            print(f"  {idx+1}. {e.get('title')} ({e.get('id')})")
        with open(f'e:/Gravi/trading_research/{name}_meta.json', 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    else:
        print(f"Error fetching {name}: {res.stderr[:200]}")
