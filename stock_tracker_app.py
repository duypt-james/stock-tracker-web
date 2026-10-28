import customtkinter as ctk
import json
import os
import sys
from datetime import datetime
from tkinter import messagebox, ttk, END, colorchooser
import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.ticker as mticker

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "stock_data.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "stock_settings.json")

FONTS = ["Segoe UI", "Arial", "Tahoma", "Verdana", "Consolas",
         "Courier New", "Times New Roman", "Calibri", "Roboto",
         "Inter", "Ubuntu", "Cascadia Code"]
FONT_SIZES = [8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24]

DEFAULT_SETTINGS = {
    "font_family": "Segoe UI", "font_size": 11,
    "bg_color": "#f0f2f5", "card_bg": "#ffffff",
    "header_color": "#1a73e8", "text_color": "#333333",
    "text_secondary": "#5f6368", "profit_color": "#34a853",
    "loss_color": "#ea4335", "accent_1": "#1a73e8",
    "accent_2": "#34a853", "accent_3": "#fbbc04",
    "accent_4": "#9334e6", "accent_5": "#ff6d01",
    "table_row_alt": "#f8f9fa", "table_header_bg": "#e8eaed",
    "table_selected": "#d2e3fc", "chart_bg": "#ffffff",
    "chart_grid": "#dadce0", "chart_text": "#5f6368",
}


def fmt(v):
    return f"{v:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_short(v):
    """Format so nguyen khong phan thap phan"""
    return f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_vnd(v, sign=False, decimals=2):
    """Format tien VND voi dau + va so thap phan"""
    s = f"{abs(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if v < 0:
        return f"-{s}"
    elif sign and v > 0:
        return f"+{s}"
    return s


def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"stocks": [], "history": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            s = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(s)
            return merged
    return dict(DEFAULT_SETTINGS)


def save_settings_to_file(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class EditableEntry(ctk.CTkEntry):
    def __init__(self, master, on_confirm=None, **kwargs):
        self.on_confirm = on_confirm
        super().__init__(master, **kwargs)
        self.bind("<Return>", self._confirm)
        self.bind("<Escape>", self._cancel)
        self.bind("<FocusOut>", self._confirm)

    def _confirm(self, event=None):
        if self.on_confirm:
            self.on_confirm(self.get())

    def _cancel(self, event=None):
        self.master.focus_set()


class ColorButton(ctk.CTkButton):
    def __init__(self, master, color="#ffffff", **kwargs):
        self.current_color = color
        super().__init__(master, width=36, height=28, corner_radius=6,
                         fg_color=color, border_color="#dadce0", border_width=1,
                         text="", command=self._pick, **kwargs)

    def _pick(self):
        result = colorchooser.askcolor(initialcolor=self.current_color,
                                       title="Chọn màu")
        if result and result[1]:
            self.current_color = result[1]
            self.configure(fg_color=self.current_color)

    def set_color(self, c):
        self.current_color = c
        self.configure(fg_color=c)


class StockApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Stock Tracker - Theo dõi cổ phiếu")
        try:
            _dir = os.path.dirname(os.path.abspath(__file__))
            _ico = os.path.join(_dir, "stock_icon.ico")
            _png = os.path.join(_dir, "stock_icon.png")
            if os.path.exists(_ico):
                self.iconbitmap(_ico)
            if os.path.exists(_png):
                from tkinter import PhotoImage
                _img = PhotoImage(file=_png)
                self.iconphoto(True, _img)
        except Exception:
            pass
        self.geometry("1400x850")
        self.settings = load_settings()
        self.configure(fg_color=self.settings["bg_color"])
        self.data = load_data()
        self.chart_filter = "Tất cả"

        self.top_frame = None
        self.tab_view = None
        self.summary_frame = None
        self.stock_frame = None
        self.chart_frame = None
        self.filter_frame = None
        self.hist_frame = None
        self.hist_combo = None
        self.tree = None
        self.add_date = None
        self.add_price_entry = None
        self._chart_drawn = False

        self._build_ui()
        self.refresh_data()

    def _font(self, size=None, bold=False):
        s = size or self.settings["font_size"]
        w = "bold" if bold else "normal"
        return ctk.CTkFont(family=self.settings["font_family"], size=s, weight=w)

    def _tkfont(self, size=None, bold=False):
        s = size or self.settings["font_size"]
        w = "bold" if bold else "normal"
        return (self.settings["font_family"], s, w)

    # ================================================================
    #  BUILD
    # ================================================================
    def _build_ui(self):
        s = self.settings

        self.top_frame = ctk.CTkFrame(self, fg_color=s["header_color"],
                                       corner_radius=0, height=56)
        self.top_frame.pack(fill="x")
        self.top_frame.pack_propagate(False)
        ctk.CTkLabel(self.top_frame, text="STOCK TRACKER",
                     font=self._font(20, True),
                     text_color="white").pack(side="left", padx=25)
        ctk.CTkButton(self.top_frame, text="Lưu cài đặt", width=110, height=34,
                      corner_radius=8, fg_color=s["accent_2"], text_color="white",
                      font=self._font(11, True), hover_color="#2d9148",
                      command=self._apply_settings).pack(side="right", padx=12)

        self.tab_view = ctk.CTkTabview(self, fg_color="transparent", anchor="nw")
        self.tab_view.pack(fill="both", expand=True, padx=15, pady=10)
        self.tab_main = self.tab_view.add("  Tổng quan  ")
        self.tab_settings = self.tab_view.add("  Cài đặt  ")

        self._build_main_tab()
        self._build_settings_tab()

    def _build_main_tab(self):
        s = self.settings
        body = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=5, pady=5)

        left = ctk.CTkFrame(body, fg_color=s["card_bg"], corner_radius=10,
                            border_width=2, border_color=s["header_color"])
        left.pack(side="left", fill="both", padx=(0, 8))
        left.configure(width=380)
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="  Danh mục cổ phiếu",
                     font=self._font(15, True),
                     text_color=s["header_color"], anchor="w").pack(
            fill="x", padx=15, pady=(15, 8))

        self.summary_frame = ctk.CTkFrame(left, fg_color=s["table_row_alt"],
                                           corner_radius=8)
        self.summary_frame.pack(fill="x", padx=8, pady=(0, 6))

        hdr = ctk.CTkFrame(left, fg_color=s["table_header_bg"], corner_radius=6, height=26)
        hdr.pack(fill="x", padx=12)
        hdr.pack_propagate(False)
        for txt, w in [("Mã CP", 45), ("SL", 32), ("Giá mua", 52),
                        ("Giá HT", 52), ("Lãi/Lỗ", 65), ("%", 35)]:
            ctk.CTkLabel(hdr, text=txt, width=w,
                         font=self._font(10, True),
                         text_color=s["text_secondary"]).pack(side="left", padx=2)

        self.stock_frame = ctk.CTkScrollableFrame(
            left, fg_color="transparent", height=250,
            scrollbar_button_color=s["chart_grid"])
        self.stock_frame.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        add_btn_frame = ctk.CTkFrame(left, fg_color="transparent", height=32)
        add_btn_frame.pack(fill="x", padx=12, pady=(0, 8))
        add_btn_frame.pack_propagate(False)
        ctk.CTkButton(add_btn_frame, text="+ Thêm mã CP mới", width=150, height=26,
                      corner_radius=6, fg_color=s["accent_2"], text_color="white",
                      font=self._font(10, True), hover_color="#2d9148",
                      command=self.add_stock_dialog).pack(side="left")

        right = ctk.CTkFrame(body, fg_color=s["card_bg"], corner_radius=10,
                             border_width=2, border_color=s["header_color"])
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        chart_card = ctk.CTkFrame(right, fg_color="transparent", height=360)
        chart_card.pack(fill="x", pady=(0, 12))
        chart_card.pack_propagate(False)

        chart_hdr = ctk.CTkFrame(chart_card, fg_color="transparent")
        chart_hdr.pack(fill="x", padx=15, pady=(12, 2))
        ctk.CTkLabel(chart_hdr, text="Biểu đồ lãi/lỗ so với giá gốc",
                     font=self._font(14, True),
                     text_color=s["header_color"]).pack(side="left")
        self.filter_frame = ctk.CTkFrame(chart_hdr, fg_color="transparent")
        self.filter_frame.pack(side="right")

        self.chart_frame = ctk.CTkFrame(chart_card, fg_color="transparent")
        self.chart_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        hist_card = ctk.CTkFrame(right, fg_color="transparent")
        hist_card.pack(fill="both", expand=True)

        hist_hdr = ctk.CTkFrame(hist_card, fg_color="transparent")
        hist_hdr.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(hist_hdr, text="Lịch sử giá theo phien",
                     font=self._font(13, True),
                     text_color=s["header_color"]).pack(side="left")

        self.hist_combo = ctk.CTkComboBox(
            hist_hdr, values=["--"], width=100, height=30,
            fg_color=s["table_row_alt"], border_color=s["chart_grid"],
            button_color=s["header_color"], font=self._font(10),
            command=self.load_history)
        self.hist_combo.pack(side="right", padx=5)

        ctk.CTkButton(hist_hdr, text="Xóa phiên cuối", width=95, height=28,
                      corner_radius=6, fg_color=s["loss_color"], text_color="white",
                      font=self._font(10),
                      command=self.delete_price).pack(side="right", padx=3)

        ctk.CTkButton(hist_hdr, text="Sửa giá", width=65, height=28,
                      corner_radius=6, fg_color="#f57c00", text_color="white",
                      font=self._font(10),
                      command=self._edit_selected_price).pack(side="right", padx=3)

        self.hist_frame = ctk.CTkFrame(hist_card, fg_color="transparent")
        self.hist_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white",
                        foreground=s["text_color"], rowheight=26,
                        fieldbackground="white", font=self._tkfont(10))
        style.configure("Treeview.Heading",
                        background=s["table_header_bg"],
                        foreground=s["text_color"],
                        font=self._tkfont(10, True))
        style.map("Treeview", background=[("selected", s["table_selected"])])

        self.tree = ttk.Treeview(
            self.hist_frame,
            columns=("date", "price", "change", "profit", "pct"),
            show="headings", height=8)
        for col, txt, w in [("date", "Ngay", 90), ("price", "Giá đóng cửa", 90),
                              ("change", "Thay đổi", 85), ("profit", "Lãi/Lỗ", 100),
                              ("pct", "Lãi/Lỗ %", 75)]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center")

        scrollbar = ttk.Scrollbar(self.hist_frame, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        add_row = ctk.CTkFrame(hist_card, fg_color="#e8f5e9", corner_radius=8)
        add_row.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(add_row, text="Thêm nhanh:", font=self._font(10, True),
                     text_color="#2e7d32").pack(side="left", padx=(10, 5))
        ctk.CTkLabel(add_row, text="Ngày:", font=self._font(10),
                     text_color=s["text_secondary"]).pack(side="left", padx=(8, 2))
        self.add_date = ctk.CTkEntry(add_row, width=95, height=28,
                                     fg_color="white", border_color="#aad4aa",
                                     font=self._font(10))
        self.add_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.add_date.pack(side="left", padx=2)
        ctk.CTkLabel(add_row, text="Giá:", font=self._font(10),
                     text_color=s["text_secondary"]).pack(side="left", padx=(8, 2))
        self.add_price_entry = ctk.CTkEntry(add_row, width=80, height=28,
                                            fg_color="white", border_color="#aad4aa",
                                            font=self._font(10), placeholder_text="0")
        self.add_price_entry.pack(side="left", padx=2)
        ctk.CTkButton(add_row, text="Thêm", width=60, height=28, corner_radius=6,
                      fg_color=s["accent_2"], text_color="white",
                      font=self._font(10, True), hover_color="#2d9148",
                      command=self.quick_add_price).pack(side="left", padx=8)

    def _build_settings_tab(self):
        s = self.settings
        outer = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent",
                                        scrollbar_button_color="#dadce0")
        outer.pack(fill="both", expand=True)

        def section(parent, title):
            card = ctk.CTkFrame(parent, fg_color=s["card_bg"], corner_radius=10)
            card.pack(fill="x", padx=20, pady=(0, 14))
            ctk.CTkLabel(card, text=title, font=self._font(14, True),
                         text_color=s["header_color"], anchor="w").pack(
                fill="x", padx=18, pady=(14, 6))
            return card

        card = section(outer, "Font chữ")
        r1 = ctk.CTkFrame(card, fg_color="transparent", height=40)
        r1.pack(fill="x", padx=18, pady=3)
        r1.pack_propagate(False)
        ctk.CTkLabel(r1, text="Font chữ", width=200, anchor="w",
                     font=self._font(11), text_color=s["text_color"]).pack(side="left")
        self.set_font_family = ctk.CTkComboBox(r1, values=FONTS, width=220, height=32,
                                                fg_color="white", border_color="#dadce0",
                                                button_color=s["header_color"],
                                                font=self._font(10))
        self.set_font_family.set(s["font_family"])
        self.set_font_family.pack(side="right")

        r2 = ctk.CTkFrame(card, fg_color="transparent", height=40)
        r2.pack(fill="x", padx=18, pady=(3, 14))
        r2.pack_propagate(False)
        ctk.CTkLabel(r2, text="Kích thước chữ", width=200, anchor="w",
                     font=self._font(11), text_color=s["text_color"]).pack(side="left")
        self.set_font_size = ctk.CTkComboBox(r2, values=[str(x) for x in FONT_SIZES],
                                              width=100, height=32, fg_color="white",
                                              border_color="#dadce0",
                                              button_color=s["header_color"],
                                              font=self._font(10))
        self.set_font_size.set(str(s["font_size"]))
        self.set_font_size.pack(side="right")

        self.color_buttons_main = {}
        self.color_buttons_table = {}
        self.color_buttons_pnl = {}
        self.color_buttons_chart = {}
        self.color_buttons_accent = {}

        for section_title, color_map, attr_name in [
            ("Màu chính", [("Màu nền chính", "bg_color"), ("Màu thẻ", "card_bg"),
                           ("Màu header", "header_color"), ("Màu chữ chính", "text_color"),
                           ("Màu chữ phụ", "text_secondary")], "color_buttons_main"),
            ("Màu bảng dữ liệu", [("Màu nền hàng lẻ", "table_row_alt"),
                                  ("Màu header bảng", "table_header_bg"),
                                  ("Màu hàng được chọn", "table_selected")], "color_buttons_table"),
            ("Màu lãi nhuận / thua lỗ", [("Màu lãi nhuận", "profit_color"),
                                         ("Màu thua lỗ", "loss_color")], "color_buttons_pnl"),
            ("Màu biểu đồ", [("Nền biểu đồ", "chart_bg"), ("Màu lưới", "chart_grid"),
                             ("Màu chữ trục", "chart_text")], "color_buttons_chart"),
            ("Màu sắc biểu đồ (tối đa 5 màu)", [("Accent 1", "accent_1"),
                                                 ("Accent 2", "accent_2"),
                                                 ("Accent 3", "accent_3"),
                                                 ("Accent 4", "accent_4"),
                                                 ("Accent 5", "accent_5")], "color_buttons_accent"),
        ]:
            card = section(outer, section_title)
            btn_map = {}
            for label, key in color_map:
                r = ctk.CTkFrame(card, fg_color="transparent", height=38)
                r.pack(fill="x", padx=18, pady=2)
                r.pack_propagate(False)
                ctk.CTkLabel(r, text=label, width=200, anchor="w",
                             font=self._font(11),
                             text_color=s["text_color"]).pack(side="left")
                cb = ColorButton(r, color=s[key])
                cb.pack(side="right")
                btn_map[key] = cb
            setattr(self, attr_name, btn_map)

        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(6, 20))
        ctk.CTkButton(btn_row, text="Phục hồi mặc định", width=160, height=38,
                      corner_radius=8, fg_color=s["loss_color"], text_color="white",
                      font=self._font(12, True), hover_color="#c5221f",
                      command=self._reset_settings).pack(side="left")

    # ================================================================
    #  SETTINGS
    # ================================================================
    def _collect_settings_from_ui(self):
        s = dict(self.settings)
        s["font_family"] = self.set_font_family.get()
        s["font_size"] = int(self.set_font_size.get())
        for group in [self.color_buttons_main, self.color_buttons_table,
                      self.color_buttons_pnl, self.color_buttons_chart,
                      self.color_buttons_accent]:
            for k, cb in group.items():
                s[k] = cb.current_color
        return s

    def _apply_settings(self):
        self.settings = self._collect_settings_from_ui()
        save_settings_to_file(self.settings)
        self.configure(fg_color=self.settings["bg_color"])
        self.top_frame.configure(fg_color=self.settings["header_color"])
        for w in self.top_frame.winfo_children():
            if isinstance(w, ctk.CTkButton):
                w.configure(fg_color=self.settings["accent_2"])
        self.tab_view.configure(fg_color="transparent")
        style = ttk.Style()
        style.configure("Treeview", foreground=self.settings["text_color"],
                        font=self._tkfont(10))
        style.configure("Treeview.Heading",
                        background=self.settings["table_header_bg"],
                        foreground=self.settings["text_color"],
                        font=self._tkfont(10, True))
        style.map("Treeview",
                  background=[("selected", self.settings["table_selected"])])
        self.tree.tag_configure("profit", foreground=self.settings["profit_color"])
        self.tree.tag_configure("loss", foreground=self.settings["loss_color"])
        self.refresh_data()
        self.draw_chart()
        messagebox.showinfo("Thành công", "Đã lưu cài đặt!")

    def _reset_settings(self):
        self.settings = dict(DEFAULT_SETTINGS)
        save_settings_to_file(self.settings)
        self.configure(fg_color=self.settings["bg_color"])
        self.top_frame.configure(fg_color=self.settings["header_color"])
        for w in self.top_frame.winfo_children():
            if isinstance(w, ctk.CTkButton):
                w.configure(fg_color=self.settings["accent_2"])
        self.refresh_data()
        self.draw_chart()

    # ================================================================
    #  REFRESH - chi update du lieu, KHONG ve chart
    # ================================================================
    def refresh_data(self):
        self._refresh_summary()
        self._refresh_stock_list()
        self._refresh_combo()
        self._refresh_filter_buttons()
        self.load_history(None)

    def _refresh_summary(self):
        s = self.settings
        total_invest = 0
        total_value = 0
        for stk in self.data["stocks"]:
            latest = self.get_latest_price(stk["code"])
            total_invest += stk["buy_price"] * stk["qty"]
            total_value += (latest * stk["qty"]) if latest else 0

        profit = total_value - total_invest
        pct = (profit / total_invest * 100) if total_invest else 0
        pcolor = s["profit_color"] if profit >= 0 else s["loss_color"]

        vals = [
            ("Tổng đầu tư", fmt_vnd(total_invest * 1000, decimals=0), s["text_secondary"]),
            ("Giá trị hiện tại", fmt_vnd(total_value * 1000, decimals=0), s["header_color"]),
            ("Lợi nhuận", fmt_vnd(profit * 1000, sign=True, decimals=0), pcolor),
            ("Ty le", f"{pct:+.2f}%", pcolor),
        ]

        existing = self.summary_frame.winfo_children()
        if existing:
            row = existing[0]
            cards = row.winfo_children()
            for i, (title, value, color) in enumerate(vals):
                if i < len(cards):
                    lbls = cards[i].winfo_children()
                    if len(lbls) >= 2:
                        lbls[0].configure(text=title, text_color=s["text_secondary"])
                        lbls[1].configure(text=value, text_color=color)
        else:
            row = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=8)
            for title, value, color in vals:
                f = ctk.CTkFrame(row, fg_color=s["card_bg"], corner_radius=8)
                f.pack(side="left", expand=True, fill="x", padx=4)
                ctk.CTkLabel(f, text=title, font=self._font(8),
                             text_color=s["text_secondary"]).pack(pady=(4, 0))
                ctk.CTkLabel(f, text=value, font=self._font(11, True),
                             text_color=color).pack(pady=(0, 4))

    def _refresh_stock_list(self):
        for w in self.stock_frame.winfo_children():
            w.destroy()
        s = self.settings

        if not self.data["stocks"]:
            ctk.CTkLabel(self.stock_frame,
                         text="Chưa có mã nào.\nNhấn 'Thêm mã mới' để bắt đầu.",
                         font=self._font(12),
                         text_color=s["text_secondary"]).pack(pady=40)
            return

        accents = [s["accent_1"], s["accent_2"], s["accent_3"],
                   s["accent_4"], s["accent_5"]]
        for i, stk in enumerate(self.data["stocks"]):
            code = stk["code"]
            latest = self.get_latest_price(code)
            profit = (latest - stk["buy_price"]) * stk["qty"] if latest else 0
            pct = ((latest - stk["buy_price"]) / stk["buy_price"] * 100) if latest else 0
            pcolor = s["profit_color"] if profit >= 0 else s["loss_color"]
            bg = s["table_row_alt"] if i % 2 == 0 else s["card_bg"]
            color = accents[i % len(accents)]

            row = ctk.CTkFrame(self.stock_frame, fg_color=bg, corner_radius=6, height=38)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            ctk.CTkFrame(row, fg_color=color, width=4,
                         corner_radius=2).pack(side="left", fill="y",
                                               padx=(8, 6), pady=8)
            ctk.CTkLabel(row, text=code, width=45,
                         font=self._font(11, True),
                         text_color=color).pack(side="left")
            qty_frame = ctk.CTkFrame(row, fg_color="transparent", width=32)
            qty_frame.pack(side="left", padx=1)
            qty_frame.pack_propagate(False)
            qty_lbl = ctk.CTkLabel(qty_frame, text=f"{stk['qty']:,}",
                                    font=self._font(9), text_color=s["text_color"],
                                    anchor="w", cursor="hand2")
            qty_lbl.pack(fill="both", expand=True)
            qty_lbl.bind("<Button-1>",
                         lambda e, c=code, lbl=qty_lbl, fr=qty_frame:
                         self._start_edit_qty(c, lbl, fr))

            buy_frame = ctk.CTkFrame(row, fg_color="transparent", width=52)
            buy_frame.pack(side="left", padx=2)
            buy_frame.pack_propagate(False)
            buy_lbl = ctk.CTkLabel(buy_frame, text=f"{fmt(stk['buy_price'])}",
                                    font=self._font(11), text_color=s["text_color"],
                                    anchor="w", cursor="hand2")
            buy_lbl.pack(fill="both", expand=True)
            buy_lbl.bind("<Button-1>",
                         lambda e, c=code, lbl=buy_lbl, fr=buy_frame:
                         self._start_edit_buy(c, lbl, fr))

            price_frame = ctk.CTkFrame(row, fg_color="transparent", width=52)
            price_frame.pack(side="left", padx=2)
            price_frame.pack_propagate(False)
            price_text = fmt(latest) if latest else "--"
            price_lbl = ctk.CTkLabel(
                price_frame, text=price_text,
                font=self._font(9, True), text_color=s["text_color"] if latest else s["text_secondary"],
                anchor="w", cursor="hand2")
            price_lbl.pack(fill="both", expand=True)
            price_lbl.bind("<Button-1>",
                           lambda e, c=code, lbl=price_lbl, fr=price_frame:
                           self._start_edit_price(c, lbl, fr))

            profit_str = fmt_vnd(profit * 1000, sign=True, decimals=0) if latest else "--"
            ctk.CTkLabel(row, text=profit_str, width=65,
                         font=self._font(9, True),
                         text_color=pcolor if latest else s["text_secondary"]
                         ).pack(side="left")
            pct_str = f"{pct:+.2f}%" if latest else "--"
            ctk.CTkLabel(row, text=pct_str, width=35,
                         font=self._font(9),
                         text_color=pcolor if latest else s["text_secondary"]
                         ).pack(side="left")
            ctk.CTkButton(row, text="x", width=22, height=22, corner_radius=11,
                          fg_color=s["loss_color"], text_color="white",
                          font=self._font(9, True),
                          command=lambda c=code: self.delete_stock(c)
                          ).pack(side="right", padx=3)

    def _refresh_combo(self):
        codes = [s["code"] for s in self.data["stocks"]]
        self.hist_combo.configure(values=codes if codes else ["--"])

    def _refresh_filter_buttons(self):
        for w in self.filter_frame.winfo_children():
            w.destroy()
        s = self.settings
        codes = ["Tất cả"] + [s2["code"] for s2 in self.data["stocks"]]
        for c in codes:
            is_active = (self.chart_filter == c)
            btn = ctk.CTkButton(
                self.filter_frame, text=c, width=65, height=26, corner_radius=6,
                fg_color=s["header_color"] if is_active else s["table_header_bg"],
                text_color="white" if is_active else s["text_secondary"],
                font=self._font(10, True),
                hover_color="#1557b0" if is_active else s["chart_grid"],
                command=lambda val=c: self.set_chart_filter(val))
            btn.pack(side="left", padx=2)

    def set_chart_filter(self, val):
        self.chart_filter = val
        self._refresh_filter_buttons()
        self.draw_chart()

    # ================================================================
    #  EDIT IN PLACE
    # ================================================================
    def _normalize_nghin(self, val):
        if val > 100:
            return val / 1000.0
        return val

    def _start_edit_buy(self, code, label, frame):
        stk = next((s for s in self.data["stocks"] if s["code"] == code), None)
        if not stk:
            return
        label.pack_forget()
        entry = EditableEntry(frame, width=100, height=28, fg_color="white",
                              border_color=self.settings["header_color"],
                              font=self._font(11))
        entry.insert(0, fmt(stk["buy_price"]))
        entry.select_range(0, END)
        entry.configure(placeholder_text="nghìn VND")
        entry.pack(fill="both", expand=True)
        entry.focus()

        def confirm(val):
            try:
                new_val = float(val.strip())
                new_val = self._normalize_nghin(new_val)
                stk["buy_price"] = new_val
                save_data(self.data)
            except ValueError:
                pass
            entry.destroy()
            self.refresh_data()
        entry.on_confirm = confirm

    def _start_edit_price(self, code, label, frame):
        hist = self.data["history"].get(code, [])
        if not hist:
            return
        last = hist[-1]
        label.pack_forget()
        entry = EditableEntry(frame, width=100, height=28, fg_color="white",
                              border_color=self.settings["header_color"],
                              font=self._font(12, True))
        entry.insert(0, fmt(last["price"]))
        entry.select_range(0, END)
        entry.configure(placeholder_text="nghìn VND")
        entry.pack(fill="both", expand=True)
        entry.focus()

        def confirm(val):
            try:
                new_val = float(val.strip())
                new_val = self._normalize_nghin(new_val)
                last["price"] = new_val
                save_data(self.data)
            except ValueError:
                pass
            entry.destroy()
            self.refresh_data()
        entry.on_confirm = confirm

    def _start_edit_qty(self, code, label, frame):
        stk = next((s for s in self.data["stocks"] if s["code"] == code), None)
        if not stk:
            return
        label.pack_forget()
        entry = EditableEntry(frame, width=50, height=24, fg_color="white",
                              border_color=self.settings["header_color"],
                              font=self._font(9))
        entry.insert(0, str(stk["qty"]))
        entry.select_range(0, END)
        entry.pack(fill="both", expand=True)
        entry.focus()

        def confirm(val):
            try:
                new_val = int(val.strip())
                if new_val > 0:
                    stk["qty"] = new_val
                    save_data(self.data)
            except ValueError:
                pass
            entry.destroy()
            self.refresh_data()
        entry.on_confirm = confirm

    def get_latest_price(self, code):
        hist = self.data["history"].get(code, [])
        return hist[-1]["price"] if hist else None

    # ================================================================
    #  DIALOGS
    # ================================================================
    def add_stock_dialog(self):
        s = self.settings
        dlg = ctk.CTkToplevel(self)
        dlg.title("Thêm mã cổ phiếu")
        dlg.geometry("360x300")
        dlg.configure(fg_color=s["bg_color"])
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Thêm mã mới", font=self._font(16, True),
                     text_color=s["header_color"]).pack(pady=(18, 8))
        ctk.CTkLabel(dlg, text="Mã cổ phiếu", font=self._font(11),
                     text_color=s["text_secondary"]).pack(anchor="w", padx=35)
        code_e = ctk.CTkEntry(dlg, width=280, height=34, fg_color="white",
                              border_color=s["chart_grid"], placeholder_text="VD: CEO")
        code_e.pack(pady=(2, 8))
        ctk.CTkLabel(dlg, text="Số lượng", font=self._font(11),
                     text_color=s["text_secondary"]).pack(anchor="w", padx=35)
        qty_e = ctk.CTkEntry(dlg, width=280, height=34, fg_color="white",
                             border_color=s["chart_grid"], placeholder_text="VD: 1325")
        qty_e.pack(pady=(2, 8))
        ctk.CTkLabel(dlg, text="Giá mua (nghìn VND)", font=self._font(11),
                     text_color=s["text_secondary"]).pack(anchor="w", padx=35)
        price_e = ctk.CTkEntry(dlg, width=280, height=34, fg_color="white",
                               border_color=s["chart_grid"], placeholder_text="VD: 13.92")
        price_e.pack(pady=(2, 12))

        def confirm():
            code = code_e.get().strip().upper()
            try:
                qty = int(qty_e.get().strip())
                price = float(price_e.get().strip())
                price = self._normalize_nghin(price)
            except Exception:
                messagebox.showerror("Lỗi", "Nhập số hợp lệ!")
                return
            if not code:
                messagebox.showwarning("Cảnh báo", "Nhập mã CP!")
                return
            for st in self.data["stocks"]:
                if st["code"] == code:
                    messagebox.showwarning("Cảnh báo", f"{code} da ton tai!")
                    return
            self.data["stocks"].append({"code": code, "qty": qty, "buy_price": price})
            if code not in self.data["history"]:
                self.data["history"][code] = []
            save_data(self.data)
            self.refresh_data()
            self.draw_chart()
            dlg.destroy()

        ctk.CTkButton(dlg, text="THÊM VÀO DANH MỤC", width=280, height=40,
                      corner_radius=8, fg_color=s["header_color"], text_color="white",
                      font=self._font(12, True),
                      hover_color="#1557b0", command=confirm).pack()

    def delete_stock(self, code):
        if messagebox.askyesno("Xác nhận", f"Xoa {code} khoi danh muc?"):
            self.data["stocks"] = [s for s in self.data["stocks"] if s["code"] != code]
            self.data["history"].pop(code, None)
            save_data(self.data)
            self.refresh_data()
            self.draw_chart()

    def add_price_dialog(self):
        s = self.settings
        codes = [st["code"] for st in self.data["stocks"]]
        if not codes:
            messagebox.showwarning("Cảnh báo", "Hay them ma CP truoc!")
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Nhập giá theo phiên")
        dlg.geometry("360x280")
        dlg.configure(fg_color=s["bg_color"])
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Nhập giá đóng cửa",
                     font=self._font(16, True),
                     text_color=s["header_color"]).pack(pady=(18, 8))
        ctk.CTkLabel(dlg, text="Mã CP", font=self._font(11),
                     text_color=s["text_secondary"]).pack(anchor="w", padx=35)
        combo = ctk.CTkComboBox(dlg, values=codes, width=280, height=34,
                                fg_color="white", border_color=s["chart_grid"],
                                button_color=s["header_color"])
        combo.pack(pady=(2, 8))
        ctk.CTkLabel(dlg, text="Ngay (dd/mm/yyyy)", font=self._font(11),
                     text_color=s["text_secondary"]).pack(anchor="w", padx=35)
        date_e = ctk.CTkEntry(dlg, width=280, height=34, fg_color="white",
                              border_color=s["chart_grid"])
        date_e.insert(0, datetime.now().strftime("%d/%m/%Y"))
        date_e.pack(pady=(2, 8))
        ctk.CTkLabel(dlg, text="Giá đóng cửa (nghìn VND)", font=self._font(11),
                     text_color=s["text_secondary"]).pack(anchor="w", padx=35)
        price_e = ctk.CTkEntry(dlg, width=280, height=34, fg_color="white",
                               border_color=s["chart_grid"], placeholder_text="VD: 12.50")
        price_e.pack(pady=(2, 12))

        def confirm():
            code = combo.get()
            date_str = date_e.get().strip()
            try:
                price = float(price_e.get().strip())
                price = self._normalize_nghin(price)
                datetime.strptime(date_str, "%d/%m/%Y")
            except Exception:
                messagebox.showerror("Lỗi", "Ngay hoac gia khong hop le!")
                return
            if code not in self.data["history"]:
                self.data["history"][code] = []
            for h in self.data["history"][code]:
                if h["date"] == date_str:
                    h["price"] = price
                    save_data(self.data)
                    self.refresh_data()
                    self.draw_chart()
                    dlg.destroy()
                    return
            self.data["history"][code].append({"date": date_str, "price": price})
            self.data["history"][code].sort(
                key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y"))
            save_data(self.data)
            self.refresh_data()
            self.draw_chart()
            dlg.destroy()

        ctk.CTkButton(dlg, text="NHẬP GIÁ", width=280, height=40,
                      corner_radius=8, fg_color=s["accent_2"], text_color="white",
                      font=self._font(12, True),
                      hover_color="#2d9148", command=confirm).pack()

    def delete_price(self):
        code = self.hist_combo.get()
        if code == "--" or not code:
            return
        hist = self.data["history"].get(code, [])
        if not hist:
            return
        last = hist[-1]
        if messagebox.askyesno("Xác nhận",
                               f"Xoa phien {last['date']} - {fmt(last['price'])}?"):
            hist.pop()
            save_data(self.data)
            self.refresh_data()
            self.draw_chart()

    def quick_add_price(self):
        code = self.hist_combo.get()
        if code == "--" or not code:
            messagebox.showwarning("Cảnh báo", "Chọn mã CP trên lịch sử trước!")
            return
        date_str = self.add_date.get().strip()
        price_str = self.add_price_entry.get().strip()
        try:
            price = float(price_str)
            price = self._normalize_nghin(price)
            datetime.strptime(date_str, "%d/%m/%Y")
        except Exception:
            messagebox.showerror("Lỗi", "Nhap ngay va gia hop le!")
            return
        if code not in self.data["history"]:
            self.data["history"][code] = []
        for h in self.data["history"][code]:
            if h["date"] == date_str:
                h["price"] = price
                save_data(self.data)
                self.refresh_data()
                self.add_price_entry.delete(0, "end")
                return
        self.data["history"][code].append({"date": date_str, "price": price})
        self.data["history"][code].sort(
            key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y"))
        save_data(self.data)
        self.refresh_data()
        self.draw_chart()
        self.add_price_entry.delete(0, "end")

    # ================================================================
    #  HISTORY TABLE
    # ================================================================
    def load_history(self, event):
        for item in self.tree.get_children():
            self.tree.delete(item)
        code = self.hist_combo.get()
        if code == "--" or not code:
            return
        stk = next((s for s in self.data["stocks"] if s["code"] == code), None)
        if not stk:
            return

        hist = self.data["history"].get(code, [])
        buy = stk["buy_price"]
        qty = stk["qty"]
        s = self.settings

        for i in range(len(hist) - 1, -1, -1):
            h = hist[i]
            price = h["price"]
            prev = hist[i - 1]["price"] if i > 0 else price
            change = price - prev
            profit = (price - buy) * qty
            pct = ((price - buy) / buy * 100)
            tag = "profit" if profit >= 0 else "loss"
            self.tree.insert("", "end",
                             values=(h["date"], f"{fmt(price)}",
                                     fmt_vnd(change * 1000, sign=True, decimals=0), fmt_vnd(profit * 1000, sign=True, decimals=0),
                                     f"{pct:+.2f}%"),
                             tags=(tag,))

        self.tree.tag_configure("profit", foreground=s["profit_color"])
        self.tree.tag_configure("loss", foreground=s["loss_color"])

    def _on_tree_double_click(self, event):
        self._edit_selected_price()

    def _edit_selected_price(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Chọn 1 dòng trong lịch sử trước!")
            return
        item = self.tree.item(sel[0])
        vals = item["values"]
        if not vals:
            return
        date_str = str(vals[0])
        old_price_str = str(vals[1]).replace(".", "").replace(",", ".")
        try:
            old_price = float(old_price_str)
        except ValueError:
            old_price = 0.0
        self._edit_price_dialog(date_str, old_price)

    def _on_tree_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self._edit_selected_price()

    def _edit_price_dialog(self, date_str, old_price):
        code = self.hist_combo.get()
        if code == "--" or not code:
            return
        s = self.settings
        dlg = tk.Toplevel(self)
        dlg.title("Sửa giá")
        dlg.geometry("340x220")
        dlg.configure(bg=s["bg_color"])
        dlg.transient(self)
        dlg.grab_set()
        dlg.lift()
        dlg.focus_force()

        tk.Label(dlg, text="Sửa giá đóng cửa",
                 font=("Segoe UI", 14, "bold"),
                 fg=s["header_color"], bg=s["bg_color"]).pack(pady=(16, 6))
        tk.Label(dlg, text=f"Ngày: {date_str}  |  Mã: {code}",
                 font=("Segoe UI", 11),
                 fg=s["text_secondary"], bg=s["bg_color"]).pack(pady=(0, 8))
        tk.Label(dlg, text="Giá mới (nghìn VND)",
                 font=("Segoe UI", 11),
                 fg=s["text_secondary"], bg=s["bg_color"]).pack(anchor="w", padx=35)
        price_e = tk.Entry(dlg, width=28, font=("Segoe UI", 11),
                           relief="solid", bd=1)
        price_e.insert(0, fmt(old_price))
        price_e.pack(pady=(2, 12))
        price_e.select_range(0, tk.END)
        price_e.focus()

        def confirm():
            try:
                price = float(price_e.get().strip().replace(",", "."))
                price = self._normalize_nghin(price)
            except Exception:
                messagebox.showerror("Lỗi", "Giá không hợp lệ!")
                return
            hist = self.data["history"].get(code, [])
            for h in hist:
                if h["date"] == date_str:
                    h["price"] = price
                    save_data(self.data)
                    self.refresh_data()
                    self.draw_chart()
                    dlg.destroy()
                    return
            messagebox.showwarning("Cảnh báo", "Không tìm thấy ngày này trong lịch sử!")

        tk.Button(dlg, text="LƯU", width=30, height=2,
                  font=("Segoe UI", 11, "bold"),
                  bg=s["accent_2"], fg="white",
                  activebackground="#2d9148",
                  relief="flat", command=confirm).pack()

    # ================================================================
    #  CHART (chi ve khi filter thay doi hoac them/xoa du lieu)
    # ================================================================
    def draw_chart(self):
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm
        import matplotlib.ticker as mticker
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        for w in self.chart_frame.winfo_children():
            w.destroy()
        s = self.settings

        if not self.data["stocks"]:
            ctk.CTkLabel(self.chart_frame, text="Thêm mã CP để xem biểu đồ",
                         font=self._font(12),
                         text_color=s["text_secondary"]).pack(expand=True)
            return

        show_stocks = self.data["stocks"] if self.chart_filter == "Tất cả" else [
            st for st in self.data["stocks"] if st["code"] == self.chart_filter]
        if not show_stocks:
            ctk.CTkLabel(self.chart_frame, text="Không có dữ liệu",
                         font=self._font(12),
                         text_color=s["text_secondary"]).pack(expand=True)
            return

        all_dates = set()
        for stk in show_stocks:
            for h in self.data["history"].get(stk["code"], []):
                all_dates.add(h["date"])
        all_dates = sorted(all_dates, key=lambda x: datetime.strptime(x, "%d/%m/%Y"))
        if not all_dates:
            ctk.CTkLabel(self.chart_frame, text="Nhập giá để xem biểu đồ",
                         font=self._font(12),
                         text_color=s["text_secondary"]).pack(expand=True)
            return

        n_dates = len(all_dates)
        n_stocks = len(show_stocks)
        chart_colors = [s["accent_1"], s["accent_2"], s["accent_3"],
                        s["accent_4"], s["accent_5"]]
        bar_w = 0.7 if n_stocks == 1 else max(0.15, 0.6 / n_stocks)

        fig = Figure(figsize=(7.5, 3.5), dpi=100, facecolor=s["chart_bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(s["chart_bg"])
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color(s["chart_grid"])
        ax.spines["left"].set_color(s["chart_grid"])
        ax.tick_params(colors=s["chart_text"], labelsize=8)
        ax.axhline(y=0, color="#999", linewidth=0.8)

        for i, stk in enumerate(show_stocks):
            code = stk["code"]
            buy = stk["buy_price"]
            qty = stk["qty"]
            hist = self.data["history"].get(code, [])
            price_map = {h["date"]: h["price"] for h in hist}
            profits, positions = [], []
            for j, d in enumerate(all_dates):
                if d in price_map:
                    profits.append((price_map[d] - buy) * qty)
                    if n_stocks == 1:
                        positions.append(j)
                    else:
                        positions.append(j + i * bar_w - (n_stocks - 1) * bar_w / 2)
            if profits:
                color = chart_colors[i % len(chart_colors)]
                bars = ax.bar(positions, profits, width=bar_w, label=code,
                              color=color, alpha=0.85, edgecolor=color, linewidth=0.5)
                for bar, val in zip(bars, profits):
                    y = bar.get_height()
                    rng = max(abs(max(profits, default=1)),
                              abs(min(profits, default=1)))
                    offset = rng * 0.03
                    va = "bottom" if val >= 0 else "top"
                    ax.text(bar.get_x() + bar.get_width() / 2.,
                            y + (offset if val >= 0 else -offset),
                            fmt_vnd(val, sign=True, decimals=0), ha="center", va=va,
                            fontsize=5.5, color=color, fontweight="bold")

        ax.set_xticks(list(range(n_dates)))
        ax.set_xticklabels([d[:5] for d in all_dates],
                           rotation=45, fontsize=7, color=s["chart_text"])
        title = "Lãi/Lỗ so với giá gốc"
        if self.chart_filter != "Tất cả":
            title += f" - {self.chart_filter}"
        ax.set_title(title, fontsize=11, fontweight="bold",
                     color=s["text_color"], pad=8)
        if n_stocks > 1:
            ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1),
                      fontsize=8, framealpha=0.9, edgecolor=s["chart_grid"],
                      borderaxespad=0)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, p: fmt_vnd(x, sign=True, decimals=0)))
        fig.subplots_adjust(left=0.08, right=0.82, top=0.92, bottom=0.18)
        fig.tight_layout(pad=1.0)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    app = StockApp()
    app.mainloop()
