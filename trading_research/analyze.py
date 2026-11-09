# Analysis Script to extract structured data for the Comprehensive PDF
import glob
import json
import os

def analyze_corpus():
    data = {
        'bootcamp_2': [],
        'fede_esses': [],
        'trading_strategies': []
    }
    
    for pl in data.keys():
        files = sorted(glob.glob(f'e:/Gravi/trading_research/transcripts/{pl}/*.json'))
        for f in files:
            with open(f, encoding='utf-8') as jf:
                d = json.load(jf)
                data[pl].append({
                    'index': d.get('index'),
                    'title': d.get('title'),
                    'id': d.get('id'),
                    'length': d.get('length'),
                    'text': d.get('text')
                })
    return data

if __name__ == '__main__':
    d = analyze_corpus()
    print("Corpus loaded successfully:")
    for k, v in d.items():
        print(f"  {k}: {len(v)} videos")
