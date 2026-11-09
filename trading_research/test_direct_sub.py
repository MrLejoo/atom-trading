import urllib.request
import re
import json

url = 'https://www.youtube.com/watch?v=OH--4nkbXlM'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"HTML len: {len(html)}")
        match = re.search(r'"captionTracks":\s*(\[.*?\])', html)
        if match:
            print("Found captionTracks directly!")
            tracks = json.loads(match.group(1))
            for t in tracks:
                print(t.get('languageCode'), t.get('name'), t.get('baseUrl')[:80])
        else:
            print("No captionTracks found directly.")
            # Check if ytInitialPlayerResponse exists
            m2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
            if m2:
                print("Found ytInitialPlayerResponse!")
            else:
                print("No ytInitialPlayerResponse found.")
except Exception as e:
    print(f"Error: {e}")
