import pandas as pd
import yfinance as yf

# Download Oct 22 to Oct 23 to get Asian / London sessions
df = yf.download('GC=F', start='2026-10-22', end='2026-10-24', interval='5m')
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# Check Asian range on Oct 23: 00:00 to 06:00
asian = df.loc['2026-10-23 00:00:00-04:00':'2026-10-23 05:00:00-04:00']
london = df.loc['2026-10-23 05:00:00-04:00':'2026-10-23 08:30:00-04:00']

print(f"Asian High: {asian['High'].max():.2f}, Asian Low: {asian['Low'].min():.2f}")
print(f"London High: {london['High'].max():.2f}, London Low: {london['Low'].min():.2f}")

ny = df.loc['2026-10-23 08:30:00-04:00':'2026-10-23 11:30:00-04:00']
print("\n--- NY Session 5m ---")
for idx, row in ny.iterrows():
    print(f"{idx.strftime('%H:%M')}: O={row['Open']:.2f}, H={row['High']:.2f}, L={row['Low']:.2f}, C={row['Close']:.2f}")
