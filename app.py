import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="VNDIRECT BPM", layout="wide")

st.title("📊 Market & Competitor Benchmark")

# =====================
# LOAD MARKET DATA (REAL CSV FIRST)
# =====================
real_market_path = "data/market_data_real.csv"

if os.path.exists(real_market_path):
    vnindex_df = pd.read_csv(real_market_path)
    vnindex_df["date"] = pd.to_datetime(vnindex_df["date"])
    liquidity_df = vnindex_df.copy()
    data_source = "real_csv"
else:
    vnindex_df = pd.read_csv("data/market_data.csv")
    vnindex_df["date"] = pd.to_datetime(vnindex_df["date"])
    liquidity_df = vnindex_df.copy()
    data_source = "demo_fallback"

# =====================
# SIDEBAR INFO
# =====================
with st.sidebar:
    st.header("⚙️ Control Panel")

    if data_source == "real_csv":
        st.success("✅ Market data: REAL (vnstock → CSV)")
    else:
        st.warning("⚠️ Market data: DEMO fallback")

    st.info(f"📅 Last data date: {vnindex_df['date'].max().date()}")

    st.divider()
    st.markdown("### 💡 Cách cập nhật dữ liệu")
    st.markdown("""
1. Chạy file `update_market_data.py`
2. Commit & push CSV
3. Streamlit tự cập nhật
""")

# =====================
# VNINDEX CHART
# =====================
st.subheader("VNINDEX")

fig_vnindex = px.line(
    vnindex_df,
    x="date",
    y="vnindex",
    title="VNINDEX"
)

st.plotly_chart(fig_vnindex, use_container_width=True)

# =====================
# MARKET LIQUIDITY
# =====================
st.subheader("Market Liquidity")

if "market_liquidity" in liquidity_df.columns:
    y_col = "market_liquidity"
else:
    y_col = "volume" if "volume" in liquidity_df.columns else None

if y_col:
    fig_liq = px.line(
        liquidity_df,
        x="date",
        y=y_col,
        title="Market Liquidity (Trading Value nếu có)"
    )
    st.plotly_chart(fig_liq, use_container_width=True)
else:
    st.warning("Không có dữ liệu liquidity")

# =====================
# NOTE CHO DEMO
# =====================
st.info("""
📌 Giải thích khi demo:
- Dữ liệu VNINDEX và thanh khoản được lấy từ vnstock → lưu thành CSV
- App không gọi API trực tiếp để đảm bảo ổn định khi demo
- Các dữ liệu khác như market share, margin là benchmark demo
""")