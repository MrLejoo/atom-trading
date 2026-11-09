import glob
import json

def inspect():
    for pl in ['bootcamp_2', 'trading_strategies']:
        files = sorted(glob.glob(f'e:/Gravi/trading_research/transcripts/{pl}/*.json'))
        print(f"\n==================== {pl} ====================")
        for f in files:
            with open(f, encoding='utf-8') as jf:
                d = json.load(jf)
                print(f"--- {d.get('index')}: {d.get('title')} ---")
                text = d.get('text', '')
                # Print key topics or sentences
                sample = text[:300].strip()
                print(f"Sample: {sample}...\n")

if __name__ == '__main__':
    inspect()
