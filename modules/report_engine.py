from datetime import datetime


def build_ceo_email(kpis: dict, customer: dict, top_actions: list) -> str:
    action_text = ''.join([f"<li>{a}</li>" for a in top_actions[:5]]) or '<li>Duy trì nhịp theo dõi và kiểm soát dữ liệu.</li>'
    return f"""
    <h2>VNDIRECT Business Performance Morning Brief</h2>
    <p><b>Ngày lập:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <h3>1. Executive snapshot</h3>
    <ul>
      <li>Doanh thu: <b>{kpis.get('revenue_mil_vnd',0):,.0f} triệu đồng</b>, WoW: <b>{kpis.get('revenue_wow_pct',0):.1f}%</b></li>
      <li>Lợi nhuận: <b>{kpis.get('profit_mil_vnd',0):,.0f} triệu đồng</b></li>
      <li>Dư nợ margin: <b>{kpis.get('margin_balance_bil_vnd',0):,.0f} tỷ đồng</b></li>
      <li>Thị phần ước tính: <b>{kpis.get('market_share_pct',0):.2f}%</b></li>
    </ul>
    <h3>2. Customer intelligence</h3>
    <ul>
      <li>Tổng khách hàng theo mẫu phân tích: <b>{customer.get('customers',0):,}</b></li>
      <li>Khách VIP/Ultra VIP: <b>{customer.get('vip_customers',0):,}</b></li>
      <li>Khách churn risk cao: <b>{customer.get('high_churn_customers',0):,}</b></li>
    </ul>
    <h3>3. Recommended actions</h3>
    <ol>{action_text}</ol>
    <p><i>Thông điệp điều hành:</i> ưu tiên bảo vệ AUM, kích hoạt lại khách inactive, kiểm soát margin theo quality score và theo dõi thị phần hàng tuần.</p>
    """


def build_interview_story() -> str:
    return """
Tôi tiếp cận vai trò Trưởng phòng Quản lý Hiệu suất Kinh doanh theo tư duy Business Operating System, không chỉ làm báo cáo. Hệ thống tôi đề xuất đi từ dữ liệu thị trường, dữ liệu khách hàng, P&L sản phẩm, hiệu suất RM/chi nhánh, đến cảnh báo sớm và action engine. Điểm khác biệt là dashboard không dừng ở việc mô tả quá khứ, mà trả lời ba câu hỏi quản trị: điều gì đang thay đổi, nguyên nhân nằm ở đâu, và tuần này phải hành động gì.

Trong 30 ngày đầu, tôi sẽ chuẩn hóa KPI dictionary, kiểm tra chất lượng dữ liệu, dựng CEO dashboard và early warning. Trong 60 ngày, tôi bổ sung customer intelligence, churn risk, RM productivity và policy simulator. Trong 90 ngày, tôi chuyển sang operating rhythm: morning brief, weekly performance committee, monthly strategy review và backlog cải tiến cùng IT/Sales/Marketing/Risk.
"""
