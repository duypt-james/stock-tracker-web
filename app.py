import streamlit as st
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib
matplotlib.use("Agg")

st.set_page_config(page_title="Stock Tracker", page_icon="📈", layout="wide")

# ============================================================
#  DATA
# ============================================================
DEFAULT_DATA = {"stocks": [], "history": {}}

def fmt(v):
    return f"{v:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_vnd(v, sign=False, decimals=0):
    s = f"{abs(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if v < 0:
        return f"-{s}"
    elif sign and v > 0:
        return f"+{s}"
    return s

def normalize_nghin(val):
    if val > 100:
        return val / 1000.0
    return val

def get_latest_price(data, code):
    hist = data["history"].get(code, [])
    return hist[-1]["price"] if hist else None

def load_data_from_file():
    path = "stock_data.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(DEFAULT_DATA)

def save_data_to_file(data):
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if "data" not in st.session_state:
    st.session_state.data = load_data_from_file()

data = st.session_state.data

# ============================================================
#  SIDEBAR - Import/Export
# ============================================================
with st.sidebar:
    st.header("📂 Quản lý dữ liệu")
    uploaded = st.file_uploader("Import JSON", type=["json"])
    if uploaded:
        try:
            imported = json.load(uploaded)
            if "stocks" in imported and "history" in imported:
                st.session_state.data = imported
                data = imported
                save_data_to_file(data)
                st.success("Import thành công!")
                st.rerun()
            else:
                st.error("File JSON không hợp lệ!")
        except Exception as e:
            st.error(f"Lỗi: {e}")

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button("📥 Export JSON", json_str,
                       file_name="stock_data.json", mime="application/json")

    st.divider()
    st.caption("Stock Tracker v1.0")
    st.caption("Deploy trên Streamlit Cloud")

# ============================================================
#  HEADER
# ============================================================
st.markdown("""
<style>
    .main-header { background: linear-gradient(90deg, #1a73e8, #4285f4);
                   color: white; padding: 16px 24px; border-radius: 10px; margin-bottom: 20px; }
    .main-header h1 { color: white; margin: 0; font-size: 28px; }
    .metric-card { background: white; border-radius: 10px; padding: 16px; text-align: center;
                   box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .profit { color: #34a853; }
    .loss { color: #ea4335; }
</style>
<div class="main-header">
    <h1>📈 STOCK TRACKER</h1>
</div>
""", unsafe_allow_html=True)

# ============================================================
#  TABS
# ============================================================
tab1, tab2 = st.tabs(["📊 Tổng quan", "⚙️ Quản lý"])

# ============================================================
#  TAB 1 - TỔNG QUAN
# ============================================================
with tab1:
    if not data["stocks"]:
        st.info("Chưa có mã CP nào. Vào tab 'Quản lý' để thêm mã mới.")
    else:
        # --- Summary metrics ---
        total_invest = 0
        total_value = 0
        for stk in data["stocks"]:
            latest = get_latest_price(data, stk["code"])
            total_invest += stk["buy_price"] * stk["qty"]
            total_value += (latest * stk["qty"]) if latest else 0

        profit = total_value - total_invest
        pct = (profit / total_invest * 100) if total_invest else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng đầu tư", fmt_vnd(total_invest * 1000))
        c2.metric("Giá trị hiện tại", fmt_vnd(total_value * 1000))
        c3.metric("Lợi nhuận", fmt_vnd(profit * 1000, sign=True))
        c4.metric("Tỷ lệ", f"{pct:+.2f}%",
                  delta="Lãi" if profit >= 0 else "Lỗ",
                  delta_color="normal" if profit >= 0 else "inverse")

        st.divider()

        # --- Portfolio table ---
        st.subheader("Danh mục cổ phiếu")
        if data["stocks"]:
            codes = ["Tất cả"] + [s["code"] for s in data["stocks"]]
            filter_code = st.selectbox("Lọc biểu đồ", codes, key="chart_filter")

            rows = []
            for stk in data["stocks"]:
                latest = get_latest_price(data, stk["code"])
                if latest:
                    pnl = (latest - stk["buy_price"]) * stk["qty"]
                    pnl_pct = (latest - stk["buy_price"]) / stk["buy_price"] * 100
                else:
                    pnl = 0
                    pnl_pct = 0
                rows.append({
                    "Mã CP": stk["code"],
                    "SL": f"{stk['qty']:,}",
                    "Giá mua": fmt(stk["buy_price"]),
                    "Giá HT": fmt(latest) if latest else "--",
                    "Lãi/Lỗ": fmt_vnd(pnl * 1000, sign=True) if latest else "--",
                    "Lãi/Lỗ %": f"{pnl_pct:+.2f}%" if latest else "--",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

            # --- Chart ---
            st.divider()
            st.subheader("Biểu đồ lãi/lỗ so với giá gốc")

            show_stocks = data["stocks"] if filter_code == "Tất cả" else [
                s for s in data["stocks"] if s["code"] == filter_code]

            all_dates = set()
            for stk in show_stocks:
                for h in data["history"].get(stk["code"], []):
                    all_dates.add(h["date"])
            all_dates = sorted(all_dates, key=lambda x: datetime.strptime(x, "%d/%m/%Y"))

            if all_dates and show_stocks:
                fig, ax = plt.subplots(figsize=(12, 5))
                colors = ["#1a73e8", "#34a853", "#fbbc04", "#9334e6", "#ff6d01"]
                n_dates = len(all_dates)
                n_stocks = len(show_stocks)
                bar_w = 0.7 if n_stocks == 1 else max(0.15, 0.6 / n_stocks)

                for i, stk in enumerate(show_stocks):
                    code = stk["code"]
                    buy = stk["buy_price"]
                    qty = stk["qty"]
                    hist = data["history"].get(code, [])
                    price_map = {h["date"]: h["price"] for h in hist}
                    profits, positions = [], []
                    for j, d in enumerate(all_dates):
                        if d in price_map:
                            profits.append((price_map[d] - buy) * qty * 1000)
                            if n_stocks == 1:
                                positions.append(j)
                            else:
                                positions.append(j + i * bar_w - (n_stocks - 1) * bar_w / 2)
                    if profits:
                        color = colors[i % len(colors)]
                        bars = ax.bar(positions, profits, width=bar_w, label=code,
                                      color=color, alpha=0.85)
                        for bar, val in zip(bars, profits):
                            y = bar.get_height()
                            rng = max(abs(max(profits, default=1)), abs(min(profits, default=1)))
                            offset = rng * 0.03
                            va = "bottom" if val >= 0 else "top"
                            ax.text(bar.get_x() + bar.get_width() / 2.,
                                    y + (offset if val >= 0 else -offset),
                                    fmt_vnd(val, sign=True), ha="center", va=va,
                                    fontsize=6, color=color, fontweight="bold")

                ax.set_xticks(list(range(n_dates)))
                ax.set_xticklabels([d[:5] for d in all_dates], rotation=45, fontsize=8)
                ax.axhline(y=0, color="#999", linewidth=0.8)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                title = "Lãi/Lỗ so với giá gốc"
                if filter_code != "Tất cả":
                    title += f" - {filter_code}"
                ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
                if n_stocks > 1:
                    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9)
                ax.yaxis.set_major_formatter(
                    mticker.FuncFormatter(lambda x, p: fmt_vnd(x, sign=True)))
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
            else:
                st.info("Nhập giá để xem biểu đồ")

        # --- Price history ---
        st.divider()
        st.subheader("Lịch sử giá theo phiên")

        hist_codes = [s["code"] for s in data["stocks"]]
        if hist_codes:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                hist_code = st.selectbox("Mã CP", hist_codes, key="hist_code")
            with col2:
                if st.button("🗑️ Xóa phiên cuối", use_container_width=True):
                    hist = data["history"].get(hist_code, [])
                    if hist:
                        last = hist[-1]
                        st.session_state["confirm_delete"] = {
                            "code": hist_code, "date": last["date"], "price": last["price"]}
                    else:
                        st.warning("Không có dữ liệu!")

            if "confirm_delete" in st.session_state:
                cd = st.session_state.confirm_delete
                st.warning(f"Xóa phiên {cd['date']} - {fmt(cd['price'])}?")
                dc1, dc2, _ = st.columns([1, 1, 4])
                with dc1:
                    if st.button("✅ Có", key="confirm_del_yes"):
                        hist = data["history"].get(cd["code"], [])
                        data["history"][cd["code"]] = [h for h in hist
                                                        if h["date"] != cd["date"]]
                        save_data_to_file(data)
                        del st.session_state["confirm_delete"]
                        st.rerun()
                with dc2:
                    if st.button("❌ Không", key="confirm_del_no"):
                        del st.session_state["confirm_delete"]
                        st.rerun()

            stk = next((s for s in data["stocks"] if s["code"] == hist_code), None)
            hist = data["history"].get(hist_code, [])
            buy = stk["buy_price"]
            qty = stk["qty"]

            if hist:
                rows = []
                edit_row = None
                for i in range(len(hist) - 1, -1, -1):
                    h = hist[i]
                    price = h["price"]
                    prev = hist[i - 1]["price"] if i > 0 else price
                    change = price - prev
                    pnl = (price - buy) * qty
                    pnl_pct = (price - buy) / buy * 100
                    rows.append({
                        "date": h["date"], "price": price,
                        "change": change, "pnl": pnl, "pnl_pct": pnl_pct
                    })

                display_rows = []
                for r in rows:
                    display_rows.append({
                        "Ngày": r["date"],
                        "Giá đóng cửa": fmt(r["price"]),
                        "Thay đổi": fmt_vnd(r["change"] * 1000, sign=True, decimals=0),
                        "Lãi/Lỗ": fmt_vnd(r["pnl"] * 1000, sign=True, decimals=0),
                        "Lãi/Lỗ %": f"{r['pnl_pct']:+.2f}%",
                    })
                st.dataframe(display_rows, use_container_width=True, hide_index=True)

                # Edit price row
                edit_dates = [r["date"] for r in rows]
                with st.expander("✏️ Sửa giá"):
                    ec1, ec2, ec3 = st.columns([2, 2, 1])
                    with ec1:
                        edit_date = st.selectbox("Chọn ngày", edit_dates, key="edit_date")
                    with ec2:
                        row_to_edit = next(r for r in rows if r["date"] == edit_date)
                        new_price = st.number_input("Giá mới (nghìn VND)",
                                                     value=row_to_edit["price"],
                                                     step=0.1, format="%.3f",
                                                     key="new_price")
                    with ec3:
                        st.write("")
                        st.write("")
                        if st.button("💾 Lưu", key="save_price", use_container_width=True):
                            for h in data["history"][hist_code]:
                                if h["date"] == edit_date:
                                    h["price"] = new_price
                                    break
                            save_data_to_file(data)
                            st.success(f"Đã cập nhật giá {edit_date}: {fmt(new_price)}")
                            st.rerun()
            else:
                st.info("Chưa có dữ liệu giá")

            # Quick add
            with st.expander("➕ Thêm nhanh giá"):
                qc1, qc2, qc3 = st.columns([2, 2, 1])
                with qc1:
                    add_date = st.date_input("Ngày", key="add_date")
                with qc2:
                    add_price = st.number_input("Giá (nghìn VND)", value=0.0,
                                                 step=0.1, format="%.3f",
                                                 key="add_price_val")
                with qc3:
                    st.write("")
                    st.write("")
                    if st.button("Thêm", key="add_price_btn", use_container_width=True):
                        date_str = add_date.strftime("%d/%m/%Y")
                        price = normalize_nghin(add_price)
                        if hist_code not in data["history"]:
                            data["history"][hist_code] = []
                        for h in data["history"][hist_code]:
                            if h["date"] == date_str:
                                h["price"] = price
                                save_data_to_file(data)
                                st.success(f"Đã cập nhật {date_str}: {fmt(price)}")
                                st.rerun()
                        data["history"][hist_code].append(
                            {"date": date_str, "price": price})
                        data["history"][hist_code].sort(
                            key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y"))
                        save_data_to_file(data)
                        st.success(f"Đã thêm {date_str}: {fmt(price)}")
                        st.rerun()
        else:
            st.info("Thêm mã CP để xem lịch sử giá")

# ============================================================
#  TAB 2 - QUẢN LÝ
# ============================================================
with tab2:
    st.subheader("Thêm mã CP mới")
    with st.form("add_stock_form", clear_on_submit=True):
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
        with fc1:
            new_code = st.text_input("Mã CP", placeholder="VD: CEO").upper()
        with fc2:
            new_qty = st.number_input("Số lượng", min_value=1, value=100, step=1)
        with fc3:
            new_price = st.number_input("Giá mua (nghìn VND)", min_value=0.0,
                                         value=0.0, step=0.1, format="%.3f")
        with fc4:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("➕ Thêm vào danh mục",
                                               use_container_width=True,
                                               type="primary")

        if submitted:
            if not new_code:
                st.error("Nhập mã CP!")
            elif any(s["code"] == new_code for s in data["stocks"]):
                st.error(f"{new_code} đã tồn tại!")
            else:
                price = normalize_nghin(new_price)
                data["stocks"].append({
                    "code": new_code, "qty": new_qty, "buy_price": price})
                if new_code not in data["history"]:
                    data["history"][new_code] = []
                save_data_to_file(data)
                st.success(f"Đã thêm {new_code}!")
                st.rerun()

    st.divider()
    st.subheader("Danh mục hiện tại")

    if not data["stocks"]:
        st.info("Chưa có mã CP nào")
    else:
        for i, stk in enumerate(data["stocks"]):
            code = stk["code"]
            latest = get_latest_price(data, code)
            if latest:
                pnl = (latest - stk["buy_price"]) * stk["qty"]
                pnl_pct = (latest - stk["buy_price"]) / stk["buy_price"] * 100
                pcolor = "🟢" if pnl >= 0 else "🔴"
            else:
                pnl = 0
                pnl_pct = 0
                pcolor = "⚪"

            with st.container():
                st.markdown(f"---")
                mc1, mc2, mc3, mc4, mc5 = st.columns([2, 2, 2, 2, 1])
                with mc1:
                    st.markdown(f"**{pcolor} {code}**")
                with mc2:
                    new_qty = st.number_input(
                        "SL", value=stk["qty"], min_value=1, step=1,
                        key=f"qty_{code}", label_visibility="collapsed")
                    if new_qty != stk["qty"]:
                        stk["qty"] = new_qty
                        save_data_to_file(data)
                with mc3:
                    new_buy = st.number_input(
                        "Giá mua", value=stk["buy_price"], step=0.1,
                        format="%.3f", key=f"buy_{code}", label_visibility="collapsed")
                    if abs(new_buy - stk["buy_price"]) > 0.0001:
                        stk["buy_price"] = normalize_nghin(new_buy)
                        save_data_to_file(data)
                with mc4:
                    if latest:
                        st.metric("Lãi/Lỗ", fmt_vnd(pnl * 1000, sign=True),
                                  f"{pnl_pct:+.2f}%")
                    else:
                        st.write("--")
                with mc5:
                    if st.button("🗑️", key=f"del_{code}"):
                        st.session_state[f"confirm_del_stock_{code}"] = True

                if st.session_state.get(f"confirm_del_stock_{code}", False):
                    st.warning(f"Xóa {code} khỏi danh mục?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("✅ Xóa", key=f"yes_del_{code}"):
                            data["stocks"] = [s for s in data["stocks"]
                                              if s["code"] != code]
                            data["history"].pop(code, None)
                            save_data_to_file(data)
                            del st.session_state[f"confirm_del_stock_{code}"]
                            st.rerun()
                    with dc2:
                        if st.button("❌ Hủy", key=f"no_del_{code}"):
                            del st.session_state[f"confirm_del_stock_{code}"]
                            st.rerun()
