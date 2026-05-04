import numpy as np
import pandas as pd


def pct_change(current, previous):
    if previous in [0, None] or pd.isna(previous):
        return 0.0
    return (current / previous - 1) * 100


def traffic_light(value, yellow, red, high_is_bad=True):
    if high_is_bad:
        if value >= red: return '🔴 Đỏ'
        if value >= yellow: return '🟡 Vàng'
        return '🟢 Xanh'
    if value <= red: return '🔴 Đỏ'
    if value <= yellow: return '🟡 Vàng'
    return '🟢 Xanh'


def latest_period_kpis(branch, pnl, market):
    latest = branch['date'].max()
    prev = latest - pd.Timedelta(days=7)
    cur_b = branch[branch['date'] == latest]
    prev_b = branch[branch['date'] == prev]
    if prev_b.empty:
        prev_b = branch[branch['date'] < latest].tail(len(cur_b))
    cur_p = pnl[pnl['date'] == pnl['date'].max()]
    prev_p = pnl[pnl['date'] < pnl['date'].max()].groupby('product', as_index=False).tail(1)
    cur_m = market.iloc[-1]
    prev_m = market.iloc[-8] if len(market) > 8 else market.iloc[0]
    revenue = float(cur_p['revenue_mil_vnd'].sum())
    revenue_prev = float(prev_p['revenue_mil_vnd'].sum()) if not prev_p.empty else revenue
    profit = float(cur_p['profit_mil_vnd'].sum())
    margin = float(cur_b['margin_balance_bil_vnd'].sum())
    aum = float(cur_b['aum_bil_vnd'].sum())
    return {
        'latest_date': latest.date().isoformat(),
        'revenue_mil_vnd': revenue,
        'profit_mil_vnd': profit,
        'margin_balance_bil_vnd': margin,
        'aum_bil_vnd': aum,
        'active_clients': int(cur_b['active_clients'].sum()),
        'new_accounts': int(cur_b['new_accounts'].sum()),
        'market_share_pct': float(cur_m.get('market_share_pct', 0) or 0),
        'vnindex': float(cur_m['vnindex']),
        'revenue_wow_pct': pct_change(revenue, revenue_prev),
        'vnindex_wow_pct': pct_change(cur_m['vnindex'], prev_m['vnindex']),
    }


def warning_table(kpis):
    rows = []
    rows.append(['Doanh thu WoW', kpis['revenue_wow_pct'], traffic_light(kpis['revenue_wow_pct'], -3, -7, high_is_bad=False), 'Doanh thu giảm mạnh cần kiểm tra thị phần, giao dịch active clients và campaign.'])
    margin_to_aum = kpis['margin_balance_bil_vnd'] / max(kpis['aum_bil_vnd'], 1) * 100
    rows.append(['Margin/AUM', margin_to_aum, traffic_light(margin_to_aum, 24, 32, True), 'Margin tăng nóng làm tăng rủi ro call margin khi thị trường đảo chiều.'])
    rows.append(['Thị phần', kpis['market_share_pct'], traffic_light(kpis['market_share_pct'], 5.8, 5.4, False), 'Thị phần suy yếu cần benchmark phí, sản phẩm và RM productivity.'])
    rows.append(['VNINDEX WoW', kpis['vnindex_wow_pct'], traffic_light(kpis['vnindex_wow_pct'], -2, -5, False), 'Thị trường giảm ảnh hưởng doanh thu môi giới và khẩu vị margin.'])
    return pd.DataFrame(rows, columns=['Risk Driver','Value','Status','Action'])


def executive_narrative(kpis):
    tone = 'tích cực' if kpis['revenue_wow_pct'] >= 0 else 'thận trọng'
    return (
        f"Tại ngày {kpis['latest_date']}, bức tranh hiệu suất ở trạng thái {tone}. "
        f"Doanh thu đạt {kpis['revenue_mil_vnd']:,.0f} triệu đồng, thay đổi {kpis['revenue_wow_pct']:.1f}% so với tuần trước. "
        f"Dư nợ margin đạt {kpis['margin_balance_bil_vnd']:,.0f} tỷ đồng, AUM đạt {kpis['aum_bil_vnd']:,.0f} tỷ đồng, thị phần ước tính {kpis['market_share_pct']:.2f}%. "
        "Ưu tiên điều hành là bảo vệ thị phần, duy trì khách hàng active, kiểm soát margin tăng nóng và chuyển insight thành hành động bán hàng theo từng chi nhánh/RM."
    )


def forecast_series(df, date_col, value_col, periods=30):
    x = df[[date_col, value_col]].dropna().sort_values(date_col).copy()
    daily = x.groupby(date_col)[value_col].sum().reset_index()
    daily['ma7'] = daily[value_col].rolling(7, min_periods=1).mean()
    last = daily.iloc[-1]
    trend = (daily['ma7'].iloc[-1] - daily['ma7'].iloc[-15]) / 14 if len(daily) > 15 else 0
    future_dates = pd.date_range(daily[date_col].max() + pd.Timedelta(days=1), periods=periods, freq='D')
    vals = [max(0, last['ma7'] + trend*(i+1)) for i in range(periods)]
    return pd.DataFrame({'date': future_dates, 'forecast': vals})


def scenario_engine(kpis, market_shock_pct=0, fee_cut_pct=0, margin_policy_pct=0):
    revenue = kpis['revenue_mil_vnd'] * (1 + 0.8*market_shock_pct/100) * (1 - fee_cut_pct/100)
    margin = kpis['margin_balance_bil_vnd'] * (1 + margin_policy_pct/100)
    profit = kpis['profit_mil_vnd'] * (revenue / max(kpis['revenue_mil_vnd'],1))
    return {'scenario_revenue_mil_vnd': revenue, 'scenario_margin_bil_vnd': margin, 'scenario_profit_mil_vnd': profit}


def action_engine(warnings):
    actions=[]
    for _, r in warnings.iterrows():
        if 'Đỏ' in r['Status'] or 'Vàng' in r['Status']:
            actions.append({'Priority':'High' if 'Đỏ' in r['Status'] else 'Medium','Issue':r['Risk Driver'],'Recommended Action':r['Action']})
    if not actions:
        actions.append({'Priority':'Normal','Issue':'No critical issue','Recommended Action':'Duy trì nhịp bán hàng, theo dõi pipeline và chuẩn bị campaign theo biến động thị trường.'})
    return pd.DataFrame(actions)
