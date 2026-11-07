/**
 * Smart Kirana Enterprise - History Page Controller (history.html)
 * Trips Ledger, Filters, Metric Cards, Item Drill-down, and Deletion Modal
 */

let allTrips = [];
let pendingDeleteTripId = null;

document.addEventListener('DOMContentLoaded', () => {
  loadTrips();
  initFilterControls();
  initDeleteModal();
});

async function loadTrips() {
  const container = document.getElementById('trips-list-container');
  const loadingEl = document.getElementById('trips-loading');
  if (!container) return;

  if (loadingEl) loadingEl.style.display = 'block';

  try {
    const params = new URLSearchParams();
    const merchantInput = document.getElementById('filter-merchant');
    const statusSelect = document.getElementById('filter-status');
    const startInput = document.getElementById('filter-start-date');
    const endInput = document.getElementById('filter-end-date');

    if (merchantInput && merchantInput.value.trim()) {
      params.append('merchant', merchantInput.value.trim());
    }
    if (statusSelect && statusSelect.value !== 'सर्व') {
      params.append('basket_status', statusSelect.value);
    }
    if (startInput && startInput.value) {
      params.append('start_date', startInput.value);
    }
    if (endInput && endInput.value) {
      params.append('end_date', endInput.value);
    }

    const resp = await fetch(`/api/v1/trips?${params.toString()}`);
    const trips = await resp.json();

    if (!resp.ok) {
      throw new Error(trips.detail || "इतिहास लोड करता आला नाही.");
    }

    allTrips = trips;
    renderMetrics(allTrips);
    renderTripsList(allTrips);

  } catch (err) {
    console.error(err);
    showToast(err.message || "खरेदी इतिहास आणण्यात त्रुटी आली.", "error");
  } finally {
    if (loadingEl) loadingEl.style.display = 'none';
  }
}

function renderMetrics(trips) {
  const totalTripsEl = document.getElementById('metric-total-trips');
  const totalSpendEl = document.getElementById('metric-total-spend');
  const balancedPctEl = document.getElementById('metric-balanced-pct');
  const avgSpendEl = document.getElementById('metric-avg-spend');

  const count = trips.length;
  let totalSpend = 0.0;
  let balancedCount = 0;

  trips.forEach(t => {
    totalSpend += t.settled_total;
    if (t.basket_status === "संतुलित बजेट") {
      balancedCount++;
    }
  });

  const balancedPct = count > 0 ? Math.round((balancedCount / count) * 100) : 0;
  const avgSpend = count > 0 ? Math.round(totalSpend / count) : 0;

  if (totalTripsEl) totalTripsEl.innerText = count;
  if (totalSpendEl) totalSpendEl.innerText = formatINR(totalSpend);
  if (balancedPctEl) balancedPctEl.innerText = `${balancedPct}%`;
  if (avgSpendEl) avgSpendEl.innerText = formatINR(avgSpend);
}

function renderTripsList(trips) {
  const container = document.getElementById('trips-list-container');
  const emptyEl = document.getElementById('trips-empty-state');
  if (!container) return;

  if (trips.length === 0) {
    container.innerHTML = '';
    if (emptyEl) emptyEl.style.display = 'block';
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';
  container.innerHTML = '';

  trips.forEach(trip => {
    const card = document.createElement('div');
    card.className = 'trip-card';
    card.id = `trip-card-${trip.trip_id}`;

    const isBalanced = trip.basket_status === "संतुलित बजेट";
    const statusClass = isBalanced ? "badge-balanced" : "badge-surge";

    card.innerHTML = `
      <div class="trip-main-info">
        <div class="trip-merchant">
          <span>🏪 ${trip.merchant_name}</span>
          <span class="badge ${statusClass}">${trip.basket_status || 'संतुलित बजेट'}</span>
        </div>
        <div class="trip-meta">
          <span>📅 ${trip.trip_date}</span>
          <span>📦 ${trip.items_count} वस्तू</span>
          <span>💳 ${trip.merchant_vpa}</span>
        </div>
      </div>
      <div class="trip-amount-info">
        <span class="trip-total-price">${formatINR(trip.settled_total)}</span>
        <div class="trip-actions">
          <button class="btn btn-secondary btn-sm" onclick="openTripDrilldown(${trip.trip_id})">
            🔍 तपशील पहा
          </button>
          <button class="btn btn-sm" onclick="downloadTripPDF(${trip.trip_id})" style="background:#0F766E; color:#FFFFFF; border:none; border-radius:4px; font-weight:700; padding:4px 10px; cursor:pointer;" title="ऑफलाइन दुकानासाठी स्वच्छ खरेदी पावती PDF">
            📄 PDF डाउनलोड
          </button>
          <a href="/receipt/${trip.trip_id}" target="_blank" class="btn btn-secondary btn-sm">
            🖨️ पावती
          </a>
          <button class="btn btn-danger btn-sm" onclick="confirmDeleteTrip(${trip.trip_id})">
            🗑️ हटवा
          </button>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}

function initFilterControls() {
  const form = document.getElementById('history-filter-form');
  const resetBtn = document.getElementById('filter-reset-btn');

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      loadTrips();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (form) form.reset();
      loadTrips();
    });
  }
}

// Global in-memory drilldown trip reference for in-line editing
let currentDrilldownTrip = null;

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function parseDynamicQuantity(quantityStr) {
  if (!quantityStr) return { normalizedQty: 1.0, baseUnit: 'किलो' };
  let clean = String(quantityStr).trim().toLowerCase();

  // 1. Convert Devanagari numerals to ASCII
  const devDigits = {'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'};
  for (const [d, a] of Object.entries(devDigits)) {
    clean = clean.split(d).join(a);
  }

  // 2. Extract numerical float Q with colloquial Marathi fractions
  let Q = null;
  if (clean.includes('अर्धा') || clean.includes('1/2') || clean.includes('१/२') || clean.includes('आधा')) {
    if (clean.includes('दीड')) Q = 1.5;
    else if (clean.includes('अडीच')) Q = 2.5;
    else Q = 0.5;
  } else if (clean.includes('पाव किलो') || clean.includes('1/4') || clean.includes('१/४') || clean.includes('पाव')) {
    Q = 0.25;
  } else if (clean.includes('पाऊण') || clean.includes('3/4') || clean.includes('३/४')) {
    Q = 0.75;
  } else if (clean.includes('सव्वा')) {
    Q = 1.25;
  } else if (clean.includes('दीड')) {
    Q = 1.5;
  } else if (clean.includes('अडीच')) {
    Q = 2.5;
  }

  if (Q === null) {
    const compositeMatch = clean.match(/\((\d+(?:\.\d+)?)\s*(?:पाकीट|पॅकेट|नग|डबा)?\)/);
    if (compositeMatch) {
      Q = parseFloat(compositeMatch[1]);
    } else {
      const numMatch = clean.match(/(\d+(?:\.\d+)?)/);
      Q = numMatch ? parseFloat(numMatch[1]) : 1.0;
    }
  }

  if (!Q || isNaN(Q) || Q <= 0) Q = 1.0;

  // 3. Identify unit type & standardize to base scales (Zero Hardcoding)
  let normalizedQty = Q;
  let baseUnit = 'किलो';

  // Liquids: milliliters vs liters
  if (clean.includes('मिली') || clean.includes('ml')) {
    normalizedQty = parseFloat((Q / 1000.0).toFixed(4));
    baseUnit = 'ली';
  } else if (clean.includes('ली') || clean.includes('ltr') || clean.includes('liter') || clean.includes('लिटर') || /\bl\b/.test(clean)) {
    normalizedQty = Q;
    baseUnit = 'ली';
  }
  // Solid weights: kilograms vs grams
  else if (clean.includes('किलो') || clean.includes('kg') || clean.includes('k.g.') || clean.includes('kilo')) {
    normalizedQty = Q;
    baseUnit = 'किलो';
  } else if (clean.includes('ग्रॅम') || clean.includes('ग्राम') || clean.includes('gm') || clean.includes('gram') || /\b(?:g|gms)\b/.test(clean)) {
    normalizedQty = parseFloat((Q / 1000.0).toFixed(4));
    baseUnit = 'किलो';
  }
  // Packaging / Discrete units
  else if (clean.includes('पाकीट') || clean.includes('पॅकेट') || clean.includes('pkt') || clean.includes('packet')) {
    normalizedQty = Q;
    baseUnit = 'पाकीट';
  } else if (clean.includes('नग') || clean.includes('pcs') || clean.includes('piece')) {
    normalizedQty = Q;
    baseUnit = 'नग';
  } else if (clean.includes('डबा') || clean.includes('डबे') || clean.includes('tin')) {
    normalizedQty = Q;
    baseUnit = 'डबा';
  } else if (clean.includes('तोळा') || clean.includes('तोल')) {
    normalizedQty = Q;
    baseUnit = 'तोळा';
  } else if (clean.includes('डझन') || clean.includes('dozen')) {
    normalizedQty = Q;
    baseUnit = 'डझन';
  }

  return { normalizedQty, baseUnit };
}

function calculateDynamicLineRate(totalPrice, quantityStr) {
  const total = parseFloat(totalPrice) || 0.0;
  const { normalizedQty, baseUnit } = parseDynamicQuantity(quantityStr);
  const unitRate = normalizedQty > 0 ? parseFloat((total / normalizedQty).toFixed(2)) : total;
  return {
    totalPrice: parseFloat(total.toFixed(2)),
    unitRate: parseFloat(unitRate.toFixed(2)),
    normalizedQty,
    baseUnit
  };
}

// Backward compatibility alias
function parseClientQuantityMagnitude(str) {
  return parseDynamicQuantity(str).normalizedQty;
}

// Drill-Down Modal
async function openTripDrilldown(tripId) {
  const modal = document.getElementById('trip-drilldown-modal');
  const modalBody = document.getElementById('trip-drilldown-content');
  if (!modal || !modalBody) return;

  modalBody.innerHTML = '<div style="text-align:center;padding:30px;">लोड होत आहे...</div>';
  modal.classList.add('active');

  try {
    const resp = await fetch(`/api/v1/trips/${tripId}`);
    const trip = await resp.json();

    if (!resp.ok) {
      throw new Error(trip.detail || "तपशील आणण्यात अडचण आली.");
    }

    currentDrilldownTrip = trip;

    let itemsRows = '';
    trip.items.forEach((it, idx) => {
      const badgeCls = it.badge === "भाववाढ" ? "badge-surge" : (it.badge === "स्वस्त" ? "badge-dip" : (it.badge === "नवीन नोंद" ? "badge-new" : "badge-balanced"));
      const pastRate = it.baseline_rate ? `${formatINR(it.baseline_rate)} / ${it.display_unit}` : "—";
      const varPctStr = it.variance_pct !== null ? `${it.variance_pct > 0 ? '+' : ''}${it.variance_pct}%` : "—";

      let displayQtyStr = it.quantity_str && it.quantity_str.trim() ? it.quantity_str.trim() : `${it.quantity_norm} ${it.display_unit}`;
      if (!it.quantity_str) {
        if (it.quantity_norm < 1.0 && (it.unit === 'kg' || it.display_unit === 'किलो')) {
          displayQtyStr = `${Math.round(it.quantity_norm * 1000)} ग्रॅम`;
        } else if (it.quantity_norm < 1.0 && (it.unit === 'L' || it.display_unit === 'लिटर')) {
          displayQtyStr = `${Math.round(it.quantity_norm * 1000)} मिली`;
        }
      }

      const { unitRate, baseUnit } = calculateDynamicLineRate(it.entered_total, displayQtyStr);
      const displayRate = (it.derived_rate && it.derived_rate > 0 && Math.abs(it.derived_rate - it.entered_total) > 0.001) ? it.derived_rate : unitRate;
      const displayUnit = it.display_unit || baseUnit || 'किलो';

      itemsRows += `
        <tr id="drilldown-row-${idx}" data-row-idx="${idx}" data-item-id="${it.item_id}">
          <td class="col-idx">${idx + 1}</td>
          <td class="col-name">
            <strong>${escapeHtml(it.name)}</strong>
            ${it.raw_input ? `<div style="font-size:0.75rem;color:#64748B;">मूळ: ${escapeHtml(it.raw_input)}</div>` : ''}
          </td>
          <td class="col-qty" id="cell-qty-${idx}">${escapeHtml(displayQtyStr)}</td>
          <td class="col-past-rate">${pastRate}</td>
          <td class="col-rate" id="cell-rate-${idx}" data-unit-base-rate="${displayRate}"><strong>${formatINR(displayRate)} / ${displayUnit}</strong></td>
          <td class="col-total" id="cell-total-${idx}" data-line-total-amount="${it.line_total_amount || it.entered_total}"><strong>${formatINR(it.line_total_amount || it.entered_total)}</strong></td>
          <td class="col-var">${varPctStr}</td>
          <td class="col-badge"><span class="badge ${badgeCls}">${it.badge}</span></td>
          <td class="col-action" id="cell-action-${idx}" style="text-align:center;">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-edit-row" onclick="enableRowEdit(${idx})" style="padding:4px 8px;font-size:0.8rem;border-radius:4px;cursor:pointer;">
              <i class="bi bi-pencil-square"></i> एडिट
            </button>
          </td>
        </tr>
      `;
    });

    modalBody.innerHTML = `
      <div style="margin-bottom:16px;">
        <h3 style="font-size:1.3rem;font-weight:700;">${escapeHtml(trip.merchant_name)}</h3>
        <p style="font-size:0.9rem;color:#64748B;">तारीख: ${trip.trip_date} | सेशन ID: ${trip.session_id} | UPI: ${trip.merchant_vpa}</p>
      </div>
      <div class="table-responsive">
        <table class="table drilldown-table">
          <thead>
            <tr>
              <th>क्र.</th>
              <th>वस्तूचे नाव</th>
              <th>प्रमाण</th>
              <th>मागील दर</th>
              <th>आजचा दर</th>
              <th>एकूण रक्कम</th>
              <th>बदल (%)</th>
              <th>स्टेटस</th>
              <th style="text-align:center;">कृती</th>
            </tr>
          </thead>
          <tbody>
            ${itemsRows}
          </tbody>
        </table>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:20px;padding-top:14px;border-top:2px solid #E2E8F0;flex-wrap:wrap;gap:12px;">
        <div style="display:flex;gap:12px;align-items:center;">
          <div>
            <strong>बजेट स्थिती:</strong> 
            <span class="badge ${trip.basket_status === 'संतुलित बजेट' ? 'badge-balanced' : 'badge-surge'}">${trip.basket_status}</span>
          </div>
          <button type="button" class="btn btn-sm" onclick="downloadTripPDF(${trip.trip_id})" style="background:#0F766E; color:#FFFFFF; border:none; padding:6px 14px; border-radius:6px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:6px;">
            📄 खरेदी पावती PDF प्रिंट / डाउनलोड
          </button>
        </div>
        <div style="font-size:1.3rem;font-weight:800;color:#FF6A00;" id="drilldown-settled-total">
          एकूण देय रक्कम: ${formatINR(trip.settled_total)}
        </div>
      </div>
    `;

  } catch (err) {
    modalBody.innerHTML = `<div style="color:red;padding:20px;">${err.message}</div>`;
  }

  const closeBtn = document.getElementById('close-drilldown-modal');
  if (closeBtn) closeBtn.onclick = () => modal.classList.remove('active');
  modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('active'); };
}

// In-Line Editing Handlers
function enableRowEdit(rowIdx) {
  if (!currentDrilldownTrip || !currentDrilldownTrip.items || !currentDrilldownTrip.items[rowIdx]) return;
  const it = currentDrilldownTrip.items[rowIdx];
  const cellQty = document.getElementById(`cell-qty-${rowIdx}`);
  const cellTotal = document.getElementById(`cell-total-${rowIdx}`);
  const cellAction = document.getElementById(`cell-action-${rowIdx}`);
  if (!cellQty || !cellTotal || !cellAction) return;

  const curQtyStr = it.quantity_str || `${it.quantity_norm} ${it.display_unit}`;
  const curTotal = parseFloat(it.entered_total || 0).toFixed(2);

  cellQty.innerHTML = `<input type="text" class="form-control form-control-sm edit-qty" id="edit-qty-${rowIdx}" value="${escapeHtml(curQtyStr)}" style="max-width:115px;text-align:center;font-weight:600;margin:auto;" />`;
  cellTotal.innerHTML = `<input type="number" step="0.01" min="0" class="form-control form-control-sm edit-total" id="edit-total-${rowIdx}" value="${curTotal}" style="max-width:115px;text-align:right;font-weight:700;color:#0F766E;margin-left:auto;" />`;
  cellAction.innerHTML = `
    <div class="btn-group btn-group-sm" style="display:inline-flex;gap:4px;">
      <button type="button" class="btn btn-sm btn-success btn-save-row" onclick="saveRowEdit(${rowIdx})" title="जतन करा" style="padding:4px 8px;font-size:0.8rem;border-radius:4px;cursor:pointer;">
        <i class="bi bi-check-lg text-white"></i> जतन करा
      </button>
      <button type="button" class="btn btn-sm btn-outline-danger btn-cancel-row" onclick="cancelRowEdit(${rowIdx})" title="रद्द करा" style="padding:4px 8px;font-size:0.8rem;border-radius:4px;cursor:pointer;">
        <i class="bi bi-x-lg"></i> रद्द करा
      </button>
    </div>
  `;
  const inp = document.getElementById(`edit-qty-${rowIdx}`);
  if (inp) inp.focus();
}

function cancelRowEdit(rowIdx) {
  if (!currentDrilldownTrip || !currentDrilldownTrip.items || !currentDrilldownTrip.items[rowIdx]) return;
  const it = currentDrilldownTrip.items[rowIdx];
  const cellQty = document.getElementById(`cell-qty-${rowIdx}`);
  const cellTotal = document.getElementById(`cell-total-${rowIdx}`);
  const cellAction = document.getElementById(`cell-action-${rowIdx}`);
  if (!cellQty || !cellTotal || !cellAction) return;

  const displayQty = it.quantity_str || `${it.quantity_norm} ${it.display_unit}`;
  cellQty.innerHTML = escapeHtml(displayQty);
  cellTotal.innerHTML = `<strong>${formatINR(it.entered_total)}</strong>`;
  cellAction.innerHTML = `
    <button type="button" class="btn btn-sm btn-outline-secondary btn-edit-row" onclick="enableRowEdit(${rowIdx})" style="padding:4px 8px;font-size:0.8rem;border-radius:4px;cursor:pointer;">
      <i class="bi bi-pencil-square"></i> एडिट
    </button>
  `;
}

async function saveRowEdit(rowIdx) {
  if (!currentDrilldownTrip || !currentDrilldownTrip.items || !currentDrilldownTrip.items[rowIdx]) return;
  const it = currentDrilldownTrip.items[rowIdx];
  const qtyInp = document.getElementById(`edit-qty-${rowIdx}`);
  const totInp = document.getElementById(`edit-total-${rowIdx}`);
  const cellAction = document.getElementById(`cell-action-${rowIdx}`);
  const row = document.getElementById(`drilldown-row-${rowIdx}`);

  if (!qtyInp || !totInp) return;
  const newQtyStr = qtyInp.value.trim();
  const newTotal = parseFloat(totInp.value);

  if (!newQtyStr || isNaN(newTotal) || newTotal < 0) {
    if (typeof showToast === 'function') showToast("कृपया योग्य प्रमाण आणि रक्कम प्रविष्ट करा.", "warn");
    return;
  }

  const { unitRate, normalizedQty, baseUnit } = calculateDynamicLineRate(newTotal, newQtyStr);
  const newUnitPrice = unitRate;

  if (cellAction) {
    cellAction.innerHTML = `<span style="font-size:0.8rem;color:#0F766E;">⏳ जतन करत आहे...</span>`;
  }

  try {
    const resp = await fetch('/api/history/update-item', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: currentDrilldownTrip.session_id,
        item_id: it.item_id,
        quantity: newQtyStr,
        total_price: newTotal,
        line_total_amount: newTotal,
        unit_price: newUnitPrice,
        unit_base_rate: newUnitPrice,
        normalized_quantity: normalizedQty
      })
    });

    const resData = await resp.json();
    if (!resp.ok || !resData.success) {
      throw new Error(resData.detail || resData.message || "नोंद अद्ययावत करता आली नाही.");
    }

    // Update in-memory item data
    it.quantity_str = newQtyStr;
    it.quantity_norm = resData.normalized_quantity || resData.quantity_norm || normalizedQty;
    it.normalized_quantity = it.quantity_norm;
    it.entered_total = newTotal;
    it.line_total_amount = newTotal;
    it.derived_rate = resData.unit_base_rate || resData.unit_price || newUnitPrice;
    it.unit_base_rate = it.derived_rate;
    it.display_unit = baseUnit;

    // Recalculate trip grand total
    const updatedTotal = currentDrilldownTrip.items.reduce((sum, item) => sum + (parseFloat(item.line_total_amount || item.entered_total) || 0), 0);
    currentDrilldownTrip.settled_total = resData.trip_settled_total || updatedTotal;

    // Update DOM cells
    const cellQty = document.getElementById(`cell-qty-${rowIdx}`);
    const cellRate = document.getElementById(`cell-rate-${rowIdx}`);
    const cellTotal = document.getElementById(`cell-total-${rowIdx}`);

    if (cellQty) cellQty.innerHTML = escapeHtml(newQtyStr);
    if (cellRate) cellRate.innerHTML = `<strong>${formatINR(it.derived_rate)} / ${baseUnit}</strong>`;
    if (cellTotal) cellTotal.innerHTML = `<strong>${formatINR(newTotal)}</strong>`;
    if (cellAction) {
      cellAction.innerHTML = `
        <button type="button" class="btn btn-sm btn-outline-secondary btn-edit-row" onclick="enableRowEdit(${rowIdx})" style="padding:4px 8px;font-size:0.8rem;border-radius:4px;cursor:pointer;">
          <i class="bi bi-pencil-square"></i> एडिट
        </button>
      `;
    }

    // Update footer grand total
    const footerTotal = document.getElementById('drilldown-settled-total');
    if (footerTotal) {
      footerTotal.innerText = `एकूण देय रक्कम: ${formatINR(currentDrilldownTrip.settled_total)}`;
    }

    // Flash row green
    if (row) {
      row.style.transition = 'background-color 0.4s ease';
      row.style.backgroundColor = '#D1FAE5';
      setTimeout(() => {
        row.style.backgroundColor = '';
      }, 2000);
    }

    if (typeof showToast === 'function') {
      showToast("नोंद यशस्वीरीत्या अद्ययावत केली!", "success");
    }

    // Sync trip card total in main background list if visible
    const tripCard = document.querySelector(`[data-trip-id="${currentDrilldownTrip.trip_id}"]`);
    if (tripCard) {
      const totalEl = tripCard.querySelector('.trip-total') || tripCard.querySelector('.settled-total');
      if (totalEl) totalEl.innerText = formatINR(currentDrilldownTrip.settled_total);
    }
  } catch (err) {
    console.error("[saveRowEdit error]:", err);
    if (typeof showToast === 'function') {
      showToast("दुरुस्ती जतन करताना अडचण आली: " + err.message, "error");
    }
    cancelRowEdit(rowIdx);
  }
}

// Make functions globally accessible
window.openTripDrilldown = openTripDrilldown;
window.enableRowEdit = enableRowEdit;
window.saveRowEdit = saveRowEdit;
window.cancelRowEdit = cancelRowEdit;


/**
 * Universal Offline PDF Downloader for Historical Trips (PILLAR 5)
 */
async function downloadTripPDF(tripId) {
  try {
    const resp = await fetch(`/api/v1/trips/${tripId}`);
    const trip = await resp.json();
    if (!resp.ok) {
      throw new Error(trip.detail || "तपशील आणता आला नाही.");
    }

    const items = (trip.items || []).map(it => ({
      name: it.name,
      commodity_name: it.name,
      quantity: it.quantity_norm,
      qty: it.quantity_norm,
      unit: it.display_unit || it.unit || "किलो"
    }));

    if (typeof window.downloadStorePurchaseOrderPDF === 'function') {
      window.downloadStorePurchaseOrderPDF({
        title: trip.title || `${trip.merchant_name} खरेदी पावती`,
        occasionType: trip.occasion_type || "नियमित",
        date: trip.purchase_date || trip.trip_date,
        customerName: "स्मार्ट किराणा ग्राहक",
        items: items
      });
    } else {
      alert("PDF जनरेटर उपलब्ध नाही.");
    }
  } catch (err) {
    console.error(err);
    if (typeof showToast === 'function') showToast("PDF तयार करण्यात अडचण आली.", "error");
  }
}

// Delete Confirmation Modal
function initDeleteModal() {
  const modal = document.getElementById('delete-confirm-modal');
  const confirmBtn = document.getElementById('delete-confirm-yes');
  const cancelBtn = document.getElementById('delete-confirm-no');
  const closeBtn = document.getElementById('close-delete-modal');

  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      if (!pendingDeleteTripId) return;
      try {
        const resp = await fetch(`/api/v1/trips/${pendingDeleteTripId}`, {
          method: 'DELETE'
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "हटवता आले नाही.");
        }
        showToast("खरेदी नोंद कायमची हटवली आहे आणि बेसलाईन अपडेट केली आहे.", "success");
        if (modal) modal.classList.remove('active');
        pendingDeleteTripId = null;
        loadTrips();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      if (modal) modal.classList.remove('active');
      pendingDeleteTripId = null;
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      if (modal) modal.classList.remove('active');
      pendingDeleteTripId = null;
    });
  }
}

function confirmDeleteTrip(tripId) {
  pendingDeleteTripId = tripId;
  const modal = document.getElementById('delete-confirm-modal');
  if (modal) modal.classList.add('active');
}
