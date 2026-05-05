"""Fast, defensive vnstock connector for VNDIRECT BPM dashboard.

Design principle:
- Do NOT call vnstock automatically on every Streamlit rerun.
- app.py should call these functions only after user clicks Refresh, with st.cache_data.
- If vnstock is slow or unavailable, return None so the app can fallback to local/demo data.

What can be public/live from vnstock:
- VNINDEX/index OHLC and volume, if the vnstock API returns it.
- Sometimes trading value/liquidity, depending on vnstock version/source.

What is NOT available directly from vnstock:
- Official brokerage market share by firm.
- Internal margin balance by brokerage firm.
- Customer/RM/branch performance.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd


INDEX_SYMBOLS = {"VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"}


def _date_range(days: int) -> tuple[str, str]:
    end = datetime.today()
    start = end - timedelta(days=int(days))
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _standardize_history(raw: pd.DataFrame, symbol: str = "VNINDEX") -> pd.DataFrame:
    """Normalize different vnstock outputs to a stable schema."""
    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    rename_map = {
        "time": "date",
        "trading_date": "date",
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "value": "trading_value",
        "trading_value": "trading_value",
        "match_value": "trading_value",
        "transaction_value": "trading_value",
        "total_value": "trading_value",
        "value_trade": "trading_value",
        "matched_value": "trading_value",
    }
    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError(f"vnstock data missing date/close for {symbol}. Columns={list(df.columns)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = _to_numeric(df, ["open", "high", "low", "close", "volume", "trading_value"])

    if "volume" not in df.columns:
        df["volume"] = pd.NA

    symbol_upper = symbol.upper()
    if "trading_value" in df.columns and df["trading_value"].notna().any():
        df["market_liquidity"] = df["trading_value"]
        df["liquidity_source"] = "real_trading_value"
    elif symbol_upper in INDEX_SYMBOLS:
        # For an index, close * volume is not true trading value. Use volume only as proxy.
        df["trading_value"] = pd.NA
        df["market_liquidity"] = df["volume"]
        df["liquidity_source"] = "volume_proxy"
    else:
        # For listed stocks, close x volume is only an estimate if real value is missing.
        df["trading_value"] = df["close"] * df["volume"]
        df["market_liquidity"] = df["trading_value"]
        df["liquidity_source"] = "estimated_close_x_volume"

    df["symbol"] = symbol_upper
    df = df.dropna(subset=["date", "close"]).sort_values("date")

    keep = [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trading_value",
        "market_liquidity",
        "liquidity_source",
    ]
    for col in keep:
        if col not in df.columns:
            df[col] = pd.NA
    return df[keep]


def get_symbol_history(symbol: str = "VNINDEX", days: int = 90, source: str = "VCI") -> Optional[pd.DataFrame]:
    """Fetch one symbol from vnstock. Returns None on any error."""
    try:
        from vnstock import Vnstock

        start, end = _date_range(days)
        stock = Vnstock().stock(symbol=symbol.upper(), source=source)
        raw = stock.quote.history(start=start, end=end, interval="1D")
        df = _standardize_history(raw, symbol=symbol)
        return df if not df.empty else None
    except Exception as exc:
        print(f"vnstock error for {symbol}: {exc}")
        return None


def get_vnindex_history(days: int = 90) -> Optional[pd.DataFrame]:
    """Return VNINDEX history with columns expected by the app."""
    df = get_symbol_history("VNINDEX", days=days, source="VCI")
    if df is None or df.empty:
        return None

    out = df.rename(columns={"close": "vnindex"}).copy()
    return out[["date", "vnindex", "volume", "trading_value", "market_liquidity", "liquidity_source"]]


def get_market_liquidity(days: int = 90) -> Tuple[Optional[pd.DataFrame], str]:
    """Return liquidity dataframe and source label.

    Source labels:
    - real_trading_value: vnstock returned traded value.
    - volume_proxy: vnstock returned only volume for index; not true value traded.
    - fallback_demo: API failed; app should use local CSV/demo.
    """
    df = get_vnindex_history(days=days)
    if df is None or df.empty:
        return None, "fallback_demo"

    source = "unknown"
    if "liquidity_source" in df.columns and df["liquidity_source"].notna().any():
        source = str(df["liquidity_source"].dropna().iloc[-1])

    out = df[["date", "market_liquidity"]].copy()
    return out, source
