# Deploy Guide

1. Tạo GitHub repo mới.
2. Upload toàn bộ package.
3. Vào Streamlit Cloud → New app → chọn repo → file `app.py`.
4. Nếu chỉ dùng demo CSV: không cần secrets.
5. Nếu dùng API thật: thêm token/API key vào `.streamlit/secrets.toml`.

## Chạy local
```bash
pip install -r requirements.txt
streamlit run app.py
```
