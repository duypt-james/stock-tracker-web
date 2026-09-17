const DB_KEY = 'stock_tracker_data';
const DEFAULT_DATA = { stocks: [], history: {} };

const GH_TOKEN_KEY = 'stock_tracker_gh_token';
const GH_REPO_KEY = 'stock_tracker_gh_repo';
const GH_FILE_KEY = 'stock_tracker_gh_file';
const GH_SHA_KEY = 'stock_tracker_gh_sha';

function getGitHubConfig() {
    return {
        token: localStorage.getItem(GH_TOKEN_KEY) || '',
        repo: localStorage.getItem(GH_REPO_KEY) || 'duypt-james/stock-tracker-web',
        file: localStorage.getItem(GH_FILE_KEY) || 'stock_data.json',
        sha: localStorage.getItem(GH_SHA_KEY) || ''
    };
}

function saveGitHubConfig(cfg) {
    if (cfg.token !== undefined) localStorage.setItem(GH_TOKEN_KEY, cfg.token);
    if (cfg.repo !== undefined) localStorage.setItem(GH_REPO_KEY, cfg.repo);
    if (cfg.file !== undefined) localStorage.setItem(GH_FILE_KEY, cfg.file);
    if (cfg.sha !== undefined) localStorage.setItem(GH_SHA_KEY, cfg.sha);
}

function setSyncStatus(text, color) {
    const el = document.getElementById('sync-status');
    if (el) {
        el.textContent = text;
        el.style.color = color || 'var(--text2)';
    }
}

async function fetchFromGitHub() {
    const cfg = getGitHubConfig();
    if (!cfg.token) return null;
    try {
        const res = await fetch(`https://api.github.com/repos/${cfg.repo}/contents/${cfg.file}`, {
            headers: { 'Authorization': 'token ' + cfg.token, 'Accept': 'application/vnd.github.v3+json' }
        });
        if (!res.ok) return null;
        const json = await res.json();
        const content = decodeURIComponent(escape(atob(json.content)));
        saveGitHubConfig({ sha: json.sha });
        return JSON.parse(content);
    } catch (e) {
        console.error('GitHub fetch error:', e);
        return null;
    }
}

async function pushToGitHub(data) {
    const cfg = getGitHubConfig();
    if (!cfg.token) return false;
    try {
        const body = JSON.stringify(data, null, 2);
        const encoded = btoa(unescape(encodeURIComponent(body)));
        const payload = { message: 'Update stock_data.json from Stock Tracker', content: encoded };
        if (cfg.sha) payload.sha = cfg.sha;

        console.log('GitHub push: sha=' + cfg.sha, 'repo=' + cfg.repo, 'file=' + cfg.file);
        const res = await fetch(`https://api.github.com/repos/${cfg.repo}/contents/${cfg.file}`, {
            method: 'PUT',
            headers: {
                'Authorization': 'token ' + cfg.token,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        console.log('GitHub push response:', res.status, json);

        if (res.ok) {
            saveGitHubConfig({ sha: json.content.sha });
            return true;
        } else {
            console.error('GitHub push failed:', json.message);
            if (res.status === 422) {
                console.log('SHA conflict - re-fetching...');
                const fresh = await fetchFromGitHub();
                if (fresh) {
                    const retry = await pushToGitHub(data);
                    return retry;
                }
            }
            return false;
        }
    } catch (e) {
        console.error('GitHub push error:', e);
        return false;
    }
}

let _syncing = false;
let _loadingFromGitHub = false;

async function syncToGitHub(data) {
    if (_syncing || _loadingFromGitHub) return;
    _syncing = true;
    setSyncStatus('Đang sync...', '#f57c00');
    const ok = await pushToGitHub(data);
    if (ok) {
        setSyncStatus('Đã sync', 'var(--profit)');
    } else {
        const cfg = getGitHubConfig();
        setSyncStatus('Lỗi sync! Kiểm tra token/repo', 'var(--loss)');
        console.error('Sync failed. Config:', cfg);
    }
    _syncing = false;
    setTimeout(() => setSyncStatus(''), 5000);
}

function loadData() {
    try {
        const raw = localStorage.getItem(DB_KEY);
        return raw ? JSON.parse(raw) : { ...DEFAULT_DATA };
    } catch { return { ...DEFAULT_DATA }; }
}

function saveData(data) {
    localStorage.setItem(DB_KEY, JSON.stringify(data));
    const cfg = getGitHubConfig();
    if (cfg.token) syncToGitHub(data);
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
        const showLabels = document.getElementById('show-labels');
        if (showLabels && !showLabels.checked) return;
        const ctx = chart.ctx;
        const yScale = chart.scales.y;
        const isPct = document.getElementById('chart-unit') && document.getElementById('chart-unit').value === 'pct';
        chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            meta.data.forEach((bar, index) => {
                const value = dataset.data[index];
                if (value === null || value === undefined) return;
                const text = isPct ? value.toFixed(2) + '%' : fmtVND(value, true);
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
let pieChart = null;
let capitalChart = null;

function renderAll() {
    const data = loadData();
    renderSummary(data);
    renderStockList(data);
    renderHistory(data);
    renderChart(data);
    renderPieChart(data);
    renderCapitalChart(data);
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

    const avgSel = document.getElementById('avg-code');
    avgSel.innerHTML = data.stocks.map(s => `<option value="${s.code}">${s.code}</option>`).join('');
    avgSel.onchange = () => renderAvgPrice();
    renderAvgPrice();
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

function renderAvgPrice() {
    const code = document.getElementById('avg-code').value;
    const data = loadData();
    const stk = data.stocks.find(s => s.code === code);

    if (!stk) {
        document.getElementById('avg-tbody').innerHTML = '<tr><td colspan="6" style="text-align:center;padding:16px;color:var(--text2)">Chọn mã CP</td></tr>';
        return;
    }

    const boughtQty = stk.qty;
    const boughtPrice = stk.buy_price;
    const newQty = parseInt(document.getElementById('avg-new-qty-input').value) || 0;
    const newPrice = parseFloat(document.getElementById('avg-new-price-input').value) || 0;
    const totalQty = boughtQty + newQty;
    const avgPrice = totalQty > 0 ? ((boughtQty * boughtPrice) + (newQty * newPrice)) / totalQty : 0;

    document.getElementById('avg-tbody').innerHTML = `
        <tr>
            <td style="padding:8px 12px;font-weight:600">${boughtQty.toLocaleString('vi-VN')}</td>
            <td style="padding:8px 12px;text-align:right;font-weight:600">${fmt(boughtPrice)}</td>
            <td style="padding:8px 12px;color:var(--primary)">${newQty ? newQty.toLocaleString('vi-VN') : '-'}</td>
            <td style="padding:8px 12px;text-align:right;color:var(--primary)">${newPrice ? fmt(newPrice) : '-'}</td>
            <td style="padding:8px 12px;border-left:2px solid var(--border);font-weight:700">${totalQty.toLocaleString('vi-VN')}</td>
            <td style="padding:8px 12px;text-align:right;font-weight:700;color:var(--primary);font-size:15px">${newQty && newPrice ? fmt(avgPrice) : fmt(boughtPrice)}</td>
        </tr>
    `;

    document.getElementById('avg-bought-qty').textContent = boughtQty.toLocaleString('vi-VN');
    document.getElementById('avg-bought-price').textContent = fmt(boughtPrice);
    document.getElementById('avg-new-qty').textContent = newQty ? newQty.toLocaleString('vi-VN') : '-';
    document.getElementById('avg-new-price').textContent = newPrice ? fmt(newPrice) : '-';
    document.getElementById('avg-total-qty').textContent = totalQty.toLocaleString('vi-VN');
    document.getElementById('avg-result').textContent = newQty && newPrice ? fmt(avgPrice) : fmt(boughtPrice);
}

const capitalLabelsPlugin = {
    id: 'capitalLabels',
    afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        const yScale = chart.scales.y;
        chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            meta.data.forEach((bar, index) => {
                const value = dataset.data[index];
                if (value === null || value === undefined) return;
                const text = fmtVND(value * 1000, true);
                const yPos = yScale.getPixelForValue(value);
                ctx.save();
                ctx.font = 'bold 9px -apple-system, sans-serif';
                ctx.fillStyle = dataset.borderColor;
                ctx.textAlign = 'center';
                if (value >= 0) {
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(text, bar.x, yPos - 4);
                } else {
                    ctx.textBaseline = 'top';
                    ctx.fillText(text, bar.x, yPos + 4);
                }
                ctx.restore();
            });
        });
    }
};

function renderCapitalChart(data) {
    const canvas = document.getElementById('capital-chart');
    if (!canvas) return;
    if (!data.stocks.length) { if (capitalChart) { capitalChart.destroy(); capitalChart = null; } return; }

    const colors = ['#1a73e8', '#34a853', '#fbbc04', '#9334e6', '#ff6d01'];
    const labels = data.stocks.map(s => s.code);
    const capitalData = data.stocks.map(s => s.buy_price * s.qty);
    const profitData = data.stocks.map(s => {
        const latest = getLatestPrice(data, s.code);
        return latest ? (latest - s.buy_price) * s.qty : 0;
    });

    const ctx = canvas.getContext('2d');
    if (capitalChart) capitalChart.destroy();
    capitalChart = new Chart(ctx, {
        type: 'bar',
        plugins: [capitalLabelsPlugin],
        data: {
            labels,
            datasets: [
                {
                    label: 'Vốn',
                    data: capitalData,
                    backgroundColor: colors.map(c => c + 'cc'),
                    borderColor: colors,
                    borderWidth: 1,
                    borderRadius: 3
                },
                {
                    label: 'Lãi/Lỗ',
                    data: profitData,
                    backgroundColor: profitData.map(v => v >= 0 ? '#34a853cc' : '#ea4335cc'),
                    borderColor: profitData.map(v => v >= 0 ? '#34a853' : '#ea4335'),
                    borderWidth: 1,
                    borderRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 24, bottom: 4 } },
            plugins: {
                legend: { display: true, position: 'top', align: 'end', labels: { boxWidth: 12, font: { size: 10 } } },
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.dataset.label + ': ' + fmtVND(ctx.raw * 1000, true) + ' VND'
                    }
                },
                datalabels: { display: false }
            },
            scales: {
                y: {
                    ticks: { callback: v => fmtVND(v * 1000, true), font: { size: 9 } },
                    grid: { color: '#e0e0e0' }
                },
                x: { grid: { display: false }, ticks: { font: { size: 10, weight: 'bold' } } }
            }
        }
    });
}

function renderPieChart(data) {
    const canvas = document.getElementById('pie-chart');
    if (!canvas) return;
    if (!data.stocks.length) { if (pieChart) { pieChart.destroy(); pieChart = null; } return; }

    const colors = ['#1a73e8', '#34a853', '#fbbc04', '#9334e6', '#ff6d01'];
    const labels = data.stocks.map(s => s.code);
    const values = data.stocks.map(s => s.buy_price * s.qty);
    const total = values.reduce((a, b) => a + b, 0);
    const bgColors = data.stocks.map((_, i) => colors[i % colors.length]);

    const ctx = canvas.getContext('2d');
    if (pieChart) pieChart.destroy();
    pieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: bgColors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '55%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const pct = ((ctx.raw / total) * 100).toFixed(1);
                            return ctx.label + ': ' + fmtVND(ctx.raw * 1000) + ' (' + pct + '%)';
                        }
                    }
                },
                datalabels: { display: false }
            }
        },
        plugins: []
    });

    const legendEl = document.getElementById('pie-legend');
    if (legendEl) {
        legendEl.innerHTML = data.stocks.map((s, i) => {
            const pct = ((values[i] / total) * 100).toFixed(1);
            return `<span style="margin-right:10px"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${bgColors[i]};margin-right:3px"></span>${s.code} ${pct}%</span>`;
        }).join('');
    }
}

function renderChart(data) {
    const filter = document.getElementById('chart-filter').value;
    const unit = document.getElementById('chart-unit') ? document.getElementById('chart-unit').value : 'vnd';
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

    const isPct = unit === 'pct';
    const colors = ['#1a73e8', '#34a853', '#fbbc04', '#9334e6', '#ff6d01'];
    const datasets = showStocks.map((stk, i) => {
        const priceMap = {};
        (data.history[stk.code] || []).forEach(h => priceMap[h.date] = h.price);
        const profits = dates.map(d => {
            const p = priceMap[d];
            if (!p) return null;
            if (isPct) return ((p - stk.buy_price) / stk.buy_price * 100);
            return (p - stk.buy_price) * stk.qty * 1000;
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
                        label: ctx => {
                            if (isPct) return ctx.dataset.label + ': ' + ctx.raw.toFixed(2) + '%';
                            return ctx.dataset.label + ': ' + fmtVND(ctx.raw, true) + ' VND';
                        }
                    }
                },
                datalabels: {
                    display: false
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: v => isPct ? v.toFixed(0) + '%' : fmtVND(v, true)
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
    const current = sel.value;
    sel.innerHTML = '<option value="all">Tất cả</option>' +
        data.stocks.map(s => `<option value="${s.code}">${s.code}</option>`).join('');
    if (data.stocks.find(s => s.code === current)) {
        sel.value = current;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateChartFilter();
    renderAll();
});
