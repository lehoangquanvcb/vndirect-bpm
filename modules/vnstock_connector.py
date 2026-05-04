import pandas as pd
from datetime import datetime, timedelta


def _standardize_vnstock_history(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa output từ vnstock về các cột: date, vnindex, volume, market_liquidity."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "vnindex", "volume", "market_liquidity"])

    out = df.copy()

    # Một số version vnstock trả về time, một số trả về date
    rename_map = {}
    if "time" in out.columns:
        rename_map["time"] = "date"
    if "close" in out.columns:
        rename_map["close"] = "vnindex"
    if "volume" in out.columns:
        rename_map["volume"] = "volume"

    out = out.rename(columns=rename_map)

    required = ["date", "vnindex"]
    for col in required:
        if col not in out.columns:
            raise ValueError(f"vnstock data missing required column: {col}. Columns={list(out.columns)}")

    if "volume" not in out.columns:
        out["volume"] = 0

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["vnindex"] = pd.to_numeric(out["vnindex"], errors="coerce")
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0)

    out = out.dropna(subset=["date", "vnindex"]).sort_values("date")
    out["market_liquidity"] = out["volume"]

    return out[["date", "vnindex", "volume", "market_liquidity"]]


def get_vnindex_history(days: int = 180) -> pd.DataFrame | None:
    """
    Lấy dữ liệu VNINDEX từ vnstock.
    Nếu lỗi, trả về None để app fallback sang dữ liệu demo.
    """
    try:
        from vnstock import Vnstock

        end = datetime.today()
        start = end - timedelta(days=days)

        stock = Vnstock().stock(symbol="VNINDEX", source="VCI")
        df = stock.quote.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1D",
        )

        out = _standardize_vnstock_history(df)
        if out.empty:
            return None
        return out

    except Exception as e:
        print("VNINDEX vnstock error:", e)
        return None


def get_market_liquidity(days: int = 180) -> pd.DataFrame | None:
    """
    Tạm lấy volume VNINDEX làm proxy thanh khoản thị trường.
    Lưu ý: đây là proxy kỹ thuật; nếu có dữ liệu giá trị giao dịch toàn thị trường thì nên thay bằng nguồn chính thức.
    """
    df = get_vnindex_history(days=days)
    if df is None or df.empty:
        return None

    out = df.copy()
    return out[["date", "market_liquidity"]]
