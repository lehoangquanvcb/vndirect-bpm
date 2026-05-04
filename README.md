# VNDIRECT BPM INTERVIEW VERSION

Package Streamlit/GitHub phục vụ demo năng lực cho vị trí Trưởng phòng Quản lý Hiệu suất Kinh doanh.

## Kế thừa các phiên bản cũ
- FINAL: KPI, P&L, early warning, forecast, market intelligence, RM/Branch ranking.
- FINAL ENTERPRISE: customer intelligence, policy simulator, competitor benchmark, OKR, data quality.
- INTERVIEW VERSION: CEO email brief, interview script, 30-60-90 day plan, mobile/boardroom mode, action center.

## Chạy local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
Đưa toàn bộ thư mục lên GitHub, sau đó deploy trên Streamlit Cloud với entry file `app.py`.

## Dữ liệu
Mặc định dùng CSV demo để chạy ổn định. Có thể thay bằng dữ liệu thật hoặc mở rộng connector trong `modules/market_data_connector.py`.
