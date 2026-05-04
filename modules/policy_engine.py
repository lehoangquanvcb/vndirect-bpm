def simulate_policy(base_revenue_mil_vnd: float, base_margin_bil_vnd: float, fee_change_pct: float, margin_rate_change_pct: float, campaign_budget_mil_vnd: float, elasticity: float = 0.8):
    volume_effect = -fee_change_pct * elasticity
    revenue_after_fee = base_revenue_mil_vnd * (1 + fee_change_pct/100) * (1 + volume_effect/100)
    margin_income_effect = base_margin_bil_vnd * margin_rate_change_pct / 100 * 1000 / 365
    campaign_uplift = campaign_budget_mil_vnd * 1.8
    total_revenue = revenue_after_fee + margin_income_effect + campaign_uplift
    roi = (total_revenue - base_revenue_mil_vnd - campaign_budget_mil_vnd) / max(campaign_budget_mil_vnd, 1)
    return {
        'scenario_revenue_mil_vnd': round(total_revenue, 2),
        'incremental_revenue_mil_vnd': round(total_revenue-base_revenue_mil_vnd, 2),
        'estimated_roi': round(roi, 2),
        'volume_effect_pct': round(volume_effect, 2),
        'management_message': 'Tốt để thử nghiệm A/B theo nhóm khách hàng' if roi > 0 else 'Không nên triển khai rộng, cần test nhỏ hoặc đổi phân khúc mục tiêu'
    }
