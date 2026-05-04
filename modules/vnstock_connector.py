"""vnstock market data connector for VNDIRECT BPM dashboard.

What is real from vnstock/public market data:
- VNINDEX / index history if vnstock returns it
- Listed securities price, volume and estimated traded value
- Broker stock performance for listed brokerage tickers

What is NOT available directly from vnstock:
- Official brokerage market share by firm
- Internal margin balance by firm
- Internal client/RM/branch performance
These should remain manual/internal-data inputs and must be labelled clearly.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd


INDEX_SYMBOLS = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"]
BROKER_TICKERS = ["VND", "SSI", "VCI", "HCM", "MBS", "VIX", "SHS", "FTS", "BSI", "CTS"]


def _date_range(days: int) -> tuple[str, str]:
    end = datetime.today()
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _standardize_history(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize different vnstock versions to one schema."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]

    rename_map = {
        "time": "date",
        "date": "date",
        "trading_date": "date",
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
    }
    out = out.rename(columns={c: rename_map.get(c, c) for c in out.columns})

    if "date" not in out.columns or "close" not in out.columns:
        raise ValueError(f"vnstock data missing date/close for {symbol}. Columns={list(out.columns)}")

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume", "trading_value"]:
        if col in out.columns:
            out[col] = _safe_numeric(out[col])

    if "volume" not in out.columns:
        out["volume"] = 0

    # If vnstock does not provide traded value for listed stocks, estimate close * volume.
    # For indices, close is an index point, so this is only a volume proxy and NOT value traded.
    if "trading_value" not in out.columns:
        if symbol.upper() in INDEX_SYMBOLS:
            out["trading_value"] = pd.NA
            out["liquidity_source"] = "volume_proxy"
        else:
            out["trading_value"] = out["close"] * out["volume"]
            out["liquidity_source"] = "estimated_close_x_volume"
    else:
        out["liquidity_source"] = "real_trading_value"

    out["symbol"] = symbol.upper()
    out = out.dropna(subset=["date", "close"]).sort_values("date")

    keep = ["date", "symbol", "open", "high", "low", "close", "volume", "trading_value", "liquidity_source"]
    for col in keep:
        if col not in out.columns:
            out[col] = pd.NA
    return out[keep]


def get_symbol_history(symbol: str, days: int = 180, source: str = "VCI") -> Optional[pd.DataFrame]:
    """Fetch one symbol from vnstock. Returns None if vnstock/API fails."""
    try:
        from vnstock import Vnstock

        start, end = _date_range(days)
        stock = Vnstock().stock(symbol=symbol.upper(), source=source)
        raw = stock.quote.history(start=start, end=end, interval="1D")
        out = _standardize_history(raw, symbol=symbol)
        return out if not out.empty else None
    except Exception as exc:
        print(f"vnstock error for {symbol}: {exc}")
        return None


def get_vnindex_history(days: int = 180) -> Optional[pd.DataFrame]:
    """Return VNINDEX history with columns expected by existing app."""
    df = get_symbol_history("VNINDEX", days=days)
    if df is None or df.empty:
        return None

    out = df.rename(columns={"close": "vnindex"}).copy()
    out["market_liquidity"] = out["trading_value"]
    if out["market_liquidity"].isna().all():
        out["market_liquidity"] = out["volume"]
    return out[["date", "vnindex", "volume", "trading_value", "market_liquidity", "liquidity_source"]]


def get_market_liquidity(days: int = 180) -> Optional[pd.DataFrame]:
    """Return liquidity series. Prefer real trading_value; otherwise volume proxy."""
    df = get_vnindex_history(days=days)
    if df is None or df.empty:
        return None
    return df[["date", "market_liquidity", "liquidity_source"]]


def get_market_liquidity_with_source(days: int = 180) -> Tuple[Optional[pd.DataFrame], str]:
    df = get_market_liquidity(days=days)
    if df is None or df.empty:
        return None, "fallback_demo"
    source = df["liquidity_source"].dropna().iloc[-1] if "liquidity_source" in df.columns and not df["liquidity_source"].dropna().empty else "unknown"
    return df, str(source)


def get_indices_history(symbols: Iterable[str] = INDEX_SYMBOLS, days: int = 180) -> pd.DataFrame:
    frames = []
    for symbol in symbols:
        df = get_symbol_history(symbol, days=days)
        if df is not None and not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "close", "volume", "trading_value", "liquidity_source"])
    return pd.concat(frames, ignore_index=True)


def get_broker_stock_panel(tickers: Iterable[str] = BROKER_TICKERS, days: int = 180) -> pd.DataFrame:
    """Listed brokerage stocks performance panel, based on public market prices."""
    rows = []
    for ticker in tickers:
        df = get_symbol_history(ticker, days=days)
        if df is None or df.empty:
            continue
        x = df.dropna(subset=["close"]).sort_values("date").copy()
        if x.empty:
            continue
        latest = x.iloc[-1]
        first = x.iloc[0]
        # Approx 1M / 3M lookback by trading observations.
        p_1m = x.iloc[-22]["close"] if len(x) >= 22 else first["close"]
        p_3m = x.iloc[-66]["close"] if len(x) >= 66 else first["close"]
        ret_1m = (latest["close"] / p_1m - 1) * 100 if p_1m else None
        ret_3m = (latest["close"] / p_3m - 1) * 100 if p_3m else None
        ret_period = (latest["close"] / first["close"] - 1) * 100 if first["close"] else None
        trading_value = latest.get("trading_value", pd.NA)
        rows.append(
            {
                "ticker": ticker.upper(),
                "last_date": latest["date"],
                "last_price": latest["close"],
                "volume": latest.get("volume", pd.NA),
                "trading_value_bil_vnd": trading_value / 1_000_000_000 if pd.notna(trading_value) else pd.NA,
                "return_1m_pct": ret_1m,
                "return_3m_pct": ret_3m,
                "return_period_pct": ret_period,
                "liquidity_source": latest.get("liquidity_source", "unknown"),
            }
        )
    return pd.DataFrame(rows)


def get_full_market_pack(days: int = 180) -> Dict[str, pd.DataFrame | str]:
    """One-call market pack for Streamlit.

    Returns:
    - vnindex_df: VNINDEX time series
    - liquidity_df: liquidity/proxy time series
    - indices_df: VNINDEX/VN30/HNXINDEX/UPCOMINDEX if available
    - broker_panel: public listed broker stock performance
    - source_note: human-readable source description
    """
    vnindex_df = get_vnindex_history(days=days)
    liquidity_df, liquidity_source = get_market_liquidity_with_source(days=days)
    indices_df = get_indices_history(days=days)
    broker_panel = get_broker_stock_panel(days=days)

    if vnindex_df is None or vnindex_df.empty:
        source_note = "Không lấy được vnstock; app nên fallback về CSV demo."
    elif liquidity_source == "real_trading_value":
        source_note = "VNINDEX và liquidity lấy từ vnstock; liquidity dùng trading_value nếu API trả về."
    elif liquidity_source == "estimated_close_x_volume":
        source_note = "VNINDEX lấy từ vnstock; liquidity của cổ phiếu là ước tính close x volume."
    else:
        source_note = "VNINDEX lấy từ vnstock; liquidity đang là volume proxy vì API không trả về trading_value."

    return {
        "vnindex_df": vnindex_df if vnindex_df is not None else pd.DataFrame(),
        "liquidity_df": liquidity_df if liquidity_df is not None else pd.DataFrame(),
        "indices_df": indices_df,
        "broker_panel": broker_panel,
        "liquidity_source": liquidity_source,
        "source_note": source_note,
    }
