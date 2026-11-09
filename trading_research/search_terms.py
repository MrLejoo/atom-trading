import glob
import json

def search_text(term):
    matches = []
    for f in glob.glob('e:/Gravi/trading_research/transcripts/*/*.json'):
        with open(f, encoding='utf-8') as jf:
            d = json.load(jf)
            cnt = d.get('text', '').lower().count(term.lower())
            if cnt > 0:
                pl = f.replace('\\', '/').split('/')[-2]
                matches.append((cnt, d.get('title'), pl))
    matches.sort(reverse=True)
    print(f"\n=== Term: '{term}' (Total files with term: {len(matches)}) ===")
    for cnt, title, pl in matches[:4]:
        print(f"  {cnt:3d} hits: {title[:40]} [{pl}]")

if __name__ == '__main__':
    for term in ['FVG', 'Order Block', 'Liquidity', 'Break and Retest', 'Risk', 'Journal', 'SMT', 'Candlestick', 'Head and Shoulders']:
        search_text(term)
