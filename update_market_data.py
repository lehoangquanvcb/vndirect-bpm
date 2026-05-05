import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def get_vnindex_history(days=180):
    from vnstock import Vnstock

    end = datetime.today()
    start = end - timedelta(days=days)

    stock = Vnstock().stock(symbol="VNINDEX", source="VCI")
    df = stock.quote.history(
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1D"
    )

    df = df.rename(columns={
        "time": "date",
        "close": "vnindex",
        "volume": "volume",
        "value": "trading_value",
        "trading_value": "trading_value",
        "match_value": "trading_value",
        "transaction_value": "trading_value",
    })

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    if "trading_value" in df.columns:
        df["market_liquidity"] = pd.to_numeric(df["trading_value"], errors="coerce")
        df["liquidity_source"] = "trading_value"
    elif "volume" in df.columns:
        df["market_liquidity"] = pd.to_numeric(df["volume"], errors="coerce")
        df["liquidity_source"] = "volume_proxy"
    else:
        df["market_liquidity"] = None
        df["liquidity_source"] = "not_available"

    keep_cols = ["date", "vnindex", "market_liquidity", "liquidity_source"]

    if "volume" in df.columns:
        keep_cols.append("volume")
    if "trading_value" in df.columns:
        keep_cols.append("trading_value")

    return df[keep_cols]

if __name__ == "__main__":
    df = get_vnindex_history(days=180)
    out = DATA_DIR / "market_data_real.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Saved: {out}")
    print(f"Rows: {len(df)}")
    print(f"Last date: {df['date'].max()}")