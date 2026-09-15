# Stock Tracker - Web App

Theo dõi danh mục cổ phiếu, lãi/lỗ theo phiên.

## Deploy lên Streamlit Cloud

### Cách 1: Deploy nhanh (Recommended)
1. Tạo repo mới trên GitHub
2. Upload 2 file: `app.py` và `requirements.txt`
3. Vào [share.streamlit.io](https://share.streamlit.io)
4. Bấm **New app** → chọn repo → nhập `app.py` → bấm **Deploy**

### Cách 2: Deploy từ repo có sẵn
1. Push code lên GitHub
2. Kết nối GitHub account trên Streamlit Cloud
3. Chọn repo → Deploy

## Chạy local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tính năng

- Thêm/sửa/xóa mã CP
- Nhập giá theo phiên
- Biểu đồ lãi/lỗ
- Import/Export dữ liệu JSON
- Responsive trên mobile/iPad
