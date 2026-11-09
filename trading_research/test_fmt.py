import urllib.request
import re
import json

url = 'https://www.youtube.com/watch?v=OH--4nkbXlM'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Referer': 'https://www.youtube.com/'
}
req = urllib.request.Request(url, headers=headers)
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
m = re.search(r'"captionTracks":\s*(\[.*?\])', html)
tracks = json.loads(m.group(1))
base_url = tracks[0]['baseUrl']

for fmt in ['json3', 'srv1', 'vtt']:
    test_url = base_url + f'&fmt={fmt}'
    try:
        r = urllib.request.Request(test_url, headers=headers)
        data = urllib.request.urlopen(r).read().decode('utf-8')
        print(f"Success with fmt={fmt}! Length: {len(data)}")
        break
    except Exception as e:
        print(f"Failed fmt={fmt}: {e}")
