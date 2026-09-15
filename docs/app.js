const DB_KEY = 'stock_tracker_data';
const DEFAULT_DATA = { stocks: [], history: {} };

function loadData() {
    try {
        const raw = localStorage.getItem(DB_KEY);
        return raw ? JSON.parse(raw) : { ...DEFAULT_DATA };
    } catch { return { ...DEFAULT_DATA }; }
}

function saveData(data) {
    localStorage.setItem(DB_KEY, JSON.stringify(data));
}

function fmt(v) {
    return v.toLocaleString('vi-VN', { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

function fmtVND(v, sign = false) {
    const abs = Math.abs(Math.round(v));
    const s = abs.toLocaleString('vi-VN');
    if (v < 0) return '-' + s;
    if (sign && v > 0) return '+' + s;
    return s;
}

function normalizeNghin(val) {
    return val > 100 ? val / 1000 : val;
}

function getLatestPrice(data, code) {
    const hist = data.history[code] || [];
    return hist.length ? hist[hist.length - 1].price : null;
}

const chartLabelsPlugin = {
    id: 'chartLabels',
    afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        const yScale = chart.scales.y;
        chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            meta.data.forEach((bar, index) => {
                const value = dataset.data[index];
                if (value === null || value === undefined) return;
                const text = fmtVND(value, true);
                const yPos = yScale.getPixelForValue(value);
                ctx.save();
                ctx.font = 'bold 9px -apple-system, sans-serif';
                ctx.fillStyle = dataset.borderColor;
                ctx.textAlign = 'center';
                const x = bar.x;
                if (value >= 0) {
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(text, x, yPos - 6);
                } else {
                    ctx.textBaseline = 'top';
                    ctx.fillText(text, x, yPos + 6);
                }
                ctx.restore();
            });
        });
    }
};

let chart = null;

function renderAll() {
    const data = loadData();
    renderSummary(data);
    renderStockList(data);
    renderHistory(data);
    renderChart(data);
}

function renderSummary(data) {
    let totalInvest = 0, totalValue = 0;
    data.stocks.forEach(stk => {
        const latest = getLatestPrice(data, stk.code);
        totalInvest += stk.buy_price * stk.qty;
        totalValue += (latest ? latest * stk.qty : 0);
    });
    const profit = totalValue - totalInvest;
    const pct = totalInvest ? (profit / totalInvest * 100) : 0;
    const color = profit >= 0 ? 'var(--profit)' : 'var(--loss)';

    document.getElementById('sum-invest').textContent = fmtVND(totalInvest * 1000);
    document.getElementById('sum-value').textContent = fmtVND(totalValue * 1000);
    document.getElementById('sum-profit').textContent = fmtVND(profit * 1000, true);
    document.getElementById('sum-profit').style.color = color;
    document.getElementById('sum-pct').textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
    document.getElementById('sum-pct').style.color = color;
}

function renderStockList(data) {
    const el = document.getElementById('stock-list');
    if (!data.stocks.length) {
        el.innerHTML = '<div class="empty">Chưa có mã CP nào</div>';
        return;
    }
    el.innerHTML = data.stocks.map(stk => {
        const latest = getLatestPrice(data, stk.code);
        const pnl = latest ? (latest - stk.buy_price) * stk.qty : 0;
        const pct = latest ? ((latest - stk.buy_price) / stk.buy_price * 100) : 0;
        const cls = latest ? (pnl >= 0 ? 'profit' : 'loss') : '';
        return `<div class="stock-row">
            <div class="stock-code">${stk.code}</div>
            <div class="stock-qty" onclick="editStockField('${stk.code}','qty',this)" style="cursor:pointer" title="Click để sửa">${stk.qty.toLocaleString('vi-VN')}</div>
            <div class="stock-buy" onclick="editStockField('${stk.code}','buy_price',this)" style="cursor:pointer" title="Click để sửa">${fmt(stk.buy_price)}</div>
            <div class="stock-price">${latest ? fmt(latest) : '--'}</div>
            <div class="stock-pnl ${cls}">${latest ? fmtVND(pnl * 1000, true) : '--'}</div>
            <div class="stock-pct ${cls}">${latest ? (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%' : '--'}</div>
            <button class="btn-icon btn-del" onclick="deleteStock('${stk.code}')">Xóa</button>
        </div>`;
    }).join('');

    const sel = document.getElementById('hist-code');
    sel.innerHTML = data.stocks.map(s => `<option value="${s.code}">${s.code}</option>`).join('');
    sel.onchange = () => renderHistory(data);
}

function renderHistory(data) {
    const code = document.getElementById('hist-code').value;
    const stk = data.stocks.find(s => s.code === code);
    const hist = (data.history[code] || []).slice().reverse();
    const table = document.getElementById('hist-table');

    if (!code || !stk || !hist.length) {
        table.innerHTML = '<div class="empty">Chọn mã CP để xem lịch sử</div>';
        return;
    }

    const rows = hist.map((h, idx) => {
        const i = hist.length - 1 - idx;
        const origIdx = (data.history[code].length - 1) - idx;
        const prev = origIdx > 0 ? data.history[code][origIdx - 1].price : h.price;
        const change = h.price - prev;
        const pnl = (h.price - stk.buy_price) * stk.qty;
        const pct = (h.price - stk.buy_price) / stk.buy_price * 100;
        const cls = pnl >= 0 ? 'profit' : 'loss';
        return `<div class="hist-row" onclick="editPrice('${code}','${h.date}',${h.price})">
            <span class="h-date">${h.date}</span>
            <span class="h-price">${fmt(h.price)}</span>
            <span class="h-change ${change >= 0 ? 'profit' : 'loss'}">${fmtVND(change * 1000, true)}</span>
            <span class="h-pnl ${cls}">${fmtVND(pnl * 1000, true)}</span>
            <span class="h-pct ${cls}">${(pct >= 0 ? '+' : '') + pct.toFixed(2)}%</span>
        </div>`;
    });
    table.innerHTML = rows.join('');
}

function renderChart(data) {
    const filter = document.getElementById('chart-filter').value;
    const showStocks = filter === 'all' ? data.stocks : data.stocks.filter(s => s.code === filter);

    const allDates = new Set();
    showStocks.forEach(stk => {
        (data.history[stk.code] || []).forEach(h => allDates.add(h.date));
    });
    const dates = [...allDates].sort((a, b) => {
        const [da, ma, ya] = a.split('/').map(Number);
        const [db, mb, yb] = b.split('/').map(Number);
        return new Date(ya, ma - 1, da) - new Date(yb, mb - 1, db);
    });

    if (!dates.length || !showStocks.length) {
        if (chart) { chart.destroy(); chart = null; }
        return;
    }

    const colors = ['#1a73e8', '#34a853', '#fbbc04', '#9334e6', '#ff6d01'];
    const datasets = showStocks.map((stk, i) => {
        const priceMap = {};
        (data.history[stk.code] || []).forEach(h => priceMap[h.date] = h.price);
        const profits = dates.map(d => {
            const p = priceMap[d];
            return p ? (p - stk.buy_price) * stk.qty * 1000 : null;
        });
        return {
            label: stk.code,
            data: profits,
            backgroundColor: colors[i % colors.length] + 'cc',
            borderColor: colors[i % colors.length],
            borderWidth: 1,
            borderRadius: 3
        };
    });

    const ctx = document.getElementById('chart').getContext('2d');
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
        type: 'bar',
        plugins: [chartLabelsPlugin],
        data: {
            labels: dates.map(d => d.substring(0, 5)),
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 20 } },
            plugins: {
                legend: { display: showStocks.length > 1, position: 'top', align: 'end' },
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.dataset.label + ': ' + fmtVND(ctx.raw, true) + ' VND'
                    }
                },
                datalabels: {
                    display: false
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: v => fmtVND(v, true)
                    },
                    grid: { color: '#e0e0e0' }
                },
                x: { grid: { display: false } }
            }
        }
    });
}

function addStock() {
    const code = document.getElementById('new-code').value.trim().toUpperCase();
    const qty = parseInt(document.getElementById('new-qty').value);
    const price = normalizeNghin(parseFloat(document.getElementById('new-price').value));

    if (!code) { alert('Nhập mã CP!'); return; }
    if (!qty || qty <= 0) { alert('Số lượng không hợp lệ!'); return; }
    if (isNaN(price) || price <= 0) { alert('Giá không hợp lệ!'); return; }

    const data = loadData();
    if (data.stocks.find(s => s.code === code)) {
        alert(code + ' đã tồn tại!');
        return;
    }
    data.stocks.push({ code, qty, buy_price: price });
    if (!data.history[code]) data.history[code] = [];
    saveData(data);
    document.getElementById('new-code').value = '';
    document.getElementById('new-qty').value = '100';
    document.getElementById('new-price').value = '';
    renderAll();
}

function deleteStock(code) {
    if (!confirm('Xóa ' + code + ' khỏi danh mục?')) return;
    const data = loadData();
    data.stocks = data.stocks.filter(s => s.code !== code);
    delete data.history[code];
    saveData(data);
    renderAll();
}

function editStockField(code, field, el) {
    const data = loadData();
    const stk = data.stocks.find(s => s.code === code);
    if (!stk) return;
    const oldVal = stk[field];
    const input = document.createElement('input');
    input.type = 'number';
    input.step = field === 'qty' ? '1' : '0.001';
    input.value = oldVal;
    input.style.cssText = 'width:80px;padding:2px 4px;border:2px solid var(--primary);border-radius:4px;font-size:13px;text-align:center;';
    el.textContent = '';
    el.appendChild(input);
    input.focus();
    input.select();
    const confirm = () => {
        let newVal = parseFloat(input.value);
        if (isNaN(newVal) || newVal <= 0) { newVal = oldVal; }
        if (field === 'qty') newVal = Math.round(newVal);
        else newVal = normalizeNghin(newVal);
        stk[field] = newVal;
        saveData(data);
        renderAll();
    };
    input.addEventListener('blur', confirm);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') confirm(); if (e.key === 'Escape') renderAll(); });
}

function addPrice() {
    const code = document.getElementById('hist-code').value;
    if (!code) { alert('Chọn mã CP!'); return; }
    const dateInput = document.getElementById('add-date').value;
    const price = normalizeNghin(parseFloat(document.getElementById('add-price').value));
    if (!dateInput || isNaN(price)) { alert('Nhập ngày và giá hợp lệ!'); return; }

    const [y, m, d] = dateInput.split('-');
    const dateStr = `${d}/${m}/${y}`;

    const data = loadData();
    if (!data.history[code]) data.history[code] = [];

    const existing = data.history[code].find(h => h.date === dateStr);
    if (existing) {
        existing.price = price;
    } else {
        data.history[code].push({ date: dateStr, price });
        data.history[code].sort((a, b) => {
            const [da, ma, ya] = a.date.split('/').map(Number);
            const [db, mb, yb] = b.date.split('/').map(Number);
            return new Date(ya, ma - 1, da) - new Date(yb, mb - 1, db);
        });
    }
    saveData(data);
    document.getElementById('add-price').value = '';
    renderAll();
}

function deleteLastPrice() {
    const code = document.getElementById('hist-code').value;
    if (!code) return;
    const data = loadData();
    const hist = data.history[code];
    if (!hist || !hist.length) return;
    const last = hist[hist.length - 1];
    if (!confirm(`Xóa phiên ${last.date} - ${fmt(last.price)}?`)) return;
    hist.pop();
    saveData(data);
    renderAll();
}

function editPrice(code, date, oldPrice) {
    const newPrice = prompt(`Sửa giá ${date}\nGiá cũ: ${fmt(oldPrice)}\nGiá mới (nghìn VND):`, oldPrice);
    if (newPrice === null) return;
    const price = normalizeNghin(parseFloat(newPrice));
    if (isNaN(price)) { alert('Giá không hợp lệ!'); return; }

    const data = loadData();
    const hist = data.history[code];
    if (hist) {
        const h = hist.find(x => x.date === date);
        if (h) { h.price = price; saveData(data); renderAll(); }
    }
}

function exportData() {
    const data = loadData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'stock_data.json';
    a.click();
}

function importData(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        try {
            const imported = JSON.parse(e.target.result);
            if (imported.stocks && imported.history) {
                saveData(imported);
                renderAll();
                alert('Import thành công!');
            } else {
                alert('File JSON không hợp lệ!');
            }
        } catch { alert('Lỗi đọc file!'); }
    };
    reader.readAsText(file);
}

function updateChartFilter() {
    const data = loadData();
    const sel = document.getElementById('chart-filter');
    sel.innerHTML = '<option value="all">Tất cả</option>' +
        data.stocks.map(s => `<option value="${s.code}">${s.code}</option>`).join('');
    sel.onchange = () => renderChart(data);
}

document.addEventListener('DOMContentLoaded', () => {
    renderAll();
    updateChartFilter();
});
