"""Market data connector.
Default mode uses local demo CSV so the app deploys immediately.
Set use_live=True to try vnstock for VNINDEX when environment supports it.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


def get_vnindex_live_or_demo(use_live: bool = False) -> pd.DataFrame:
    if not use_live:
        return pd.read_csv(DATA_DIR / 'market_data.csv', parse_dates=['date'])
    try:
        # vnstock APIs change across versions; keep this defensive.
        from vnstock import Vnstock
        stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
        df = stock.quote.history(start='2025-01-01', end=pd.Timestamp.today().strftime('%Y-%m-%d'))
        rename = {'time': 'date', 'close': 'vnindex', 'volume': 'market_liquidity_bil_vnd'}
        df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        if 'market_liquidity_bil_vnd' in df.columns:
            df['market_liquidity_bil_vnd'] = df['market_liquidity_bil_vnd'] / 1_000_000
        for col in ['market_margin_bil_vnd', 'market_share_pct']:
            if col not in df.columns:
                df[col] = None
        return df[['date','vnindex','market_liquidity_bil_vnd','market_margin_bil_vnd','market_share_pct']].dropna(subset=['date'])
    except Exception:
        return pd.read_csv(DATA_DIR / 'market_data.csv', parse_dates=['date'])
