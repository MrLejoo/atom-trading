import glob
import json

for pl in ['bootcamp_2', 'fede_esses', 'trading_strategies']:
    files = sorted(glob.glob(f'e:/Gravi/trading_research/transcripts/{pl}/*.json'))
    print(f"\n=== {pl} ({len(files)} files) ===")
    for f in files:
        with open(f, encoding='utf-8') as jf:
            d = json.load(jf)
            idx = d.get('index', 0)
            vid = d.get('id', '')
            length = d.get('length', 0)
            title = d.get('title', '')
            print(f"  {idx:02d} | {vid} | {length:6d} chars | {title[:40]}")
