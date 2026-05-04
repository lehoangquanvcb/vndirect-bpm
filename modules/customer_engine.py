import pandas as pd
import numpy as np


def enrich_customers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['last_active_date'] = pd.to_datetime(out['last_active_date'])
    ref = out['last_active_date'].max()
    out['inactive_days'] = (ref - out['last_active_date']).dt.days
    out['segment'] = pd.cut(out['aum_bil_vnd'], bins=[-1, 1, 5, 20, 10**9], labels=['Retail', 'Mass Affluent', 'VIP', 'Ultra VIP']).astype(str)
    out['margin_usage_pct'] = out['margin_balance_bil_vnd'] / out['aum_bil_vnd'].replace(0, np.nan) * 100
    out['margin_usage_pct'] = out['margin_usage_pct'].fillna(0)
    out['churn_risk_score'] = (
        np.minimum(out['inactive_days'] / 60, 1) * 45
        + np.where(out['monthly_trading_value_mil_vnd'] < out['monthly_trading_value_mil_vnd'].median(), 25, 5)
        + np.where(out['segment'].isin(['VIP','Ultra VIP']), 20, 5)
    ).clip(0,100).round(1)
    out['churn_flag'] = np.where(out['churn_risk_score'] >= 65, '🔴 High', np.where(out['churn_risk_score'] >= 45, '🟡 Medium', '🟢 Low'))
    return out


def customer_summary(df: pd.DataFrame) -> dict:
    x = enrich_customers(df)
    return {
        'customers': int(len(x)),
        'aum_bil_vnd': float(x['aum_bil_vnd'].sum()),
        'margin_bil_vnd': float(x['margin_balance_bil_vnd'].sum()),
        'high_churn_customers': int((x['churn_flag']=='🔴 High').sum()),
        'vip_customers': int(x['segment'].isin(['VIP','Ultra VIP']).sum()),
        'avg_margin_usage_pct': float(x['margin_usage_pct'].mean()),
    }


def rm_churn_ranking(df: pd.DataFrame) -> pd.DataFrame:
    x = enrich_customers(df)
    res = x.groupby(['branch','rm'], as_index=False).agg(
        customers=('customer_id','count'),
        aum_bil_vnd=('aum_bil_vnd','sum'),
        high_churn=('churn_flag', lambda s: int((s=='🔴 High').sum())),
        avg_churn_score=('churn_risk_score','mean')
    )
    res['aum_bil_vnd'] = res['aum_bil_vnd'].round(1)
    res['avg_churn_score'] = res['avg_churn_score'].round(1)
    return res.sort_values(['high_churn','aum_bil_vnd'], ascending=False)
