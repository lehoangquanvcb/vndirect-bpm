import streamlit as st
import pandas as pd
import plotly.express as px
from modules.data_loader import load_all
from modules.kpi_engine import latest_period_kpis, warning_table, executive_narrative, forecast_series, scenario_engine, action_engine
from modules.market_data_connector import get_vnindex_live_or_demo
from modules.customer_engine import enrich_customers, customer_summary, rm_churn_ranking
from modules.policy_engine import simulate_policy
from modules.report_engine import build_ceo_email, build_interview_story

st.set_page_config(page_title='VNDIRECT BPM INTERVIEW VERSION', page_icon='🏆', layout='wide')
st.markdown('''
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 24px;}
.big-title {font-size:30px;font-weight:800;}
.small-note {color:#6B7280;font-size:13px;}
.card {background:#FFFFFF;border:1px solid #E5E7EB;border-radius:18px;padding:16px;box-shadow:0 3px 14px rgba(0,0,0,0.05);}
</style>
''', unsafe_allow_html=True)

st.markdown('<div class="big-title">🏆 VNDIRECT Business Performance Intelligence — INTERVIEW VERSION</div>', unsafe_allow_html=True)
st.caption('Kế thừa FINAL + ENTERPRISE: CEO dashboard | Customer Intelligence | Policy Simulator | Competitor Benchmark | OKR | CEO Email | Interview Story')

with st.sidebar:
    st.header('⚙️ Control Panel')
    use_live = st.toggle('Thử lấy VNINDEX qua vnstock', value=False)
    view_mode = st.radio('Giao diện', ['PC / Boardroom', 'Mobile friendly'], index=0)
    forecast_days = st.slider('Forecast horizon', 7, 90, 30)
    st.divider()
    st.subheader('Policy Simulator')
    fee_change = st.slider('Thay đổi phí giao dịch (%)', -50, 30, -10)
    margin_rate_change = st.slider('Thay đổi lãi margin (%)', -30, 30, 5)
    campaign_budget = st.slider('Campaign budget (triệu VND)', 0, 5000, 500, step=100)
    st.divider()
    st.subheader('Market Scenario')
    market_shock = st.slider('Market shock (%)', -20, 20, 0)
    fee_cut = st.slider('Fee cut for scenario (%)', 0, 50, 0)
    margin_policy = st.slider('Margin policy change (%)', -30, 30, 0)

all_data = load_all()
market = get_vnindex_live_or_demo(use_live=use_live)
branch, pnl, rm = all_data['branch'], all_data['pnl'], all_data['rm']
customer, competitor, okr = all_data['customer'], all_data['competitor'], all_data['okr']
kpis = latest_period_kpis(branch, pnl, market)
warnings = warning_table(kpis)
actions_df = action_engine(warnings)
cust_enriched = enrich_customers(customer)
cust_summary = customer_summary(customer)
policy = simulate_policy(kpis['revenue_mil_vnd'], kpis['margin_balance_bil_vnd'], fee_change, margin_rate_change, campaign_budget)

cols = st.columns(2 if view_mode.startswith('Mobile') else 5)
cols[0].metric('Revenue', f"{kpis['revenue_mil_vnd']:,.0f} tr", f"{kpis['revenue_wow_pct']:.1f}% WoW")
cols[1].metric('Profit', f"{kpis['profit_mil_vnd']:,.0f} tr")
cols[2].metric('AUM', f"{kpis['aum_bil_vnd']:,.0f} tỷ")
cols[3].metric('Margin', f"{kpis['margin_balance_bil_vnd']:,.0f} tỷ")
cols[4].metric('High churn', f"{cust_summary['high_churn_customers']:,}")

st.info(executive_narrative(kpis))

tabs = st.tabs([
    '1️⃣ Executive', '2️⃣ Customer Intelligence', '3️⃣ Business Performance', '4️⃣ Market & Competitor',
    '5️⃣ Policy Simulator', '6️⃣ Forecast & Scenario', '7️⃣ Action Center', '8️⃣ OKR / Initiative',
    '9️⃣ CEO Email', '🔟 Interview Pack', '🧱 Data Quality'
])

with tabs[0]:
    st.subheader('Executive Dashboard')
    trend = pnl.groupby('date', as_index=False)[['revenue_mil_vnd','profit_mil_vnd']].sum().tail(120)
    st.plotly_chart(px.line(trend, x='date', y=['revenue_mil_vnd','profit_mil_vnd'], title='Revenue & Profit Trend'), use_container_width=True)
    c1,c2=st.columns(2)
    with c1:
        st.markdown('### Early warning')
        st.dataframe(warnings, use_container_width=True, hide_index=True)
    with c2:
        st.markdown('### Top recommended actions')
        st.dataframe(actions_df, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader('Customer Intelligence Engine')
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Customers', f"{cust_summary['customers']:,}")
    c2.metric('VIP/Ultra VIP', f"{cust_summary['vip_customers']:,}")
    c3.metric('AUM sample', f"{cust_summary['aum_bil_vnd']:,.0f} tỷ")
    c4.metric('Avg margin usage', f"{cust_summary['avg_margin_usage_pct']:.1f}%")
    st.plotly_chart(px.histogram(cust_enriched, x='segment', color='churn_flag', title='Customer Segment x Churn Risk'), use_container_width=True)
    st.markdown('### RM có rủi ro mất khách cao')
    st.dataframe(rm_churn_ranking(customer).head(20), use_container_width=True, hide_index=True)
    st.markdown('### Danh sách khách hàng cần chăm sóc')
    st.dataframe(cust_enriched.sort_values('churn_risk_score', ascending=False).head(50), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader('Business Performance')
    latest_pnl = pnl[pnl['date'] == pnl['date'].max()].sort_values('profit_mil_vnd', ascending=False)
    latest_branch = branch[branch['date'] == branch['date'].max()].sort_values('brokerage_revenue_mil_vnd', ascending=False)
    latest_rm = rm[rm['date'] == rm['date'].max()].sort_values('revenue_mil_vnd', ascending=False)
    c1,c2=st.columns(2)
    with c1:
        st.plotly_chart(px.bar(latest_pnl, x='product', y='profit_mil_vnd', title='Profit by Product'), use_container_width=True)
        st.dataframe(latest_pnl, use_container_width=True, hide_index=True)
    with c2:
        st.plotly_chart(px.bar(latest_branch, x='branch', y='brokerage_revenue_mil_vnd', title='Revenue by Branch'), use_container_width=True)
        st.dataframe(latest_rm.head(15), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader('Market & Competitor Benchmark')
    c1,c2=st.columns(2)
    with c1:
        st.plotly_chart(px.line(market.tail(180), x='date', y='vnindex', title='VNINDEX'), use_container_width=True)
        st.plotly_chart(px.line(market.tail(180), x='date', y='market_liquidity_bil_vnd', title='Market Liquidity'), use_container_width=True)
    with c2:
        st.plotly_chart(px.bar(competitor.sort_values('brokerage_market_share_pct', ascending=False), x='firm', y='brokerage_market_share_pct', title='Brokerage Market Share Benchmark'), use_container_width=True)
        st.dataframe(competitor, use_container_width=True, hide_index=True)
    st.success('Gap analysis: VNDIRECT cần đồng thời bảo vệ thị phần, nâng digital conversion và tăng active clients từ nhóm Retail/Mass Affluent.')

with tabs[4]:
    st.subheader('Policy Impact Simulator')
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Scenario revenue', f"{policy['scenario_revenue_mil_vnd']:,.0f} tr")
    c2.metric('Incremental revenue', f"{policy['incremental_revenue_mil_vnd']:,.0f} tr")
    c3.metric('Estimated ROI', f"{policy['estimated_roi']:.2f}x")
    c4.metric('Volume effect', f"{policy['volume_effect_pct']:.1f}%")
    st.info(policy['management_message'])
    st.markdown('**Cách dùng khi phỏng vấn:** Khi được hỏi “giảm phí hay tăng margin có tác động gì?”, mở tab này để trình bày tư duy mô phỏng chính sách.')

with tabs[5]:
    st.subheader('Forecast & Scenario')
    rev_daily = pnl.groupby('date', as_index=False)['revenue_mil_vnd'].sum()
    fc = forecast_series(rev_daily, 'date', 'revenue_mil_vnd', periods=forecast_days)
    hist = rev_daily.tail(90).assign(type='Actual').rename(columns={'revenue_mil_vnd':'value'})[['date','value','type']]
    fut = fc.assign(type='Forecast').rename(columns={'forecast':'value'})[['date','value','type']]
    st.plotly_chart(px.line(pd.concat([hist,fut]), x='date', y='value', color='type', title='Revenue Forecast'), use_container_width=True)
    sc = scenario_engine(kpis, market_shock, fee_cut, margin_policy)
    c1,c2,c3=st.columns(3)
    c1.metric('Scenario revenue', f"{sc['scenario_revenue_mil_vnd']:,.0f} tr")
    c2.metric('Scenario profit', f"{sc['scenario_profit_mil_vnd']:,.0f} tr")
    c3.metric('Scenario margin', f"{sc['scenario_margin_bil_vnd']:,.0f} tỷ")

with tabs[6]:
    st.subheader('Action Center')
    action_list = actions_df['Recommended Action'].tolist()
    extra = [
        'Kích hoạt chiến dịch gọi lại khách VIP/Mass Affluent inactive trên 30 ngày.',
        'Thiết lập weekly competitor pack: phí, thị phần, margin, digital campaign.',
        'Tách KPI theo RM/chi nhánh/sản phẩm để xác định nguyên nhân thay đổi doanh thu.',
        'A/B test chính sách phí trước khi triển khai toàn hệ thống.'
    ]
    for i,a in enumerate(action_list+extra,1):
        st.write(f'{i}. {a}')

with tabs[7]:
    st.subheader('OKR / Initiative Tracker')
    okr2=okr.copy()
    okr2['status']=okr2['progress'].apply(lambda x: '🔴 Đỏ' if x<0.5 else ('🟡 Vàng' if x<0.8 else '🟢 Xanh'))
    st.dataframe(okr2, use_container_width=True, hide_index=True)
    st.plotly_chart(px.bar(okr2, x='initiative', y='progress', color='risk_level', title='Initiative Progress'), use_container_width=True)

with tabs[8]:
    st.subheader('CEO Email / Morning Brief')
    top_actions = actions_df['Recommended Action'].tolist() + extra
    email_html = build_ceo_email(kpis, cust_summary, top_actions)
    st.components.v1.html(email_html, height=500, scrolling=True)
    st.download_button('Download CEO email HTML', data=email_html, file_name='ceo_morning_brief.html', mime='text/html')

with tabs[9]:
    st.subheader('Interview Pack')
    st.markdown(build_interview_story())
    st.markdown('### 10 câu trả lời nên chuẩn bị')
    qs = [
        'Bạn sẽ đo hiệu suất kinh doanh bán lẻ chứng khoán bằng bộ KPI nào?',
        'Nếu doanh thu môi giới giảm nhưng thị trường tăng, bạn phân tích thế nào?',
        'Giảm phí giao dịch có phải là cách tốt để tăng thị phần không?',
        'Làm sao phát hiện sớm khách hàng có nguy cơ rời bỏ?',
        'Bạn phối hợp với IT/Sales/Marketing/Risk như thế nào?',
        'Bạn xây dựng operating rhythm tuần/tháng cho phòng như thế nào?',
        'Dashboard tốt khác báo cáo truyền thống ở điểm nào?',
        'Bạn ưu tiên tăng margin hay kiểm soát rủi ro?',
        'Làm sao benchmark VNDIRECT với SSI, VPS, TCBS?',
        '90 ngày đầu bạn sẽ làm gì?'
    ]
    for q in qs: st.write('- '+q)

with tabs[10]:
    st.subheader('Data Quality & Governance')
    rows=[]
    for name, df in all_data.items():
        rows.append({'dataset': name,'rows': len(df),'columns': len(df.columns),'missing_pct': round(df.isna().mean().mean()*100,2),'date_max': str(df['date'].max().date()) if 'date' in df.columns else ''})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.warning('Khi dùng dữ liệu thật, cần thống nhất KPI dictionary, owner dữ liệu, tần suất cập nhật, reconciliation với nguồn kế toán/risk và SLA xử lý lỗi.')

st.divider()
st.caption('INTERVIEW VERSION kế thừa bản FINAL/ENTERPRISE. Demo chạy ngay bằng CSV; có sẵn connector/API-ready để thay dữ liệu thật.')
