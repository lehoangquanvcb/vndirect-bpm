import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

from modules.data_loader import load_all
from modules.kpi_engine import (
    latest_period_kpis,
    warning_table,
    executive_narrative,
    forecast_series,
    scenario_engine,
    action_engine,
)
from modules.customer_engine import enrich_customers, customer_summary, rm_churn_ranking
from modules.policy_engine import simulate_policy
from modules.report_engine import build_ceo_email, build_interview_story


st.set_page_config(
    page_title="VNDIRECT BPM - AUTHOR: LE HOANG QUAN",
    page_icon="🏆",
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {padding-top: 2.4rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetricValue"] {font-size: 24px;}
.big-title {font-size:30px;font-weight:800; line-height:1.25; margin:0.5rem 0 0.25rem 0; white-space:normal;}
.small-note {color:#6B7280;font-size:13px;}
.card {background:#FFFFFF;border:1px solid #E5E7EB;border-radius:18px;padding:16px;box-shadow:0 3px 14px rgba(0,0,0,0.05);}
.script-box {background:#F8FAFC;border-left:5px solid #2563EB;padding:14px 16px;border-radius:12px;margin:10px 0;}
.warning-box {background:#FFF7ED;border-left:5px solid #F97316;padding:14px 16px;border-radius:12px;margin:10px 0;}
.good-box {background:#F0FDF4;border-left:5px solid #16A34A;padding:14px 16px;border-radius:12px;margin:10px 0;}
</style>
""",
    unsafe_allow_html=True,
)

# Dùng st.title thay vì custom HTML để tránh lỗi bị cắt ký tự trên Streamlit Cloud.
st.title("🏆 VNDIRECT Business Performance Intelligence — AUTHOR: LE HOANG QUAN")
st.caption(
    "Tính năng: CEO dashboard | Customer Intelligence | Policy Simulator | Competitor Benchmark | OKR | CEO Email | Interview Story"
)

with st.sidebar:
    st.header("⚙️ Control Panel")
    # Không gọi vnstock live trên Streamlit Cloud để tránh treo app.
    # Dữ liệu thật được cập nhật offline bằng update_market_data.py -> data/market_data_real.csv.
    view_mode = st.radio("Giao diện", ["PC / Boardroom", "Mobile friendly"], index=0)
    forecast_days = st.slider("Forecast horizon", 7, 90, 30)

    st.divider()
    st.subheader("Policy Simulator")
    fee_change = st.slider("Thay đổi phí giao dịch (%)", -50, 30, -10)
    margin_rate_change = st.slider("Thay đổi lãi margin (%)", -30, 30, 5)
    campaign_budget = st.slider("Campaign budget (triệu VND)", 0, 5000, 500, step=100)

    st.divider()
    st.subheader("Market Scenario")
    market_shock = st.slider("Market shock (%)", -20, 20, 0)
    fee_cut = st.slider("Fee cut for scenario (%)", 0, 50, 0)
    margin_policy = st.slider("Margin policy change (%)", -30, 30, 0)

    st.divider()
    st.subheader("Demo mode")
    boss_mode = st.toggle("Bật nội dung giải thích cho sếp", value=True)


@st.cache_data(show_spinner=False)
def load_cached_data():
    return load_all()


def build_market_dataset(demo_market: pd.DataFrame):
    """
    Ưu tiên đọc data/market_data_real.csv được tạo offline từ vnstock.
    Nếu file này chưa có, fallback về data/market_data.csv để app luôn chạy ổn định.
    """
    real_market_path = Path("data/market_data_real.csv")
    demo = demo_market.copy()
    demo["date"] = pd.to_datetime(demo["date"], errors="coerce")

    if real_market_path.exists():
        real = pd.read_csv(real_market_path)
        real["date"] = pd.to_datetime(real["date"], errors="coerce")
        real = real.dropna(subset=["date"]).sort_values("date")

        market = real.copy()
        if "market_liquidity" in market.columns and "market_liquidity_bil_vnd" not in market.columns:
            market["market_liquidity_bil_vnd"] = market["market_liquidity"]
        elif "market_liquidity_bil_vnd" not in market.columns:
            market["market_liquidity_bil_vnd"] = 0

        # Các cột này không có trong vnstock; giữ giá trị demo/manual để KPI engine không lỗi.
        if "market_share_pct" not in market.columns:
            market["market_share_pct"] = demo["market_share_pct"].iloc[-1] if "market_share_pct" in demo.columns else 0
        if "market_margin_bil_vnd" not in market.columns:
            market["market_margin_bil_vnd"] = demo["market_margin_bil_vnd"].iloc[-1] if "market_margin_bil_vnd" in demo.columns else 0

        vnindex_df = market[["date", "vnindex"]].copy()
        if "market_liquidity" in market.columns:
            liquidity_df = market[["date", "market_liquidity"]].copy()
        elif "market_liquidity_bil_vnd" in market.columns:
            liquidity_df = market[["date", "market_liquidity_bil_vnd"]].rename(columns={"market_liquidity_bil_vnd": "market_liquidity"})
        elif "volume" in market.columns:
            liquidity_df = market[["date", "volume"]].rename(columns={"volume": "market_liquidity"})
        else:
            liquidity_df = market[["date"]].copy()
            liquidity_df["market_liquidity"] = 0

        last_date = vnindex_df["date"].max().date()
        data_note = f"Market data: REAL CSV từ vnstock. Last date: {last_date}. Market share/margin/fee vẫn là benchmark/manual."
        data_source = "real_csv"
    else:
        market = demo.copy()
        vnindex_df = market[["date", "vnindex"]].copy()
        if "market_liquidity_bil_vnd" in market.columns:
            liquidity_df = market[["date", "market_liquidity_bil_vnd"]].rename(columns={"market_liquidity_bil_vnd": "market_liquidity"})
        else:
            liquidity_df = market[["date"]].copy()
            liquidity_df["market_liquidity"] = 0
        data_note = "Market data: DEMO fallback. Chạy update_market_data.py để tạo data/market_data_real.csv."
        data_source = "demo_fallback"

    return market, vnindex_df, liquidity_df, data_note, data_source


all_data = load_cached_data()
branch, pnl, rm = all_data["branch"], all_data["pnl"], all_data["rm"]
customer, competitor, okr = all_data["customer"], all_data["competitor"], all_data["okr"]
market, vnindex_df, liquidity_df, data_note, data_source = build_market_dataset(all_data["market"])

kpis = latest_period_kpis(branch, pnl, market)
warnings = warning_table(kpis)
actions_df = action_engine(warnings)
cust_enriched = enrich_customers(customer)
cust_summary = customer_summary(customer)
policy = simulate_policy(
    kpis["revenue_mil_vnd"],
    kpis["margin_balance_bil_vnd"],
    fee_change,
    margin_rate_change,
    campaign_budget,
)

cols = st.columns(2 if view_mode.startswith("Mobile") else 5)
cols[0].metric("Revenue", f"{kpis['revenue_mil_vnd']:,.0f} tr", f"{kpis['revenue_wow_pct']:.1f}% WoW")
cols[1].metric("Profit", f"{kpis['profit_mil_vnd']:,.0f} tr")
cols[2].metric("AUM", f"{kpis['aum_bil_vnd']:,.0f} tỷ")
cols[3].metric("Margin", f"{kpis['margin_balance_bil_vnd']:,.0f} tỷ")
cols[4].metric("High churn", f"{cust_summary['high_churn_customers']:,}")

st.info(executive_narrative(kpis))
st.caption(f"Market data note: {data_note}")

with st.sidebar:
    st.divider()
    st.subheader("Market data source")
    if data_source == "real_csv":
        st.success("✅ Market data: REAL (vnstock → CSV)")
    else:
        st.warning("⚠️ Market data: DEMO fallback")
    st.info(f"📅 Last market date: {vnindex_df['date'].max().date()}")
    st.caption("Cập nhật: chạy update_market_data.py → commit/push market_data_real.csv")

if boss_mode:
    st.markdown(
        """
<div class="script-box">
<b>Ưu điểm của mô hình:</b><br>
“Đây không phải là dashboard đơn thuần mà là một hệ thống hỗ trợ ra quyết định kinh doanh: đi từ Dữ liệu → Phân tích → Dự báo → Hành động.”
</div>
<div class="script-box">
<b>Lưu ý:</b><br>
“Mô hình có nhiều tab, được đánh số từ 1 đến 10. Click vào từng tab để xem nội dung nhé:”
</div>
""",
        unsafe_allow_html=True,
    )

tabs = st.tabs(
    [
        "1️⃣ Executive",
        "2️⃣ Customer Intelligence",
        "3️⃣ Business Performance",
        "4️⃣ Market & Competitor",
        "5️⃣ Policy Simulator",
        "6️⃣ Forecast & Scenario",
        "7️⃣ Action Center",
        "8️⃣ OKR / Initiative",
        "9️⃣ CEO Email",
        "🔟 Interview Pack",
        "🎤 Demo Script",
        "🧩 CTCK Operating Model",
        "💣 Case Study",
        "🧱 Data Quality",
    ]
)

with tabs[0]:
    st.subheader("Executive Dashboard")
    st.markdown(
        """
**Mục đích:** Giúp Ban lãnh đạo nhìn nhanh sức khỏe kinh doanh: doanh thu, lợi nhuận, AUM, margin và cảnh báo sớm.

**Giải thích:** “Tab này trả lời 3 câu hỏi: hôm nay business tốt hay xấu, rủi ro ở đâu, và cần hành động gì ngay.”
"""
    )

    trend = pnl.groupby("date", as_index=False)[["revenue_mil_vnd", "profit_mil_vnd"]].sum().tail(120)
    st.plotly_chart(
        px.line(trend, x="date", y=["revenue_mil_vnd", "profit_mil_vnd"], title="Revenue & Profit Trend"),
        use_container_width=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Early warning")
        st.dataframe(warnings, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("### Top recommended actions")
        st.dataframe(actions_df, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("Customer Intelligence Engine")
    st.markdown(
        """
**Thông điệp chính:** Trong công ty chứng khoán, tăng trưởng bền vững không chỉ đến từ thị trường, mà đến từ khả năng giữ khách, tăng activity và quản lý nhóm VIP.
"""
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers", f"{cust_summary['customers']:,}")
    c2.metric("VIP/Ultra VIP", f"{cust_summary['vip_customers']:,}")
    c3.metric("AUM sample", f"{cust_summary['aum_bil_vnd']:,.0f} tỷ")
    c4.metric("Avg margin usage", f"{cust_summary['avg_margin_usage_pct']:.1f}%")

    st.plotly_chart(
        px.histogram(cust_enriched, x="segment", color="churn_flag", title="Customer Segment x Churn Risk"),
        use_container_width=True,
    )
    st.markdown("### RM có rủi ro mất khách cao")
    st.dataframe(rm_churn_ranking(customer).head(20), use_container_width=True, hide_index=True)
    st.markdown("### Danh sách khách hàng cần chăm sóc")
    st.dataframe(cust_enriched.sort_values("churn_risk_score", ascending=False).head(50), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Business Performance")
    st.markdown(
        """
**Logic phân tích:** Doanh thu CTCK thường được phân rã theo 3 driver: trading volume, margin balance và active clients/RM productivity.
"""
    )
    latest_pnl = pnl[pnl["date"] == pnl["date"].max()].sort_values("profit_mil_vnd", ascending=False)
    latest_branch = branch[branch["date"] == branch["date"].max()].sort_values(
        "brokerage_revenue_mil_vnd", ascending=False
    )
    latest_rm = rm[rm["date"] == rm["date"].max()].sort_values("revenue_mil_vnd", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.bar(latest_pnl, x="product", y="profit_mil_vnd", title="Profit by Product"), use_container_width=True)
        st.dataframe(latest_pnl, use_container_width=True, hide_index=True)
    with c2:
        st.plotly_chart(
            px.bar(latest_branch, x="branch", y="brokerage_revenue_mil_vnd", title="Revenue by Branch"),
            use_container_width=True,
        )
        st.dataframe(latest_rm.head(15), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Market & Competitor Benchmark")
    st.markdown(
        """
**Giải thích:** Market data giúp tách yếu tố khách quan khỏi yếu tố nội bộ. Nếu thị trường giảm thì doanh thu giảm có thể là do thanh khoản chung; nếu thị trường tăng mà doanh thu giảm thì phải kiểm tra khách hàng, phí, margin và hiệu suất RM.
"""
    )

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.line(vnindex_df.tail(180), x="date", y="vnindex", title="VNINDEX"), use_container_width=True)
        st.plotly_chart(
            px.line(liquidity_df.tail(180), x="date", y="market_liquidity", title="Market Liquidity / Volume Proxy"),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            px.bar(
                competitor.sort_values("brokerage_market_share_pct", ascending=False),
                x="firm",
                y="brokerage_market_share_pct",
                title="Brokerage Market Share Benchmark",
            ),
            use_container_width=True,
        )
        st.dataframe(competitor, use_container_width=True, hide_index=True)

    st.success(
        "Gap analysis: VNDIRECT cần đồng thời bảo vệ thị phần, nâng digital conversion và tăng active clients từ nhóm Retail/Mass Affluent."
    )

    st.markdown(
        f"""
<div class="warning-box">
<b>Lưu ý về dữ liệu:</b><br>
{data_note}<br><br>
Market share, margin balance, fee và digital score hiện là dữ liệu demo/benchmark mẫu, cần thay bằng dữ liệu nội bộ hoặc nguồn chính thức khi triển khai thật.
</div>
""",
        unsafe_allow_html=True,
    )

with tabs[4]:
    st.subheader("Policy Impact Simulator")
    st.markdown(
        """
**Mục đích:** Cho phép test tác động của chính sách trước khi triển khai: giảm phí, thay đổi lãi margin, tăng ngân sách campaign.
"""
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scenario revenue", f"{policy['scenario_revenue_mil_vnd']:,.0f} tr")
    c2.metric("Incremental revenue", f"{policy['incremental_revenue_mil_vnd']:,.0f} tr")
    c3.metric("Estimated ROI", f"{policy['estimated_roi']:.2f}x")
    c4.metric("Volume effect", f"{policy['volume_effect_pct']:.1f}%")
    st.info(policy["management_message"])

    st.markdown(
        """
**Câu nói khi demo:** “Ví dụ nếu giảm phí giao dịch, hệ thống không chỉ cho thấy doanh thu phí giảm, mà còn ước lượng volume effect và ROI của campaign đi kèm.”
"""
    )

with tabs[5]:
    st.subheader("Forecast & Scenario")
    rev_daily = pnl.groupby("date", as_index=False)["revenue_mil_vnd"].sum()
    fc = forecast_series(rev_daily, "date", "revenue_mil_vnd", periods=forecast_days)
    hist = rev_daily.tail(90).assign(type="Actual").rename(columns={"revenue_mil_vnd": "value"})[["date", "value", "type"]]
    fut = fc.assign(type="Forecast").rename(columns={"forecast": "value"})[["date", "value", "type"]]
    st.plotly_chart(
        px.line(pd.concat([hist, fut]), x="date", y="value", color="type", title="Revenue Forecast"),
        use_container_width=True,
    )

    sc = scenario_engine(kpis, market_shock, fee_cut, margin_policy)
    c1, c2, c3 = st.columns(3)
    c1.metric("Scenario revenue", f"{sc['scenario_revenue_mil_vnd']:,.0f} tr")
    c2.metric("Scenario profit", f"{sc['scenario_profit_mil_vnd']:,.0f} tr")
    c3.metric("Scenario margin", f"{sc['scenario_margin_bil_vnd']:,.0f} tỷ")

    st.markdown(
        """
**Giải thích:** Forecast không phải để đoán tuyệt đối chính xác, mà để tạo early warning và giúp lập kế hoạch kinh doanh theo kịch bản.
"""
    )

with tabs[6]:
    st.subheader("Action Center")
    st.markdown(
        """
**Điểm khác biệt lớn nhất của mô hình:** Dashboard thường chỉ nói “điều gì đang xảy ra”. Action Center trả lời thêm “phải làm gì”.
"""
    )
    action_list = actions_df["Recommended Action"].tolist()
    extra = [
        "Kích hoạt chiến dịch gọi lại khách VIP/Mass Affluent inactive trên 30 ngày.",
        "Thiết lập weekly competitor pack: phí, thị phần, margin, digital campaign.",
        "Tách KPI theo RM/chi nhánh/sản phẩm để xác định nguyên nhân thay đổi doanh thu.",
        "A/B test chính sách phí trước khi triển khai toàn hệ thống.",
    ]
    for i, a in enumerate(action_list + extra, 1):
        st.write(f"{i}. {a}")

with tabs[7]:
    st.subheader("OKR / Initiative Tracker")
    okr2 = okr.copy()
    okr2["status"] = okr2["progress"].apply(lambda x: "🔴 Đỏ" if x < 0.5 else ("🟡 Vàng" if x < 0.8 else "🟢 Xanh"))
    st.dataframe(okr2, use_container_width=True, hide_index=True)
    st.plotly_chart(px.bar(okr2, x="initiative", y="progress", color="risk_level", title="Initiative Progress"), use_container_width=True)

with tabs[8]:
    st.subheader("CEO Email / Morning Brief")
    top_actions = actions_df["Recommended Action"].tolist() + extra
    email_html = build_ceo_email(kpis, cust_summary, top_actions)
    st.components.v1.html(email_html, height=500, scrolling=True)
    st.download_button("Download CEO email HTML", data=email_html, file_name="ceo_morning_brief.html", mime="text/html")

with tabs[9]:
    st.subheader("Data Quality & Governance")
    rows = []
    for name, df in all_data.items():
        rows.append(
            {
                "dataset": name,
                "rows": len(df),
                "columns": len(df.columns),
                "missing_pct": round(df.isna().mean().mean() * 100, 2),
                "date_max": str(df["date"].max().date()) if "date" in df.columns else "",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.warning(
        "Khi dùng dữ liệu thật, cần thống nhất KPI dictionary, owner dữ liệu, tần suất cập nhật, reconciliation với nguồn kế toán/risk và SLA xử lý lỗi."
    )

    st.markdown(
        """
### Phân biệt dữ liệu thật và dữ liệu demo

| Nhóm dữ liệu | Trạng thái hiện tại | Ghi chú khi demo |
|---|---:|---|
| VNINDEX | Có thể lấy thật qua vnstock | Bật toggle `Thử lấy VNINDEX qua vnstock` |
| Market liquidity | Có thể dùng proxy từ vnstock | Cần kiểm tra lại cách quy đổi volume/value |
| Market share | Demo/benchmark mẫu | Cần thay bằng HOSE/HNX hoặc nguồn chính thức |
| Margin balance | Demo | Cần dữ liệu nội bộ hoặc BCTC |
| Fee, digital score | Demo | Dùng để minh họa framework |
| Customer/RM/Branch | Demo | Thay bằng CRM/trading/core nội bộ |

<div class="warning-box">
<b>Lưu ý đối với dữ liệu:</b><br>
“Hiện tại đây là demo framework. VNINDEX có thể lấy qua vnstock; các phần nội bộ như khách hàng, margin, RM, market share sẽ thay bằng dữ liệu thật khi được kết nối với hệ thống nội bộ.”
</div>
""",
        unsafe_allow_html=True,
    )

st.divider()
st.caption(
    "INTERVIEW VERSION kế thừa bản FINAL/ENTERPRISE. Demo chạy ngay bằng CSV; có sẵn connector/API-ready để thay dữ liệu thật."
)
