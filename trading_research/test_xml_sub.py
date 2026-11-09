import urllib.request
import re
import json
import xml.etree.ElementTree as ET
import html as html_lib

url = 'https://www.youtube.com/watch?v=OH--4nkbXlM'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}
req = urllib.request.Request(url, headers=headers)
html_content = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
match = re.search(r'"captionTracks":\s*(\[.*?\])', html_content)
if not match:
    print("No caption tracks found.")
    exit(1)

tracks = json.loads(match.group(1))
base_url = tracks[0]['baseUrl']

# Try auto-translated Spanish
es_url = base_url + '&tlang=es'
es_req = urllib.request.Request(es_url, headers=headers)
es_xml = urllib.request.urlopen(es_req).read().decode('utf-8')
root = ET.fromstring(es_xml)
items = []
for elem in root.findall('.//text'):
    start = float(elem.attrib.get('start', 0))
    dur = float(elem.attrib.get('dur', 0))
    text = html_lib.unescape(elem.text or '')
    if text.strip():
        items.append({'start': start, 'duration': dur, 'text': text.strip()})

print(f"Success! Extracted {len(items)} snippets.")
print("Sample:", " ".join([i['text'] for i in items[:15]]))
