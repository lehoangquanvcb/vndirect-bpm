from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'

def _read(name):
    df = pd.read_csv(DATA_DIR / name)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    if 'last_active_date' in df.columns:
        df['last_active_date'] = pd.to_datetime(df['last_active_date'])
    return df

def load_all():
    return {
        'market': _read('market_data.csv'),
        'branch': _read('branch_performance.csv'),
        'pnl': _read('product_pnl.csv'),
        'rm': _read('rm_performance.csv'),
        'customer': _read('customer_behavior.csv'),
        'competitor': _read('competitor_benchmark.csv'),
        'okr': _read('okr_initiatives.csv'),
    }
