/**
 * Smart Kirana Enterprise - Dynamic Commodity 3-Way Audit Engine (audit_engine.js)
 * Replaces restrictive session-only dropdown with dynamic commodity search,
 * autocomplete, on-the-fly APMC/Gemini grounding for unlisted items,
 * and 4-tier comparative audit analysis.
 */

const AuditEngine = (function () {
  let commodityList = [];
  let isAuditing = false;

  function formatINR(val) {
    if (val === null || val === undefined || isNaN(val)) return '₹0.00';
    const num = parseFloat(val);
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  const DEV_DIGITS = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'];
  function toDevDigits(val) {
    if (val === null || val === undefined) return '';
    return String(val).replace(/[0-9]/g, d => DEV_DIGITS[d]);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function init() {
    await loadHistoricalCommodities();
    bindEvents();

    // Check if query params contain a commodity or session to audit on load
    const params = new URLSearchParams(window.location.search);
    const commParam = params.get('commodity');
    const sessParam = params.get('session_id');

    if (commParam) {
      const input = document.getElementById('audit-commodity-input');
      if (input) input.value = commParam;
      runCommodityAudit();
    } else if (!sessParam) {
      // Pre-load default staple "साखर" so cards, benchmarks, and chart display instantly
      const input = document.getElementById('audit-commodity-input');
      if (input && !input.value) {
        input.value = "साखर";
        runCommodityAudit();
      }
    }
  }

  async function loadHistoricalCommodities() {
    const datalist = document.getElementById('audit-commodity-datalist');
    const chipsContainer = document.getElementById('audit-quick-chips');

    try {
      const resp = await fetch('/api/v1/analyzer/historical-commodities');
      if (!resp.ok) return;
      commodityList = await resp.json();

      if (datalist) {
        datalist.innerHTML = '';
        commodityList.forEach(name => {
          const opt = document.createElement('option');
          opt.value = name;
          datalist.appendChild(opt);
        });
      }

      // Populate Quick Chips for popular staples
      if (chipsContainer) {
        const staples = ["साखर", "चना डाळ", "गोडतेल", "शेंगदाणा तेल", "शेंगदाणे", "तूर डाळ", "तांदूळ", "कांदा", "पोहे"];
        chipsContainer.innerHTML = staples.map(st => `
          <button type="button" class="audit-chip-btn" data-comm="${st}" style="background:#F1F5F9;border:1px solid #CBD5E1;border-radius:16px;padding:4px 12px;font-size:0.82rem;font-weight:600;color:#334155;cursor:pointer;transition:all 0.2s;touch-action:manipulation;">
            ${st}
          </button>
        `).join('');

        chipsContainer.querySelectorAll('.audit-chip-btn').forEach(btn => {
          const handleChipClick = (e) => {
            if (e && e.type === 'touchend') e.preventDefault();
            const comm = btn.dataset.comm;
            const input = document.getElementById('audit-commodity-input');
            if (input) {
              input.value = comm;
              runCommodityAudit();
            }
          };
          btn.addEventListener('click', handleChipClick);
          btn.addEventListener('touchend', handleChipClick);
        });
      }
    } catch (e) {
      console.warn("[AuditEngine] Failed to load historical commodities:", e);
    }
  }

  function bindEvents() {
    const runBtn = document.getElementById('btn-run-audit') || document.getElementById('run-commodity-audit-btn');
    const input = document.getElementById('audit-commodity-input');
    const qtyInput = document.getElementById('audit-quantity-input');
    const unitSelect = document.getElementById('audit-unit-select');

    if (runBtn) {
      const handleRun = (e) => {
        if (e && e.type === 'touchend') e.preventDefault();
        runCommodityAudit();
      };
      runBtn.addEventListener('click', handleRun);
      runBtn.addEventListener('touchend', handleRun);
    }

    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          runCommodityAudit();
        }
      });
    }

    if (qtyInput) {
      qtyInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          runCommodityAudit();
        }
      });
    }

    if (unitSelect) {
      unitSelect.addEventListener('change', () => {
        const val = input ? input.value.trim() : '';
        if (val) runCommodityAudit();
      });
    }
  }

  async function runCommodityAudit() {
    if (isAuditing) return;

    const input = document.getElementById('audit-commodity-input');
    const qtyInput = document.getElementById('audit-quantity-input');
    const unitSelect = document.getElementById('audit-unit-select');
    const runBtn = document.getElementById('btn-run-audit') || document.getElementById('run-commodity-audit-btn');
    const noticeEl = document.getElementById('audit-unlisted-notice');
    const liveStatusBadge = document.getElementById('audit-live-status-badge');
    const liveStatusText = document.getElementById('audit-live-status-text');

    const commodity = input ? input.value.trim() : '';
    if (!commodity) {
      alert("कृपया वस्तूचे नाव टाईप करा (उदा. साखर, चना डाळ, गोडतेल, शेंगदाणा)...");
      if (input) input.focus();
      return;
    }

    const qty = parseFloat(qtyInput ? qtyInput.value : 1.0) || 1.0;
    const unit = unitSelect ? unitSelect.value : 'किलो';

    isAuditing = true;
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.innerText = "थेट शोधत आहे...";
    }

    // Display live Gemini Web Search Grounding status badge
    if (liveStatusBadge) {
      liveStatusBadge.style.display = 'flex';
      if (liveStatusText) {
        liveStatusText.innerText = `🌐 जेमिनी थेट वेब सर्चवरून '${commodity}' चे चालू दर मिळवत आहे...`;
      }
    }

    try {
      // Trigger live Gemini Google Search Grounding endpoint
      const resp = await fetch('/api/audit-commodity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ commodity: commodity, quantity: qty, unit: unit })
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || "थेट दर तपासण्यात अडचण आली (Search Grounding API Error).");
      }

      const data = await resp.json();
      renderAuditResult(data);

    } catch (err) {
      console.error("[AuditEngine] Live Grounding failed:", err);
      if (noticeEl) {
        noticeEl.style.display = 'flex';
        noticeEl.style.background = '#FEF2F2';
        noticeEl.style.borderColor = '#F87171';
        noticeEl.style.color = '#991B1B';
        noticeEl.innerHTML = `
          <span style="font-size:1.3rem;">❌</span>
          <div>
            <strong>थेट दर मिळवण्यात त्रुटी आली (Live Grounding Failed)</strong>
            <div style="font-size:0.85rem;color:#B91C1C;margin-top:2px;">
              ${escapeHtml(err.message)}
            </div>
          </div>
        `;
      }
    } finally {
      isAuditing = false;
      if (liveStatusBadge) {
        liveStatusBadge.style.display = 'none';
      }
      if (runBtn) {
        runBtn.disabled = false;
        runBtn.innerHTML = `🔍 ऑडिट करा`;
      }
    }
  }

  function renderAuditResult(data) {
    const noticeEl = document.getElementById('audit-unlisted-notice');
    const govtTotEl = document.getElementById('audit-govt-total');
    const govtSubEl = document.getElementById('audit-govt-sub');
    const fairTotEl = document.getElementById('audit-fair-total');
    const fairSubEl = document.getElementById('audit-fair-sub');
    const shopTotEl = document.getElementById('audit-shop-total');
    const shopSubEl = document.getElementById('audit-shop-sub');
    const profitTotEl = document.getElementById('audit-profit-total');
    const profitSubEl = document.getElementById('audit-profit-sub');

    const qty = data.quantity || 1.0;
    const unit = data.canonical_unit || data.unit || 'किलो';

    const mandiRate = data.govt_rate !== undefined ? data.govt_rate : (data.apmc || 0.0);
    const mandiTotal = data.govt_total_amount !== undefined ? data.govt_total_amount : Math.round(mandiRate * qty * 100) / 100;

    const fairRate = data.fair_retail_rate !== undefined ? data.fair_retail_rate : (data.fair_retail || 0.0);
    const fairTotal = data.fair_retail_total_amount !== undefined ? data.fair_retail_total_amount : Math.round(fairRate * qty * 100) / 100;

    const storeRate = data.shopkeeper_rate !== undefined ? data.shopkeeper_rate : (data.store_estimate || 0.0);
    const storeTotal = data.shopkeeper_total_amount !== undefined ? data.shopkeeper_total_amount : Math.round(storeRate * qty * 100) / 100;

    const netProfit = data.shopkeeper_net_profit !== undefined ? data.shopkeeper_net_profit : Math.round((storeRate - mandiRate) * 100) / 100;
    const custVariance = data.customer_variance !== undefined ? data.customer_variance : Math.round((storeRate - fairRate) * 100) / 100;

    // 1. Live Grounded Notice Banner
    if (noticeEl) {
      noticeEl.style.display = 'flex';
      noticeEl.style.background = '#EFF6FF';
      noticeEl.style.borderColor = '#93C5FD';
      noticeEl.style.color = '#1E40AF';
      const noticeTitle = data.is_new_item 
        ? "ही वस्तू मागील याद्यांमध्ये उपलब्ध नाही (नवीन वस्तू / बाहेरून खरेदी)" 
        : `थेट दर पडताळणी पूर्ण झाली: ${escapeHtml(data.commodity || data.commodity_name)}`;
      noticeEl.innerHTML = `
        <span style="font-size:1.3rem;">🌐</span>
        <div>
          <strong>${noticeTitle}</strong>
          <div style="font-size:0.84rem;color:#2563EB;margin-top:2px;">
            Gemini Live Google Search Grounding द्वारे थेट चालू बाजारभाव पडताळण्यात आले आहेत (${escapeHtml(data.grounding_source || "gemini-2.5-flash live search")}).
          </div>
        </div>
      `;
    }

    // 2. Render 3 Live Verified Cards
    const isLiquid = /तेल|oil|तूप|ghee|दूध|milk/i.test(data.commodity || data.commodity_name || '');
    const baseUnit = isLiquid ? 'लिटर' : 'किलो';

    if (govtTotEl) govtTotEl.innerText = formatINR(mandiTotal);
    if (govtSubEl) govtSubEl.innerText = `थेट चालू घाऊक भाव: ${formatINR(mandiRate)} / ${baseUnit}`;

    if (fairTotEl) fairTotEl.innerText = formatINR(fairTotal);
    if (fairSubEl) fairSubEl.innerText = `अपेक्षित रास्त दर (+२२%): ${formatINR(fairRate)} / ${baseUnit}`;

    if (shopTotEl) shopTotEl.innerText = formatINR(storeTotal);
    if (shopSubEl) shopSubEl.innerText = `थेट चालू किरकोळ दर: ${formatINR(storeRate)} / ${baseUnit}`;

    // 3. Render Profit & Real Variance Card
    if (profitTotEl) {
      profitTotEl.innerText = `नफा: ${formatINR(netProfit * qty)}`;
      profitTotEl.style.color = netProfit >= 0 ? '#0F766E' : '#DC2626';
    }
    if (profitSubEl) {
      profitSubEl.innerHTML = `दुकानदार नफा: ${formatINR(netProfit)} / ${baseUnit} | खरी तफावत: <strong>${custVariance >= 0 ? '+' : ''}${formatINR(custVariance)} / ${baseUnit}</strong>`;
    }

    const elHistRefAudit = document.getElementById('card-hist-ref-total') || document.getElementById('card-apmc-total');
    if (elHistRefAudit) elHistRefAudit.innerText = formatINR(mandiTotal);
    if (document.getElementById('card-fair-total')) document.getElementById('card-fair-total').innerText = formatINR(fairTotal);
    if (document.getElementById('card-store-total')) document.getElementById('card-store-total').innerText = formatINR(storeTotal);
    if (document.getElementById('card-net-margin')) document.getElementById('card-net-margin').innerText = formatINR(netProfit * qty);

    // 4. Dynamic Margin Variance Banner
    const banner = document.getElementById('audit-variance-banner');
    const titleEl = document.getElementById('audit-variance-title');
    const descEl = document.getElementById('audit-variance-desc');
    const badgeEl = document.getElementById('audit-variance-badge');

    if (banner && titleEl && descEl && badgeEl) {
      if (custVariance > 5.0) {
        banner.className = 'variance-banner inflated';
        titleEl.innerText = '⚠️ अपेक्षित दरापेक्षा जास्त (Above Fair Retail Price):';
        descEl.innerText = `चालू किरकोळ दर २२% रास्त नफा व वाहतूक खर्चानंतरही एकूण ${formatINR(custVariance * qty)} जास्त आहे.`;
        badgeEl.innerText = `+${formatINR(custVariance * qty)} तफावत (महाग)`;
      } else if (custVariance < -5.0) {
        banner.className = 'variance-banner fair';
        titleEl.innerText = '✓ सवलत / उत्तम ऑफर (Good Deal & Savings):';
        descEl.innerText = `वाजवी किरकोळ दरांच्या तुलनेत आपण एकूण ${formatINR(Math.abs(custVariance * qty))} बचत करत आहात.`;
        badgeEl.innerText = `${formatINR(Math.abs(custVariance * qty))} बचत (Good Deal)`;
      } else {
        banner.className = 'variance-banner fair';
        titleEl.innerText = '✓ वाजवी दर (Fair Retail Price Verified):';
        descEl.innerText = 'चालू किरकोळ दर २२% वाजवी दुकानदार नफा आणि वाहतूक खर्चाशी तंतोतंत सुसंगत आहेत.';
        badgeEl.innerText = 'वाजवी दर (Fair Retail Price)';
      }
    }

    // 5. Itemized Table
    renderItemizedAuditTable({
      ...data,
      govt_rate: mandiRate,
      govt_total_amount: mandiTotal,
      fair_retail_rate: fairRate,
      fair_retail_total_amount: fairTotal,
      shopkeeper_rate: storeRate,
      shopkeeper_total_amount: storeTotal,
      shopkeeper_net_profit: netProfit,
      customer_variance: custVariance
    });

    // 6. Update Visual Canvas Chart
    updateAuditChart({
      ...data,
      govt_total_amount: mandiTotal,
      fair_retail_total_amount: fairTotal,
      shopkeeper_total_amount: storeTotal
    });

    // 7. Render 30-Day Variance Trend Chart (BUG 2)
    if (typeof window.renderVarianceTrendChart === 'function') {
      window.renderVarianceTrendChart();
    }
  }

  function renderItemizedAuditTable(data) {
    const tableBody = document.getElementById('audit-items-table-body');
    if (!tableBody) return;

    const isLiquid = /तेल|oil|तूप|ghee|दूध|milk/i.test(data.commodity_name || data.commodity || '');
    const baseUnit = data.standard_base_unit || (isLiquid ? 'लिटर' : 'किलो');
    const unit = data.unit || data.canonical_unit || 'किलो';
    const varAmt = data.total_variance_amount || 0.0;
    const diffSign = varAmt > 0 ? '+' : '';
    const diffColor = varAmt > 5.0 ? '#DC2626' : (varAmt < -5.0 ? '#16A34A' : '#475569');

    let rowsHtml = `
      <tr style="background:#F8FAFC;font-weight:600;">
        <td style="text-align:center;">१</td>
        <td>
          <strong>${escapeHtml(data.commodity_name)}</strong>
          ${!data.is_historical ? '<span style="font-size:0.75rem;background:#E0F2FE;color:#0369A1;padding:1px 6px;border-radius:8px;margin-left:6px;">नवीन वस्तू</span>' : ''}
        </td>
        <td>${data.quantity} ${unit}</td>
        <td>${formatINR(data.govt_rate)} / ${baseUnit}<br><span style="font-size:0.8rem;color:#64748B;">एकूण: ${formatINR(data.govt_total_amount)}</span></td>
        <td style="color:#15803D;">${formatINR(data.fair_retail_rate)} / ${baseUnit}<br><span style="font-size:0.8rem;color:#166534;">एकूण: ${formatINR(data.fair_retail_total_amount)}</span></td>
        <td style="color:#1E293B;">${formatINR(data.shopkeeper_rate)} / ${baseUnit}<br><span style="font-size:0.8rem;color:#475569;">एकूण: ${formatINR(data.shopkeeper_total_amount)}</span></td>
        <td style="color:${diffColor};font-weight:700;">${diffSign}${formatINR(varAmt)}<br><span style="font-size:0.78rem;">(${diffSign}${data.variance_percentage}%)</span></td>
        <td>
          <span class="badge ${varAmt > 5.0 ? 'badge-surge' : (varAmt < -5.0 ? 'badge-dip' : 'badge-balanced')}">
            ${escapeHtml(data.margin_indicator || (varAmt > 5.0 ? 'महाग' : 'वाजवी दर'))}
          </span>
        </td>
      </tr>
    `;

    // If historical records exist, append them as historical context rows
    if (data.historical_records && data.historical_records.length > 0) {
      rowsHtml += `
        <tr style="background:#F1F5F9;">
          <td colspan="8" style="padding:8px 12px;font-size:0.85rem;font-weight:700;color:#334155;">
            📜 मागील खरेदी नोंदींमधील प्रत्यक्ष आकारणी (Historical Store Receipts):
          </td>
        </tr>
      `;
      data.historical_records.forEach((rec, idx) => {
        rowsHtml += `
          <tr style="font-size:0.86rem;color:#475569;">
            <td style="text-align:center;">•</td>
            <td>📅 ${escapeHtml(rec.date)} (${escapeHtml(rec.merchant)})</td>
            <td>${rec.qty} ${rec.unit}</td>
            <td>—</td>
            <td style="color:#15803D;">वाजवी तुलना</td>
            <td style="font-weight:600;color:#0F172A;">${formatINR(rec.rate)} / ${rec.unit}</td>
            <td colspan="2">एकूण भरणा: <strong>${formatINR(rec.total)}</strong></td>
          </tr>
        `;
      });
    }

    tableBody.innerHTML = rowsHtml;
  }

  function updateAuditChart(data) {
    const canvas = document.getElementById('category-bar-canvas');
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // High DPI Canvas Scaling
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.parentElement ? canvas.parentElement.clientWidth - 40 : 420;
    const h = 240;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, w, h);

    const labels = ["शासकीय घाऊक", "वाजवी किरकोळ", "दुकानदार दर", "UPI भरणा"];
    const values = [
      data.govt_total_amount || 0,
      data.fair_retail_total_amount || 0,
      data.shopkeeper_total_amount || 0,
      data.upi_settled_total_amount || 0
    ];
    const colors = ["#0284C7", "#16A34A", "#F59E0B", "#0F766E"];

    const maxVal = Math.max(...values, 10.0) * 1.25;
    const chartBottom = h - 45;
    const chartTop = 30;
    const barWidth = Math.min(54, (w - 80) / 4);
    const gap = (w - (barWidth * 4)) / 5;

    // Draw Title
    ctx.font = "bold 13px sans-serif";
    ctx.fillStyle = "#1E293B";
    ctx.textAlign = "center";
    ctx.fillText(`${data.commodity_name} - दर तुलना (₹)`, w / 2, 18);

    // Grid baseline
    ctx.strokeStyle = "#E2E8F0";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(20, chartBottom);
    ctx.lineTo(w - 20, chartBottom);
    ctx.stroke();

    values.forEach((val, i) => {
      const barHeight = ((val / maxVal) * (chartBottom - chartTop));
      const x = gap + i * (barWidth + gap);
      const y = chartBottom - barHeight;

      // Draw Bar
      ctx.fillStyle = colors[i];
      ctx.fillRect(x, y, barWidth, barHeight);

      // Amount on top
      ctx.fillStyle = "#0F172A";
      ctx.font = "bold 11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(formatINR(val), x + barWidth / 2, y - 6);

      // Label at bottom
      ctx.fillStyle = "#64748B";
      ctx.font = "10px sans-serif";
      ctx.fillText(labels[i], x + barWidth / 2, chartBottom + 18);
    });
  }

  return {
    init: init,
    runCommodityAudit: runCommodityAudit
  };
})();

document.addEventListener('DOMContentLoaded', () => {
  AuditEngine.init();
});

window.AuditEngine = AuditEngine;

