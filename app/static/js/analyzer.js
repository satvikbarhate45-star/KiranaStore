/**
 * Smart Kirana Enterprise - Price Analyzer, Budget Simulator & 3-Way Audit Controller (analyzer.html)
 * Prospective Budget Simulator with Quick Budget Chips, 3-Way Audit Engine,
 * Side-by-Side Comparator, and Price Volatility Visualizer.
 */

let catalogItems = [];
let allTripsList = [];
let allAnalyticsList = [];
let activeSimulatorRows = [];
let activeSelectedBudget = null;

// Currency & numeral helpers
function formatINR(val) {
  if (val === null || val === undefined || isNaN(val)) return '₹0.00';
  const num = parseFloat(val);
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const DEV_DIGITS = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'];
function toDevanagariDigits(val) {
  if (val === null || val === undefined) return '';
  return String(val).replace(/[0-9]/g, d => DEV_DIGITS[d]);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

document.addEventListener('DOMContentLoaded', () => {
  const safeInit = (name, fn) => {
    try {
      fn();
    } catch (e) {
      console.error(`[Analyzer Init Error in ${name}]:`, e);
    }
  };

  safeInit('Tabs', initTabs);
  safeInit('QuickBudgetChips', initQuickBudgetChips);
  safeInit('SimulatorVerificationModal', initSimulatorVerificationModal);
  safeInit('CatalogForSimulator', loadCatalogForSimulator);
  safeInit('TripsForComparator', loadTripsForComparator);
  safeInit('AuditAnalytics', loadAuditAnalytics);
  safeInit('PriceTrends', () => loadPriceTrends(30));
  safeInit('AnalyzerFestivalSurgeBanner', initAnalyzerFestivalSurgeBanner);
  safeInit('VarianceTrendChart', () => renderVarianceTrendChart());
  safeInit('SavedListImportAudit', initSavedListImportAudit);
  safeInit('AnalyzerReceiptScanner', initAnalyzerReceiptScanner);
  safeInit('PersonalInflationIndex', loadPersonalInflationIndex);
  safeInit('SimulatorReplayEvents', initSimulatorReplayEvents);
  safeInit('HistoricalBillModal', initHistoricalBillModal);

  // Check URL query parameters for auto tab activation (e.g. ?tab=audit-3way&session_id=...)
  try {
    const params = new URLSearchParams(window.location.search);
    const targetTab = params.get('tab');
    if (targetTab) {
      const tabBtn = document.querySelector(`.tab-btn[data-tab="tab-${targetTab}"]`);
      if (tabBtn) tabBtn.click();
    }
  } catch (err) {
    console.error("[Analyzer Query Param Error]:", err);
  }
});

// Tab Navigation
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    const activateTab = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => {
        c.classList.remove('active');
        c.classList.add('d-none');
      });

      tab.classList.add('active');
      const targetId = tab.dataset.tab;
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        targetEl.classList.remove('d-none');
        targetEl.classList.add('active');
      }
    };

    tab.addEventListener('click', activateTab);
    tab.addEventListener('touchend', activateTab);
  });
}

/**
 * ==============================================================================
 * MODULE 4: QUICK BUDGET PRESET CHIPS & PROSPECTIVE SIMULATOR
 * ==============================================================================
 */
function initQuickBudgetChips() {
  const chips = document.querySelectorAll('.budget-chip');
  const budgetRow = document.getElementById('sim-budget-limit-row');
  const budgetDisplay = document.getElementById('sim-selected-budget-display');

  chips.forEach(chip => {
    const handleChip = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      const budgetVal = parseFloat(chip.dataset.budget);
      if (activeSelectedBudget === budgetVal) {
        // Toggle off
        activeSelectedBudget = null;
        chip.classList.remove('active');
        if (budgetRow) budgetRow.style.display = 'none';
      } else {
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        activeSelectedBudget = budgetVal;
        if (budgetRow) budgetRow.style.display = 'flex';
        if (budgetDisplay) budgetDisplay.innerText = formatINR(budgetVal);
      }
      recalculateSimulation();
    };

    chip.addEventListener('click', handleChip);
    chip.addEventListener('touchend', handleChip);
  });
}

async function initAnalyzerFestivalSurgeBanner() {
  const banner = document.getElementById('analyzer-festival-surge-banner');
  const titleEl = document.getElementById('analyzer-fest-title');
  const textEl = document.getElementById('analyzer-fest-text');
  const badgeEl = document.getElementById('analyzer-fest-badge');
  const chipsEl = document.getElementById('analyzer-fest-chips');

  if (!banner) return;

  try {
    const resp = await fetch('/api/v1/analyzer/festival-surge-advice');
    if (!resp.ok) return;
    const data = await resp.json();
    if (data && data.advice_card_mr) {
      if (textEl) textEl.innerText = data.advice_card_mr;
      if (titleEl) titleEl.innerText = `💡 ${data.festival_name} - स्मार्ट खरेदी सल्ला`;
      if (badgeEl) badgeEl.innerText = `${data.days_until} दिवस बाकी`;
      if (chipsEl && Array.isArray(data.affected_commodities)) {
        chipsEl.innerHTML = data.affected_commodities
          .map(
            (c) => `
          <span style="background:#FEF3C7;border:1px solid #F59E0B;padding:2px 8px;border-radius:12px;font-weight:600;">
            📈 ${c}
          </span>
        `
          )
          .join('');
      }
      banner.style.display = 'block';
    }
  } catch (e) {
    console.warn("[AnalyzerFestivalSurge] Advice fetch failed:", e);
  }
}

// Debounce helper for smooth user input recalculations
function debounce(fn, delay = 300) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

async function loadCatalogForSimulator() {
  try {
    const resp = await fetch('/api/v1/catalog');
    catalogItems = await resp.json();

    const container = document.getElementById('sim-items-container');
    if (container && container.children.length === 0) {
      // Default staple rows
      addSimulatorRow(1, 5.0); // साखर 5 kg
      addSimulatorRow(2, 2.0); // शेंगदाणा तेल 2 L
      addSimulatorRow(3, 2.0); // तूर डाळ 2 kg
      recalculateSimulation();
    }

    const addBtn = document.getElementById('add-sim-item-btn');
    if (addBtn) {
      const handleAddSim = (e) => {
        if (e && e.type === 'touchend') e.preventDefault();
        addSimulatorRow();
        recalculateSimulation();
      };
      addBtn.onclick = handleAddSim;
    }

    initSimulatorActions();

  } catch (err) {
    console.error("Failed to load catalog for simulator", err);
  }
}

function initSimulatorActions() {
  // 1. Send to Counter
  const sendCounterBtn = document.getElementById('sim-send-counter-btn');
  if (sendCounterBtn) {
    sendCounterBtn.onclick = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      handleSimulatorSendToCounter();
    };
  }

  // 2. Offline A4 Printable PDF
  const simPdfBtn = document.getElementById('btn-sim-download-pdf');
  if (simPdfBtn) {
    simPdfBtn.onclick = () => {
      const rows = document.querySelectorAll('.sim-item-row');
      const items = [];
      rows.forEach((row, idx) => {
        const skuSelect = row.querySelector('.sim-sku-select');
        const qtyInput = row.querySelector('.sim-qty-input');
        const skuId = parseInt(skuSelect.value, 10);
        const qty = parseFloat(qtyInput.value) || 1.0;
        const opt = skuSelect.options[skuSelect.selectedIndex];
        const name = opt ? opt.dataset.name : `वस्तू #${skuId}`;
        const unit = opt ? opt.dataset.unit : 'किलो';
        if (skuId && qty > 0) {
          items.push({ commodity_name: name, name: name, quantity: qty, qty: qty, unit: unit });
        }
      });

      if (items.length === 0) {
        if (typeof showToast === 'function') showToast("सिम्युलेटरमध्ये किमान एक वस्तू जोडा.", "warn");
        return;
      }

      if (typeof window.downloadStorePurchaseOrderPDF === 'function') {
        window.downloadStorePurchaseOrderPDF({
          title: "सिम्युलेटर खरेदी यादी",
          occasionType: "नियमित",
          date: new Date().toISOString().split('T')[0],
          customerName: "स्मार्ट किराणा ग्राहक",
          items: items
        });
      }
    };
  }

  // 3. Save Budget Draft
  const simSaveBtn = document.getElementById('btn-sim-save-budget');
  if (simSaveBtn) {
    simSaveBtn.onclick = async () => {
      const rows = document.querySelectorAll('.sim-item-row');
      const items = [];
      let budget = 0.0;
      rows.forEach((row, idx) => {
        const skuSelect = row.querySelector('.sim-sku-select');
        const qtyInput = row.querySelector('.sim-qty-input');
        const manualInp = row.querySelector('.item-manual-price');
        const skuId = parseInt(skuSelect.value, 10);
        const qty = parseFloat(qtyInput.value) || 1.0;
        const opt = skuSelect.options[skuSelect.selectedIndex];
        const name = opt ? opt.dataset.name : `वस्तू #${skuId}`;
        const unit = opt ? opt.dataset.unit : 'किलो';
        const manualPrice = manualInp && manualInp.value ? (parseFloat(manualInp.value) || 0.0) : 0.0;

        if (skuId && qty > 0) {
          items.push({
            sku_id: skuId,
            commodity_name: name,
            name: name,
            quantity: qty,
            qty: qty,
            unit: unit,
            target_price: manualPrice,
            price: manualPrice
          });
          budget += (qty * manualPrice);
        }
      });

      if (items.length === 0) {
        if (typeof showToast === 'function') showToast("सिम्युलेटरमध्ये किमान एक वस्तू जोडा.", "warn");
        return;
      }

      try {
        const resp = await fetch('/api/save-grocery-list', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: "सिम्युलेटर नियोजित बजेट",
            occasion_type: "regular",
            purchase_date: new Date().toISOString().split('T')[0],
            items: items,
            estimated_budget: budget
          })
        });

        if (resp.ok) {
          if (typeof showToast === 'function') {
            showToast("💾 सिम्युलेटर बजेट यादी सेव्ह झाली!", "success");
          }
        }
      } catch (err) {
        console.error("Save budget error:", err);
      }
    };
  }
}

function addSimulatorRow(defaultSkuId = null, defaultQty = 1.0) {
  const container = document.getElementById('sim-items-container');
  if (!container) return;

  const rowId = `sim-row-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
  const div = document.createElement('div');
  div.className = 'sim-item-row';
  div.id = rowId;

  let optionsHtml = '';
  catalogItems.forEach(item => {
    const selected = (defaultSkuId && item.sku_id === defaultSkuId) ? 'selected' : '';
    optionsHtml += `<option value="${item.sku_id}" data-unit="${item.display_unit}" data-name="${item.marathi_name}" ${selected}>${item.marathi_name} (${item.display_unit})</option>`;
  });

  div.innerHTML = `
    <div style="flex:2.5;min-width:140px;">
      <select class="form-control sim-sku-select">
        ${optionsHtml}
      </select>
    </div>
    <div style="flex:1;min-width:70px;">
      <input type="number" step="0.25" min="0.1" class="form-control sim-qty-input" value="${defaultQty}" />
    </div>
    <div class="sim-line-est" style="flex:2.2;min-width:140px;display:flex;align-items:center;">
      —
    </div>
    <div style="width:36px;text-align:right;">
      <button type="button" class="btn btn-secondary btn-sm" onclick="removeSimulatorRow('${rowId}')">✕</button>
    </div>
  `;

  container.appendChild(div);

  div.querySelector('.sim-sku-select').addEventListener('change', () => {
    // Clear manual price input on changing item
    const manualInp = div.querySelector('.item-manual-price');
    if (manualInp) manualInp.value = '';
    recalculateSimulation();
  });
  div.querySelector('.sim-qty-input').addEventListener('input', recalculateSimulation);
}

function removeSimulatorRow(rowId) {
  const el = document.getElementById(rowId);
  if (el) el.remove();
  recalculateSimulation();
}

async function recalculateSimulation() {
  const rows = document.querySelectorAll('.sim-item-row');
  const itemsPayload = [];

  rows.forEach(row => {
    const skuSelect = row.querySelector('.sim-sku-select');
    const qtyInput = row.querySelector('.sim-qty-input');
    const manualInp = row.querySelector('.item-manual-price');
    const skuId = parseInt(skuSelect.value, 10);
    const qty = parseFloat(qtyInput.value) || 0;
    const manualPrice = (manualInp && manualInp.value) ? (parseFloat(manualInp.value) || null) : null;

    if (skuId && qty > 0) {
      itemsPayload.push({
        sku_id: skuId,
        quantity: qty,
        manual_price: manualPrice
      });
    }
  });

  if (itemsPayload.length === 0) {
    updateSimulatorUI(0, 0, 0, [], false, 0);
    return;
  }

  try {
    const resp = await fetch('/api/v1/analyzer/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: itemsPayload })
    });
    const data = await resp.json();
    if (resp.ok) {
      updateSimulatorUI(
        data.total_estimated,
        data.total_range_low,
        data.total_range_high,
        data.items,
        data.has_missing_history,
        data.missing_items_count
      );
    }
  } catch (err) {
    console.error("Simulation failed", err);
  }
}

function updateSimulatorUI(total, low, high, items, hasMissingHistory = false, missingCount = 0) {
  const totalEl = document.getElementById('sim-total-display');
  const lowEl = document.getElementById('sim-low-display');
  const highEl = document.getElementById('sim-high-display');
  const alertEl = document.getElementById('sim-missing-prices-alert');

  if (totalEl) {
    totalEl.innerText = formatINR(total);
    if (activeSelectedBudget && total > activeSelectedBudget) {
      totalEl.style.color = '#F87171';
    } else {
      totalEl.style.color = '#FFD54F';
    }
  }
  if (lowEl) lowEl.innerText = (low && low > 0) ? formatINR(low) : '—';
  if (highEl) highEl.innerText = (high && high > 0) ? formatINR(high) : '—';

  if (alertEl) {
    if (hasMissingHistory || missingCount > 0) {
      alertEl.style.display = 'block';
      alertEl.innerText = '⚠️ काही वस्तूंचा इतिहास उपलब्ध नाही, कृपया चालू दर टाका.';
    } else {
      alertEl.style.display = 'none';
    }
  }

  const rows = document.querySelectorAll('.sim-item-row');
  rows.forEach((row, idx) => {
    const estEl = row.querySelector('.sim-line-est');
    const itemData = items[idx];
    if (!estEl || !itemData) return;

    if (!itemData.has_history && !itemData.baseline_unit_rate) {
      // EMPTY STATE: User has NO past purchase record for this item in database!
      // DO NOT invent numbers. Display empty ("-") and editable number input:
      const existingInp = estEl.querySelector('.item-manual-price');
      const curVal = existingInp ? existingInp.value : (itemData.manual_price || '');

      estEl.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:3px;width:100%;">
          <input type="number" step="any" min="0" placeholder="चालू दर टाका (₹)" class="form-control form-control-sm item-manual-price" value="${curVal}" style="width:130px;font-size:0.85rem;padding:4px 8px;border:1.5px solid #F59E0B;border-radius:6px;background:#FFFBEB;font-weight:700;" />
          <span class="badge bg-secondary" style="font-size:0.7rem;background:#E2E8F0;color:#475569;border-radius:4px;padding:2px 6px;width:max-content;">नवीन वस्तू (इतिहास नाही)</span>
        </div>
      `;
      const newInp = estEl.querySelector('.item-manual-price');
      if (newInp) {
        newInp.addEventListener('input', debounce(() => recalculateSimulation(), 300));
      }
    } else {
      const badgeHtml = itemData.has_history
        ? `<div style="font-size:0.75rem;color:#64748B;">मागील दर: ₹${itemData.baseline_unit_rate}/${itemData.display_unit}</div>`
        : `<div style="font-size:0.75rem;color:#92400E;">चालू दर: ₹${itemData.baseline_unit_rate}</div>`;

      estEl.innerHTML = `
        <div>
          <div style="font-size:0.95rem;font-weight:800;color:#1E293B;">${itemData.estimated_total ? formatINR(itemData.estimated_total) : '—'}</div>
          ${badgeHtml}
        </div>
      `;
    }
  });
}

/**
 * ==============================================================================
 * MODULE 2 & 4: SIMULATOR TO VERIFICATION MODAL ("📝 यादी करा")
 * ==============================================================================
 */
function initSimulatorVerificationModal() {
  const modal = document.getElementById('verification-modal');
  const closeBtn = document.getElementById('close-verification-modal');
  const cancelBtn = document.getElementById('v-cancel-btn');
  const addRowBtn = document.getElementById('v-add-row-btn');
  const confirmBtn = document.getElementById('v-confirm-btn');

  function closeModal() {
    if (modal) modal.classList.remove('active');
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }

  if (addRowBtn) {
    addRowBtn.addEventListener('click', () => {
      addSimVerificationRow();
    });
  }

  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      confirmSimAndSendToCounter();
    });
  }
}

function handleSimulatorSendToCounter() {
  const rows = document.querySelectorAll('.sim-item-row');
  const simItems = [];

  rows.forEach((row, index) => {
    const skuSelect = row.querySelector('.sim-sku-select');
    const qtyInput = row.querySelector('.sim-qty-input');
    const estEl = row.querySelector('.sim-line-est');

    const skuId = parseInt(skuSelect.value, 10);
    const qty = parseFloat(qtyInput.value) || 1.0;
    const opt = skuSelect.options[skuSelect.selectedIndex];
    const name = opt ? opt.dataset.name : `वस्तू #${skuId}`;
    const unit = opt ? opt.dataset.unit : 'किलो';

    let estAmount = 0.0;
    if (estEl && estEl.innerText.includes('₹')) {
      estAmount = parseFloat(estEl.innerText.replace(/[^0-9.]/g, '')) || 0.0;
    }

    simItems.push({
      line_index: index,
      sku_id: skuId,
      name: name,
      qty: qty,
      unit: unit,
      display_qty: qty,
      display_unit: unit,
      target_price: estAmount,
      estimated_price: estAmount
    });
  });

  if (simItems.length === 0) {
    alert("कृपया सिम्युलेटरमध्ये किमान एक वस्तू निवडा.");
    return;
  }

  // Open the intermediate verification modal
  openSimVerificationModal(simItems);
}

function openSimVerificationModal(items) {
  const modal = document.getElementById('verification-modal');
  const tableBody = document.getElementById('v-table-body');
  if (!modal || !tableBody) return;

  tableBody.innerHTML = '';
  items.forEach(itm => addSimVerificationRow(itm));
  updateSimVerificationCounts(items.length);

  modal.classList.add('active');
}

function addSimVerificationRow(itemData = null) {
  const tableBody = document.getElementById('v-table-body');
  if (!tableBody) return;

  const currentCount = tableBody.children.length;
  const tr = document.createElement('tr');

  const nameVal = itemData ? itemData.name : '';
  const qtyVal = itemData ? itemData.qty : 1.0;
  const rawUnit = itemData ? itemData.unit : 'किलो';
  let matchedUnit = 'किलो';
  if (/ग्रॅम|gm/i.test(rawUnit)) matchedUnit = 'ग्रॅम';
  else if (/लिटर|L/i.test(rawUnit)) matchedUnit = 'लिटर';
  else if (/पाकीट/i.test(rawUnit)) matchedUnit = 'पाकीट';
  else if (/नग/i.test(rawUnit)) matchedUnit = 'नग';

  const priceVal = (itemData && itemData.target_price) ? parseFloat(itemData.target_price).toFixed(2) : '';

  tr.innerHTML = `
    <td class="v-td-sr">${toDevanagariDigits(currentCount + 1)}</td>
    <td>
      <input type="text" class="v-input v-item-name" value="${escapeHtml(nameVal)}" placeholder="उदा. अगरबत्ती [विलास], गोडतेल" />
    </td>
    <td>
      <input type="number" step="any" min="0.01" class="v-input v-item-qty" value="${qtyVal}" />
    </td>
    <td>
      <select class="v-input v-item-unit">
        <option value="किलो" ${matchedUnit === 'किलो' ? 'selected' : ''}>किलो</option>
        <option value="ग्रॅम" ${matchedUnit === 'ग्रॅम' ? 'selected' : ''}>ग्रॅम</option>
        <option value="लिटर" ${matchedUnit === 'लिटर' ? 'selected' : ''}>लिटर</option>
        <option value="पाकीट" ${matchedUnit === 'पाकीट' ? 'selected' : ''}>पाकीट</option>
        <option value="नग" ${matchedUnit === 'नग' ? 'selected' : ''}>नग</option>
      </select>
    </td>
    <td>
      <input type="number" step="0.01" min="0" class="v-input v-item-price" placeholder="—" value="${priceVal}" />
    </td>
    <td style="text-align:center;">
      <button type="button" class="v-delete-btn" title="वस्तू हटवा" aria-label="वस्तू हटवा">🗑️</button>
    </td>
  `;

  const delBtn = tr.querySelector('.v-delete-btn');
  if (delBtn) {
    delBtn.addEventListener('click', () => {
      tr.remove();
      updateSimVerificationCounts();
    });
  }

  tableBody.appendChild(tr);
  updateSimVerificationCounts();
}

function updateSimVerificationCounts(totalOriginal = null) {
  const rows = document.querySelectorAll('#v-table-body tr');
  const currentCount = rows.length;
  const tot = totalOriginal || currentCount;

  const badgeEl = document.getElementById('v-verification-badge');
  if (badgeEl) {
    badgeEl.innerHTML = `<span class="v-badge v-badge-success">एकूण वस्तू: ${toDevanagariDigits(currentCount)}/${toDevanagariDigits(tot)}</span>`;
  }
  const noteEl = document.getElementById('v-count-status-note');
  if (noteEl) {
    noteEl.innerText = `एकूण वस्तू: ${toDevanagariDigits(currentCount)}/${toDevanagariDigits(tot)}`;
  }
  rows.forEach((row, i) => {
    const srCell = row.querySelector('.v-td-sr');
    if (srCell) srCell.innerText = toDevanagariDigits(i + 1);
  });
}

function confirmSimAndSendToCounter() {
  const rows = document.querySelectorAll('#v-table-body tr');
  const verifiedItems = [];

  rows.forEach((row, index) => {
    const nameInput = row.querySelector('.v-item-name');
    const qtyInput = row.querySelector('.v-item-qty');
    const unitSelect = row.querySelector('.v-item-unit');
    const priceInput = row.querySelector('.v-item-price');

    if (!nameInput) return;
    const name = nameInput.value.trim();
    if (!name) return;

    const qty = parseFloat(qtyInput ? qtyInput.value : 1.0) || 1.0;
    const unit = unitSelect ? unitSelect.value : 'नग';
    const priceVal = priceInput ? parseFloat(priceInput.value) : null;
    const targetPrice = (!isNaN(priceVal) && priceVal > 0) ? priceVal : null;

    let quantityNorm = qty;
    let canonicalUnit = 'kg';
    if (unit === 'ग्रॅम') {
      quantityNorm = qty / 1000.0;
    } else if (unit === 'लिटर') {
      canonicalUnit = 'L';
    } else if (unit === 'पाकीट') {
      canonicalUnit = 'packet';
    } else if (unit === 'नग') {
      canonicalUnit = 'pcs';
    }

    verifiedItems.push({
      line_index: index,
      name: name,
      qty: qty,
      unit: unit,
      display_qty: qty,
      display_unit: unit,
      quantity_norm: quantityNorm,
      canonical_unit: canonicalUnit,
      target_price: targetPrice,
      estimated_price: targetPrice,
      enteredTotal: targetPrice || 0.0
    });
  });

  if (verifiedItems.length === 0) {
    alert("कृपया यादीत किमान एक वस्तू ठेवा.");
    return;
  }

  // Persist into localStorage draft and navigate to counter
  const draftData = {
    session_id: 'sim-' + Date.now(),
    title: `सिम्युलेटर यादी (${verifiedItems.length} वस्तू)`,
    items: verifiedItems,
    saved_at: new Date().toISOString()
  };

  try {
    localStorage.setItem('smart_kirana_draft', JSON.stringify(draftData));
  } catch (e) {}

  window.location.href = '/?restore=draft';
}

/**
 * ==============================================================================
 * MODULE 4: CLOSED-LOOP 3-WAY COMPARATIVE PRICE VARIANCE & AUDIT ENGINE
 * ==============================================================================
 */
async function loadAuditAnalytics() {
  const sessionSelect = document.getElementById('audit-session-select');
  const refreshBtn = document.getElementById('refresh-audit-btn');

  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadAuditAnalytics);
  }

  try {
    const resp = await fetch('/api/v1/analyzer/trip-analytics?limit=30');
    if (!resp.ok) return;

    allAnalyticsList = await resp.json();
    if (!sessionSelect) return;

    sessionSelect.innerHTML = '';
    if (allAnalyticsList.length === 0) {
      sessionSelect.innerHTML = '<option value="">-- कोणतीही खरेदी नोंद उपलब्ध नाही --</option>';
      return;
    }

    allAnalyticsList.forEach((r, idx) => {
      const opt = document.createElement('option');
      opt.value = r.session_id;
      const dateStr = r.created_at || 'खरेदी सत्र';
      opt.innerText = `सत्र ${toDevanagariDigits(idx + 1)} (${dateStr}) - ${formatINR(r.shopkeeper_total_amount)}`;
      sessionSelect.appendChild(opt);
    });

    sessionSelect.addEventListener('change', () => {
      const chosen = allAnalyticsList.find(a => a.session_id === sessionSelect.value);
      if (chosen) renderAuditSession(chosen);
    });

    // Check if session_id passed in URL; only auto-render session if explicitly requested
    const params = new URLSearchParams(window.location.search);
    const targetSess = params.get('session_id');
    if (targetSess) {
      sessionSelect.value = targetSess;
      const currentSelected = allAnalyticsList.find(a => a.session_id === targetSess);
      if (currentSelected) {
        renderAuditSession(currentSelected);
      }
    }

  } catch (err) {
    console.error("Failed to load audit analytics", err);
  }
}

function renderEmptyAuditState() {
  const banner = document.getElementById('audit-variance-banner');
  const tableBody = document.getElementById('audit-items-table-body');
  if (banner) {
    banner.className = 'variance-banner fair';
    const vTitle = document.getElementById('audit-variance-title');
    if (vTitle) vTitle.innerText = "कोणतीही खरेदी नोंद नाही";
    const vDesc = document.getElementById('audit-variance-desc');
    if (vDesc) vDesc.innerText = "काउंटरवर बिलिंग पूर्ण करून QR पेमेंट केल्यावर येथे ३-वे ऑडिट दिसेल.";
    const vBadge = document.getElementById('audit-variance-badge');
    if (vBadge) vBadge.innerText = "—";
  }
  if (tableBody) {
    tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#64748B;">खरेदीचा डेटा उपलब्ध नाही.</td></tr>`;
  }
}

function renderAuditSession(auditData) {
  const govtTotEl = document.getElementById('audit-govt-total');
  const fairTotEl = document.getElementById('audit-fair-total');
  const shopTotEl = document.getElementById('audit-shop-total');
  const upiTotEl = document.getElementById('audit-upi-total');

  const govtTotal = auditData.govt_total_amount || 0.0;
  const fairTotal = auditData.fair_retail_total_amount || Math.round((govtTotal * 1.22 + 10.0) * 100) / 100;
  const shopTotal = auditData.shopkeeper_total_amount || 0.0;
  const upiTotal = auditData.upi_settled_amount || 0.0;
  const varianceAmt = auditData.total_variance_amount !== undefined ? auditData.total_variance_amount : (shopTotal - fairTotal);
  const variancePct = auditData.variance_percentage || (fairTotal > 0 ? ((varianceAmt / fairTotal) * 100.0) : 0.0);

  if (govtTotEl) govtTotEl.innerText = formatINR(govtTotal);
  if (fairTotEl) fairTotEl.innerText = formatINR(fairTotal);
  if (shopTotEl) shopTotEl.innerText = formatINR(shopTotal);
  if (upiTotEl) upiTotEl.innerText = formatINR(upiTotal);

  const elCardHistRef = document.getElementById('card-hist-ref-total') || document.getElementById('card-apmc-total');
  if (elCardHistRef) elCardHistRef.innerText = formatINR(govtTotal);
  if (document.getElementById('card-fair-total')) document.getElementById('card-fair-total').innerText = formatINR(fairTotal);
  if (document.getElementById('card-store-total')) document.getElementById('card-store-total').innerText = formatINR(shopTotal);
  if (document.getElementById('card-net-margin')) document.getElementById('card-net-margin').innerText = formatINR(shopTotal - govtTotal);

  // MODULE 2: Dynamic Margin Variance Banner
  const banner = document.getElementById('audit-variance-banner');
  const titleEl = document.getElementById('audit-variance-title');
  const descEl = document.getElementById('audit-variance-desc');
  const badgeEl = document.getElementById('audit-variance-badge');

  if (banner && titleEl && descEl && badgeEl) {
    if (auditData.is_inflated) {
      banner.className = 'variance-banner inflated';
      titleEl.innerText = '⚠️ अपेक्षित दरापेक्षा जास्त (Above Fair Retail Price):';
      descEl.innerText = `दुकानदाराने २२% वाजवी किरकोळ नफा व वाहतूक खर्चानंतरही एकूण ${formatINR(Math.abs(varianceAmt))} जास्त आकारले आहे.`;
      badgeEl.innerText = auditData.badge_label || `+${formatINR(varianceAmt)} जास्त आकारले`;
    } else if (varianceAmt < -5.0) {
      banner.className = 'variance-banner fair';
      titleEl.innerText = '✓ सवलत / उत्तम ऑफर (Good Deal & Savings):';
      descEl.innerText = `वाजवी किरकोळ दरांच्या तुलनेत आपण एकूण ${formatINR(Math.abs(varianceAmt))} बचत केली आहे.`;
      badgeEl.innerText = auditData.badge_label || `${formatINR(Math.abs(varianceAmt))} बचत (Good Deal)`;
    } else {
      banner.className = 'variance-banner fair';
      titleEl.innerText = '✓ वाजवी दर (Fair Retail Price Verified):';
      descEl.innerText = 'दुकानदाराने आकारलेले दर २२% वाजवी किरकोळ मार्जिन आणि वाहतूक खर्चाशी तंतोतंत सुसंगत आहेत.';
      badgeEl.innerText = auditData.badge_label || 'वाजवी दर (Fair Retail Price)';
    }
  }

  // Itemized Table
  const tableBody = document.getElementById('audit-items-table-body');
  if (tableBody) {
    const items = auditData.items_breakdown || [];
    if (items.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:20px;color:#64748B;">तपशीलवार वस्तूंचा डेटा उपलब्ध नाही.</td></tr>`;
    } else {
      let rowsHtml = '';
      items.forEach((item, idx) => {
        const name = item.name || `वस्तू ${idx + 1}`;
        const qty = item.qty || item.quantity || 1.0;
        const unit = item.unit || 'kg';
        const isLiquid = /तेल|oil|तूप|ghee|दूध|milk/i.test(name);
        const baseUnit = isLiquid ? 'लिटर' : 'किलो';
        const gRate = item.govt_rate ? `${formatINR(item.govt_rate)} / ${baseUnit}` : '—';
        const fairRate = item.fair_retail_rate ? `${formatINR(item.fair_retail_rate)} / ${baseUnit}` : (item.govt_rate ? `${formatINR(item.govt_rate * 1.22 + 5.0)} / ${baseUnit}` : '—');
        const sRate = item.shopkeeper_rate ? `${formatINR(item.shopkeeper_rate)} / ${baseUnit}` : '—';
        const varAmt = item.variance_amount !== undefined ? item.variance_amount : 0.0;
        
        let remarkClass = 'fair';
        let remarkLabel = item.remark || 'वाजवी दर';
        let diffColor = '#15803D';
        let diffSign = '';

        if (remarkLabel === 'महाग' || varAmt > 5.0) {
          remarkClass = 'inflated';
          remarkLabel = item.margin_indicator || 'महाग';
          diffColor = '#DC2626';
          diffSign = '+';
        } else if (remarkLabel === 'बचत' || varAmt < -5.0) {
          remarkClass = 'fair';
          remarkLabel = item.margin_indicator || 'सवलत (Good Deal)';
          diffColor = '#16A34A';
        } else {
          remarkClass = 'fair';
          remarkLabel = item.margin_indicator || 'वाजवी दर';
          diffColor = '#475569';
        }

        rowsHtml += `
          <tr>
            <td>${toDevanagariDigits(idx + 1)}</td>
            <td><strong>${escapeHtml(name)}</strong></td>
            <td>${toDevanagariDigits(qty)} ${escapeHtml(unit)}</td>
            <td style="color:#64748B;">${gRate}</td>
            <td style="color:#0F766E;font-weight:600;">${fairRate}</td>
            <td style="font-weight:700;">${sRate}</td>
            <td style="color:${diffColor};font-weight:700;">
              ${diffSign}${formatINR(varAmt)}
            </td>
            <td>
              <span class="badge ${remarkClass}" style="font-size:0.78rem;padding:3px 8px;border-radius:12px;">
                ${escapeHtml(remarkLabel)}
              </span>
            </td>
          </tr>
        `;
      });
      tableBody.innerHTML = rowsHtml;
    }
  }

  // Render Visual Charts
  renderCategoryBarChart(auditData);
  renderVarianceTrendLine(allAnalyticsList);
}

/**
 * Visual Chart 1: Category Comparison Bar Chart (Historical vs Shopkeeper)
 * Rendered natively on HTML5 Canvas (zero external CDN dependencies)
 */
function renderCategoryBarChart(auditData) {
  const canvas = document.getElementById('category-bar-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);

  const items = auditData.items_breakdown || [];
  if (items.length === 0) {
    ctx.fillStyle = '#64748B';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('आलेखासाठी डेटा उपलब्ध नाही', width / 2, height / 2);
    return;
  }

  // Aggregate by top items (up to 5 items)
  const displayItems = items.slice(0, 5);
  const paddingLeft = 50;
  const paddingBottom = 40;
  const paddingTop = 25;
  const paddingRight = 20;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  let maxVal = 0;
  displayItems.forEach(it => {
    const gTot = it.govt_amount || (it.govt_rate * (it.qty || 1));
    const sTot = it.shopkeeper_amount || (it.shopkeeper_rate * (it.qty || 1));
    if (gTot > maxVal) maxVal = gTot;
    if (sTot > maxVal) maxVal = sTot;
  });
  maxVal = Math.ceil((maxVal || 100) * 1.15);

  // Draw grid lines
  ctx.strokeStyle = '#E2E8F0';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 4; i++) {
    const y = paddingTop + (chartH / 4) * i;
    ctx.moveTo(paddingLeft, y);
    ctx.lineTo(width - paddingRight, y);
    ctx.fillStyle = '#94A3B8';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    const labelVal = Math.round(maxVal - (maxVal / 4) * i);
    ctx.fillText(`₹${labelVal}`, paddingLeft - 6, y + 4);
  }
  ctx.stroke();

  // Draw bars
  const groupW = chartW / displayItems.length;
  const barW = Math.min(24, groupW * 0.35);

  displayItems.forEach((it, i) => {
    const groupX = paddingLeft + (i * groupW) + (groupW / 2);
    const gVal = it.govt_amount || (it.govt_rate * (it.qty || 1)) || 0;
    const sVal = it.shopkeeper_amount || (it.shopkeeper_rate * (it.qty || 1)) || 0;

    const gH = (gVal / maxVal) * chartH;
    const sH = (sVal / maxVal) * chartH;

    // Govt Bar (Blue)
    ctx.fillStyle = '#2563EB';
    ctx.fillRect(groupX - barW - 2, height - paddingBottom - gH, barW, gH);

    // Shopkeeper Bar (Orange)
    ctx.fillStyle = '#EA580C';
    ctx.fillRect(groupX + 2, height - paddingBottom - sH, barW, sH);

    // Label below
    ctx.fillStyle = '#334155';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    const shortName = (it.name || '').split(' ')[0].slice(0, 7);
    ctx.fillText(shortName, groupX, height - paddingBottom + 16);
  });

  // Legend
  ctx.fillStyle = '#2563EB';
  ctx.fillRect(width - 220, 10, 12, 12);
  ctx.fillStyle = '#1E293B';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('मागील खरेदी दर', width - 202, 20);

  ctx.fillStyle = '#EA580C';
  ctx.fillRect(width - 110, 10, 12, 12);
  ctx.fillStyle = '#1E293B';
  ctx.fillText('दुकानदार बिल', width - 92, 20);
}

let varianceChartInstance = null;

/**
 * Visual Chart 2: 30-Day Price Variance Trend Line (BUG 2)
 * Primary: Chart.js CDN line chart on #varianceTrendChart
 * Fallback: Native HTML5 2D Canvas rendering for offline resilience
 */
function renderCanvasFallback(canvas, labels, values) {
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = rect.width > 0 ? rect.width : (canvas.width || 460);
  const height = rect.height > 0 ? rect.height : (canvas.height || 260);

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, width, height);

  const paddingLeft = 45;
  const paddingBottom = 40;
  const paddingTop = 30;
  const paddingRight = 20;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  const maxVal = Math.max(...values, 8.0) * 1.2;
  const minVal = Math.min(0, Math.min(...values));
  const range = maxVal - minVal || 10;

  // Background subtle grid lines
  ctx.strokeStyle = '#E2E8F0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = paddingTop + (chartH / 4) * i;
    ctx.beginPath();
    ctx.moveTo(paddingLeft, y);
    ctx.lineTo(width - paddingRight, y);
    ctx.stroke();

    ctx.fillStyle = '#64748B';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    const val = Math.round(maxVal - (range / 4) * i);
    ctx.fillText(`${val}%`, paddingLeft - 6, y + 4);
  }

  // Draw smooth line
  const nPoints = values.length;
  const coords = [];
  for (let i = 0; i < nPoints; i++) {
    const x = paddingLeft + (i / Math.max(1, nPoints - 1)) * chartW;
    const y = paddingTop + chartH - ((values[i] - minVal) / range) * chartH;
    coords.push({ x, y, v: values[i], l: labels[i] });
  }

  // Draw gradient fill below line
  if (coords.length > 0) {
    const grad = ctx.createLinearGradient(0, paddingTop, 0, height - paddingBottom);
    grad.addColorStop(0, 'rgba(99, 102, 241, 0.25)');
    grad.addColorStop(1, 'rgba(99, 102, 241, 0.02)');
    ctx.beginPath();
    ctx.moveTo(coords[0].x, height - paddingBottom);
    coords.forEach(c => ctx.lineTo(c.x, c.y));
    ctx.lineTo(coords[coords.length - 1].x, height - paddingBottom);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
  }

  // Draw line stroke
  ctx.strokeStyle = '#6366F1';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  coords.forEach((c, idx) => {
    if (idx === 0) ctx.moveTo(c.x, c.y);
    else ctx.lineTo(c.x, c.y);
  });
  ctx.stroke();

  // Draw points and labels
  coords.forEach(c => {
    ctx.beginPath();
    ctx.arc(c.x, c.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#4F46E5';
    ctx.fill();
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Bottom label
    ctx.fillStyle = '#475569';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(c.l, c.x, height - paddingBottom + 16);
  });
}

function renderVarianceTrendChart(customData) {
  const canvas = document.getElementById('varianceTrendChart') || document.getElementById('variance-trend-canvas');
  if (!canvas) return;

  const defaultLabels = ['दिवस १', 'दिवस ५', 'दिवस १०', 'दिवस १५', 'दिवस २०', 'दिवस २५', 'दिवस ३०'];
  const defaultValues = [4.5, 5.0, 6.2, 5.8, 7.0, 6.5, 7.0];

  let labels = defaultLabels;
  let values = defaultValues;
  let labelName = '३० दिवसांचा दर तफावत कल (%)';

  if (customData && Array.isArray(customData.labels) && Array.isArray(customData.data) && customData.data.length > 0) {
    labels = customData.labels;
    values = customData.data;
    if (customData.title) labelName = customData.title;
  } else if (Array.isArray(customData) && customData.length > 0) {
    labels = customData.map((d, i) => d.created_at ? `सत्र ${i + 1}` : `दिवस ${(i + 1) * 3}`);
    values = customData.map(d => typeof d === 'number' ? d : (d.variance_percentage || d.total_variance_amount || 5.0));
  }

  // 1. Try Chart.js CDN first
  if (typeof Chart !== 'undefined') {
    try {
      if (varianceChartInstance) {
        varianceChartInstance.destroy();
        varianceChartInstance = null;
      }
      const ctx = canvas.getContext('2d');
      varianceChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: labelName,
            data: values,
            borderColor: '#6366F1',
            backgroundColor: 'rgba(99, 102, 241, 0.15)',
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#4F46E5',
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointRadius: 4.5,
            pointHoverRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                boxWidth: 12,
                font: { family: 'inherit', size: 12, weight: '600' },
                color: '#1E293B'
              }
            },
            tooltip: {
              callbacks: {
                label: function (context) {
                  return `तफावत: ${context.parsed.y}%`;
                }
              }
            }
          },
          scales: {
            y: {
              title: {
                display: true,
                text: 'तफावत (%)',
                color: '#64748B',
                font: { size: 11, weight: '600' }
              },
              grid: { color: '#E2E8F0' },
              ticks: { color: '#64748B', font: { size: 10 } }
            },
            x: {
              grid: { color: '#F1F5F9' },
              ticks: { color: '#64748B', font: { size: 10 } }
            }
          }
        }
      });
      return;
    } catch (err) {
      console.warn("[VarianceTrendChart] Chart.js render failed, falling back to 2D canvas:", err);
    }
  }

  // 2. HTML5 2D Canvas Fallback
  renderCanvasFallback(canvas, labels, values);
}

function renderVarianceTrendLine(analyticsList) {
  if (analyticsList && analyticsList.length >= 2) {
    const points = analyticsList.slice(0, 10).reverse();
    const labels = points.map((p, idx) => `सत्र ${idx + 1}`);
    const data = points.map(p => {
      const fair = p.fair_retail_total_amount || 1.0;
      const v = p.total_variance_amount || 0.0;
      return Math.round((v / fair) * 1000) / 10;
    });
    renderVarianceTrendChart({ labels, data, title: 'सत्रांमधील दर तफावत कल (%)' });
  } else {
    renderVarianceTrendChart();
  }
}

/**
 * ==============================================================================
 * MODULE 4B: BATCH SAVED GROCERY LIST AUDIT ENGINE (BUG 1)
 * ==============================================================================
 */
function initSavedListImportAudit() {
  const triggerBtn = document.getElementById('btn-import-history-receipt') || document.getElementById('btn-import-saved-list');
  const modal = document.getElementById('import-saved-list-modal');
  const closeBtn = document.getElementById('close-import-saved-list-modal');
  const cancelBtn = document.getElementById('cancel-import-saved-list-btn');

  function openModal() {
    if (modal) {
      modal.classList.add('active');
      loadHistoricalReceiptsForAudit();
    }
  }

  function closeModal() {
    if (modal) modal.classList.remove('active');
  }

  if (triggerBtn) {
    triggerBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openModal();
    });
    triggerBtn.addEventListener('touchend', (e) => {
      e.preventDefault();
      openModal();
    });
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }
}

async function loadHistoricalReceiptsForAudit() {
  const container = document.getElementById('saved-lists-for-audit-container');
  if (!container) return;

  container.innerHTML = `<div style="text-align:center;padding:24px;color:#64748B;">खरेदी इतिहासातील पावत्या लोड होत आहेत...</div>`;

  let receipts = [];
  try {
    const resp = await fetch('/api/purchase-history');
    if (resp.ok) {
      receipts = await resp.json();
    }
  } catch (e) {
    console.warn("[PurchaseHistory] Fetch failed:", e);
  }

  // Pre-populated default staple sample receipts if none exist in DB
  if (!receipts || receipts.length === 0) {
    receipts = [
      {
        receipt_id: 'REC-0001',
        merchant_name: 'पाटील किराणा स्टोअर्स',
        invoice_date: 'आज, ०४:३० PM',
        total_items: 8,
        billed_amount: 1195.89,
        items: [
          { commodity_name: 'साबुदाणा', name: 'साबुदाणा', quantity: 500, qty: 500, unit: 'ग्रॅम', billed_rate: 92.82 },
          { commodity_name: 'मैदा', name: 'मैदा', quantity: 500, qty: 500, unit: 'ग्रॅम', billed_rate: 67.20 },
          { commodity_name: 'साखर', name: 'साखर', quantity: 2, qty: 2, unit: 'kg', billed_rate: 55.44 },
          { commodity_name: 'गोडतेल', name: 'गोडतेल', quantity: 2, qty: 2, unit: 'ltr', billed_rate: 173.88 },
          { commodity_name: 'तूर डाळ', name: 'तूर डाळ', quantity: 1, qty: 1, unit: 'kg', billed_rate: 189.95 },
          { commodity_name: 'तांदूळ', name: 'तांदूळ', quantity: 5, qty: 5, unit: 'kg', billed_rate: 65.69 },
          { commodity_name: 'कांदा', name: 'कांदा', quantity: 2, qty: 2, unit: 'kg', billed_rate: 39.02 },
          { commodity_name: 'पोहे', name: 'पोहे', quantity: 1, qty: 1, unit: 'kg', billed_rate: 60.80 }
        ]
      },
      {
        receipt_id: 'REC-0002',
        merchant_name: 'गणेश सुपर मार्केट',
        invoice_date: 'काल, ११:१५ AM',
        total_items: 5,
        billed_amount: 780.00,
        items: [
          { commodity_name: 'साबुदाणा', name: 'साबुदाणा', quantity: 1, qty: 1, unit: 'kg', billed_rate: 95.00 },
          { commodity_name: 'साखर', name: 'साखर', quantity: 3, qty: 3, unit: 'kg', billed_rate: 54.00 },
          { commodity_name: 'शेंगदाणे', name: 'शेंगदाणे', quantity: 1, qty: 1, unit: 'kg', billed_rate: 175.00 },
          { commodity_name: 'बेसन', name: 'बेसन', quantity: 1, qty: 1, unit: 'kg', billed_rate: 110.00 },
          { commodity_name: 'पोहे', name: 'पोहे', quantity: 2, qty: 2, unit: 'kg', billed_rate: 62.00 }
        ]
      }
    ];
  }

  let html = '';
  receipts.forEach((rec, idx) => {
    const receiptNum = rec.receipt_id || `पावती #${idx + 1}`;
    const merchant = rec.merchant_name || 'किराणा स्टोअर्स';
    const items = rec.items || [];
    const count = rec.total_items || items.length;
    const dateStr = rec.invoice_date || 'मागील खरेदी';
    const billAmt = rec.billed_amount || 0.0;
    const previewItems = items.slice(0, 4).map(i => i.commodity_name || i.name).filter(Boolean).join(', ');

    html += `
      <div style="background:#F8FAFC;border:1.5px solid #CBD5E1;border-radius:10px;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px;transition:all 0.2s;">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <span style="font-weight:800;font-size:1.02rem;color:#0F172A;">🧾 ${escapeHtml(receiptNum)}</span>
            <span style="background:#FEF3C7;color:#92400E;font-size:0.75rem;padding:2px 8px;border-radius:10px;font-weight:700;">
              🏪 ${escapeHtml(merchant)}
            </span>
            <span style="background:#DCFCE7;color:#166534;font-size:0.75rem;padding:2px 8px;border-radius:10px;font-weight:700;">
              बिल: ${formatINR(billAmt)}
            </span>
          </div>
          <div style="font-size:0.84rem;color:#64748B;margin-top:6px;">
            ${escapeHtml(previewItems ? previewItems + '...' : 'वस्तू तपशील')} (${toDevanagariDigits(count)} वस्तू)
          </div>
          <div style="font-size:0.75rem;color:#94A3B8;margin-top:3px;">📅 ${escapeHtml(dateStr)}</div>
        </div>
        <div>
          <button type="button" class="btn btn-warning btn-sm batch-audit-run-btn" data-index="${idx}" style="font-weight:700;display:flex;align-items:center;gap:6px;padding:8px 14px;border-radius:6px;white-space:nowrap;background:#F59E0B;color:#000000;border:none;cursor:pointer;">
            📜 पावतीचे थेट ऑडिट करा
          </button>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;

  container.querySelectorAll('.batch-audit-run-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.index, 10);
      const selectedReceipt = receipts[idx];
      const modal = document.getElementById('import-saved-list-modal');
      if (modal) modal.classList.remove('active');
      if (selectedReceipt) {
        runBatchListAudit(selectedReceipt);
      }
    });
  });
}

async function runBatchListAudit(receipt) {
  const receiptTitle = receipt.merchant_name 
    ? `${receipt.merchant_name} (${receipt.receipt_id || 'पावती'})` 
    : (receipt.list_name || receipt.name || 'खरेदी पावती');

  const banner = document.getElementById('audit-variance-banner');
  if (banner) {
    banner.className = 'alert alert-info fw-bold';
    banner.innerHTML = `⏳ "${escapeHtml(receiptTitle)}" चे थेट ३-वे ऑडिट चालू आहे...`;
  }

  const tableBody = document.getElementById('audit-items-table-body');
  if (tableBody) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:#4F46E5;font-weight:700;">पावतीतील सर्व वस्तूंचे एकाच वेळी ३-वे ऑडिट चालू आहे...</td></tr>`;
  }

  try {
    const resp = await fetch('/api/batch-audit-list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        list_name: receiptTitle,
        items: receipt.items || []
      })
    });

    if (!resp.ok) {
      throw new Error(`सर्व्हर त्रुटी: ${resp.status}`);
    }

    const data = await resp.json();
    if (data.status === 'success') {
      renderBatchAuditResults(data);
    } else {
      throw new Error(data.message || 'ऑडिट अयशस्वी');
    }
  } catch (err) {
    console.error("[runBatchListAudit] Error:", err);
    if (banner) {
      banner.className = 'alert alert-danger fw-bold';
      banner.innerHTML = `❌ पावती ऑडिट अयशस्वी झाले: ${escapeHtml(err.message)}`;
    }
  }
}

function renderBatchAuditResults(data) {
  const auditItems = data.items || [];

  let grandApmcTotal = 0.0;
  let grandFairRetailTotal = 0.0;
  let grandStoreTotal = 0.0;

  auditItems.forEach(item => {
    // Calculate exact itemized row values based on normalized quantity:
    let qty = parseFloat(item.quantity) || 1.0;
    const unit = (item.unit || '').toLowerCase().trim();
    if (unit === 'ग्रॅम' || unit === 'gm' || unit === 'g' || unit === 'मिली' || unit === 'ml') {
      qty = qty / 1000.0;
    }

    const rowApmc = (parseFloat(item.apmc_rate) || 0.0) * qty;
    const rowFair = (parseFloat(item.fair_rate) || 0.0) * qty;
    const rowStore = (parseFloat(item.store_rate) || 0.0) * qty;

    grandApmcTotal += rowApmc;
    grandFairRetailTotal += rowFair;
    grandStoreTotal += rowStore;
  });

  const netVariance = grandStoreTotal - grandFairRetailTotal;

  // Direct DOM population:
  const elCardApmc = document.getElementById('card-hist-ref-total') || document.getElementById('card-apmc-total');
  if (elCardApmc) elCardApmc.innerText = '₹' + grandApmcTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  
  const elCardFair = document.getElementById('card-fair-total');
  if (elCardFair) elCardFair.innerText = '₹' + grandFairRetailTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  
  const elCardStore = document.getElementById('card-store-total');
  if (elCardStore) elCardStore.innerText = '₹' + grandStoreTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  
  const marginCard = document.getElementById('card-net-margin');
  if (marginCard) {
    marginCard.innerText = '₹' + (grandStoreTotal - grandApmcTotal).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Dual-compatibility for existing element IDs
  const govtTotEl = document.getElementById('audit-govt-total');
  if (govtTotEl && !elCardApmc) govtTotEl.innerText = '₹' + grandApmcTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  
  const fairTotEl = document.getElementById('audit-fair-total');
  if (fairTotEl && !elCardFair) fairTotEl.innerText = '₹' + grandFairRetailTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  
  const shopTotEl = document.getElementById('audit-shop-total');
  if (shopTotEl && !elCardStore) shopTotEl.innerText = '₹' + grandStoreTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  
  const profitTotEl = document.getElementById('audit-profit-total');
  if (profitTotEl && !marginCard) profitTotEl.innerText = 'नफा: ₹' + (grandStoreTotal - grandApmcTotal).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const varianceBanner = document.getElementById('audit-variance-banner');
  if (varianceBanner) {
    if (netVariance > 0) {
      varianceBanner.className = 'alert alert-danger fw-bold';
      varianceBanner.innerHTML = `⚠️ संपूर्ण पावतीवर रास्त दरापेक्षा ₹${netVariance.toFixed(2)} जास्त आकारणी (Total Above Fair Price)`;
    } else {
      varianceBanner.className = 'alert alert-success fw-bold';
      varianceBanner.innerHTML = `✅ संपूर्ण पावती रास्त दरात आहे. ग्राहकाची ₹${Math.abs(netVariance).toFixed(2)} बचत झाली आहे.`;
    }
  }

  // Notice banner
  const noticeEl = document.getElementById('audit-unlisted-notice');
  if (noticeEl) {
    noticeEl.style.display = 'flex';
    noticeEl.style.background = '#EFF6FF';
    noticeEl.style.borderColor = '#93C5FD';
    noticeEl.style.color = '#1E40AF';
    noticeEl.innerHTML = `
      <span style="font-size:1.3rem;">📜</span>
      <div>
        <strong>खरेदी पावती ३-वे थेट ऑडिट: "${escapeHtml(data.list_name || 'खरेदी पावती')}" (${toDevanagariDigits(auditItems.length)} वस्तू)</strong>
        <div style="font-size:0.84rem;color:#2563EB;margin-top:2px;">
          पावतीतील प्रत्यक्ष दुकानदार दर (Billed Rate), मागील खरेदी दर व २२% रास्त किरकोळ दराशी एकाच वेळी तुलना पूर्ण झाली.
        </div>
      </div>
    `;
  }

  // Items breakdown table
  const tableBody = document.getElementById('audit-items-table-body');
  if (tableBody) {
    let rowsHtml = '';
    auditItems.forEach((item, idx) => {
      let qty = parseFloat(item.quantity) || 1.0;
      const rawUnit = (item.unit || '').trim();
      const unitLower = rawUnit.toLowerCase();
      let normQty = qty;
      if (unitLower === 'ग्रॅम' || unitLower === 'gm' || unitLower === 'g' || unitLower === 'मिली' || unitLower === 'ml') {
        normQty = qty / 1000.0;
      }

      const apmcRate = parseFloat(item.apmc_rate) || 0.0;
      const fairRate = parseFloat(item.fair_rate) || 0.0;
      const storeRate = parseFloat(item.store_rate) || 0.0;

      const rowApmc = apmcRate * normQty;
      const rowFair = fairRate * normQty;
      const rowStore = storeRate * normQty;
      const rowVariance = rowStore - rowFair;

      const diffSign = rowVariance > 0 ? '+' : '';
      const diffColor = rowVariance > 5.0 ? '#DC2626' : (rowVariance < -5.0 ? '#16A34A' : '#475569');

      // 3. CORRECT UNIT DISPLAY IN TABLE:
      // For solid items, display base rate as ₹XX.XX / किलो.
      // For 500 gm purchases, display: प्रमाण: ५०० ग्रॅम | दर: ₹७०.०० / किलो | एकूण: ₹३५.००. Never print ₹७०.०० / ग्रॅम.
      const isLiquid = /तेल|oil|तूप|ghee|दूध|milk/i.test(item.commodity_name || '');
      const baseUnit = isLiquid ? 'लिटर' : 'किलो';
      const isNewItem = item.is_new || !item.has_history;

      let badgeHtml = '';
      if (isNewItem) {
        badgeHtml = `<span style="background:#F1F5F9;color:#475569;font-size:0.78rem;padding:3px 8px;border-radius:12px;font-weight:700;">नवीन वस्तू (इतिहास उपलब्ध नाही)</span>`;
      } else if (rowVariance < -5.0) {
        badgeHtml = `<span style="background:#DCFCE7;color:#166534;font-size:0.78rem;padding:3px 8px;border-radius:12px;font-weight:700;">सवलत / Deal</span>`;
      } else if (rowVariance <= 5.0) {
        badgeHtml = `<span style="background:#E0F2FE;color:#0369A1;font-size:0.78rem;padding:3px 8px;border-radius:12px;font-weight:700;">वाजवी दर / Fair</span>`;
      } else if (rowVariance <= 10.0) {
        badgeHtml = `<span style="background:#FEF3C7;color:#92400E;font-size:0.78rem;padding:3px 8px;border-radius:12px;font-weight:700;">किंचित महाग / Moderate</span>`;
      } else {
        badgeHtml = `<span style="background:#FEE2E2;color:#991B1B;font-size:0.78rem;padding:3px 8px;border-radius:12px;font-weight:700;">महाग / Expensive</span>`;
      }

      const prevRateCell = isNewItem
        ? `<div style="color:#94A3B8;font-weight:700;text-align:center;">—</div>`
        : `<div>दर: ${formatINR(fairRate)} / ${baseUnit}</div><div style="font-size:0.8rem;color:#166534;font-weight:700;">एकूण: ${formatINR(rowFair)}</div>`;

      const apmcRateCell = isNewItem
        ? `<div style="color:#94A3B8;font-weight:700;text-align:center;">—</div>`
        : `<div>दर: ${formatINR(apmcRate)} / ${baseUnit}</div><div style="font-size:0.8rem;color:#475569;font-weight:600;">एकूण: ${formatINR(rowApmc)}</div>`;

      const varianceCell = isNewItem
        ? `<span style="color:#94A3B8;font-weight:700;text-align:center;">—</span>`
        : `<span style="color:${diffColor};font-weight:700;">${diffSign}${formatINR(rowVariance)}</span>`;

      rowsHtml += `
        <tr>
          <td style="text-align:center;">${toDevanagariDigits(idx + 1)}</td>
          <td><strong>${escapeHtml(item.commodity_name)}</strong></td>
          <td>
            <div style="font-weight:700;color:#0F172A;">प्रमाण: ${toDevanagariDigits(qty)} ${escapeHtml(rawUnit)}</div>
          </td>
          <td style="color:#64748B;">
            ${apmcRateCell}
          </td>
          <td style="color:#0F766E;font-weight:600;">
            ${prevRateCell}
          </td>
          <td style="font-weight:700;">
            <div>दर: ${formatINR(storeRate)} / ${baseUnit}</div>
            <div style="font-size:0.8rem;color:#0F172A;font-weight:800;">एकूण: ${formatINR(rowStore)}</div>
          </td>
          <td>${varianceCell}</td>
          <td>${badgeHtml}</td>
        </tr>
      `;
    });

    // Grand Total Footer Row
    const grandVarSign = netVariance >= 0 ? '+' : '';
    rowsHtml += `
      <tr style="background:#0F172A;color:#FFFFFF;font-weight:800;border-top:3px solid #334155;">
        <td style="text-align:center;color:#94A3B8;">∑</td>
        <td style="color:#FFFFFF;">एकूण पावती (Grand Total)</td>
        <td style="color:#CBD5E1;">${toDevanagariDigits(auditItems.length)} वस्तू</td>
        <td style="color:#93C5FD;">${formatINR(grandApmcTotal)}</td>
        <td style="color:#86EFAC;">${formatINR(grandFairRetailTotal)}</td>
        <td style="color:#FDE047;">${formatINR(grandStoreTotal)}</td>
        <td style="color:${netVariance > 5.0 ? '#FCA5A5' : '#86EFAC'};">${grandVarSign}${formatINR(netVariance)}</td>
        <td>
          <span style="background:${netVariance > 5.0 ? '#DC2626' : '#16A34A'};color:#FFFFFF;font-size:0.78rem;padding:4px 10px;border-radius:12px;font-weight:700;">
            ${netVariance > 5.0 ? 'महाग / Expensive' : 'वाजवी / Fair'}
          </span>
        </td>
      </tr>
    `;

    tableBody.innerHTML = rowsHtml;
  }

  // Update Category Comparison Bar Chart
  renderCategoryBarChart({
    items_breakdown: auditItems.map(i => {
      let q = parseFloat(i.quantity) || 1.0;
      const u = (i.unit || '').toLowerCase().trim();
      if (u === 'ग्रॅम' || u === 'gm' || u === 'g' || u === 'मिली' || u === 'ml') q = q / 1000.0;
      return {
        name: i.commodity_name,
        govt_amount: (parseFloat(i.apmc_rate) || 0) * q,
        shopkeeper_amount: (parseFloat(i.store_rate) || 0) * q,
        qty: i.quantity,
        govt_rate: i.apmc_rate,
        shopkeeper_rate: i.store_rate
      };
    })
  });

  // Update 30-Day Trend Chart with list variance distribution
  renderVarianceTrendChart({
    labels: auditItems.slice(0, 7).map(i => (i.commodity_name || '').slice(0, 6)),
    data: auditItems.slice(0, 7).map(i => {
      let q = parseFloat(i.quantity) || 1.0;
      const u = (i.unit || '').toLowerCase().trim();
      if (u === 'ग्रॅम' || u === 'gm' || u === 'g' || u === 'मिली' || u === 'ml') q = q / 1000.0;
      return Math.round(((parseFloat(i.store_rate) || 0) - (parseFloat(i.fair_rate) || 0)) * q * 100) / 100;
    }),
    title: 'पावतीतील वस्तूंची दर तफावत (₹)'
  });
}

// Global exports for accessibility from other modules
window.renderVarianceTrendChart = renderVarianceTrendChart;
window.renderVarianceTrendLine = renderVarianceTrendLine;
window.runBatchListAudit = runBatchListAudit;
window.initSavedListImportAudit = initSavedListImportAudit;

/**
 * ==============================================================================
 * MODULE 4: SIDE-BY-SIDE TRIP COMPARATOR
 * ==============================================================================
 */
async function loadTripsForComparator() {
  try {
    const resp = await fetch('/api/v1/trips?limit=20');
    allTripsList = await resp.json();

    const selectA = document.getElementById('compare-trip-a');
    const selectB = document.getElementById('compare-trip-b');
    const compareBtn = document.getElementById('run-compare-btn');

    if (!selectA || !selectB) return;

    selectA.innerHTML = '<option value="">-- पहिली खरेदी निवडा --</option>';
    selectB.innerHTML = '<option value="">-- दुसरी खरेदी निवडा --</option>';

    allTripsList.forEach((t, i) => {
      const optA = `<option value="${t.trip_id}" ${i === 1 ? 'selected' : ''}>${t.merchant_name} (${t.trip_date}) - ${formatINR(t.settled_total)}</option>`;
      const optB = `<option value="${t.trip_id}" ${i === 0 ? 'selected' : ''}>${t.merchant_name} (${t.trip_date}) - ${formatINR(t.settled_total)}</option>`;
      selectA.innerHTML += optA;
      selectB.innerHTML += optB;
    });

    if (compareBtn) {
      const handleCompare = (e) => {
        if (e && e.type === 'touchend') e.preventDefault();
        runTripComparison();
      };
      compareBtn.addEventListener('click', handleCompare);
      compareBtn.addEventListener('touchend', handleCompare);
      if (allTripsList.length >= 2) {
        runTripComparison();
      }
    }

  } catch (err) {
    console.error("Failed to load trips for comparator", err);
  }
}

async function runTripComparison() {
  const selectA = document.getElementById('compare-trip-a');
  const selectB = document.getElementById('compare-trip-b');

  const idA = selectA ? selectA.value : null;
  const idB = selectB ? selectB.value : null;

  if (!idA || !idB || idA === idB) {
    alert("कृपया तुलनेसाठी दोन वेगवेगळ्या खरेदी नोंदी निवडा.");
    return;
  }

  try {
    const resp = await fetch(`/api/v1/analyzer/compare-trips?trip_a_id=${idA}&trip_b_id=${idB}`);
    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.detail || "तुलना करता आली नाही.");
    }

    renderComparisonTable(data);

  } catch (err) {
    alert(err.message);
  }
}

function renderComparisonTable(data) {
  const container = document.getElementById('comparison-results-wrap');
  if (!container) return;

  let rowsHtml = '';
  data.rows.forEach(r => {
    const rateA = r.trip_a_rate ? `${formatINR(r.trip_a_rate)}/${r.unit}` : '—';
    const rateB = r.trip_b_rate ? `${formatINR(r.trip_b_rate)}/${r.unit}` : '—';
    const totalA = r.trip_a_total ? formatINR(r.trip_a_total) : '—';
    const totalB = r.trip_b_total ? formatINR(r.trip_b_total) : '—';

    let diffClass = '';
    let diffStr = '—';
    if (r.var_pct !== null) {
      if (r.var_pct > 0) {
        diffClass = 'diff-positive';
        diffStr = `+${r.var_pct}% (${formatINR(r.rate_diff)})`;
      } else if (r.var_pct < 0) {
        diffClass = 'diff-negative';
        diffStr = `${r.var_pct}% (${formatINR(r.rate_diff)})`;
      } else {
        diffStr = `0%`;
      }
    }

    rowsHtml += `
      <tr>
        <td><strong>${r.name}</strong></td>
        <td>${rateA}</td>
        <td>${totalA}</td>
        <td>${rateB}</td>
        <td>${totalB}</td>
        <td class="${diffClass}">${diffStr}</td>
      </tr>
    `;
  });

  const basketDiffCls = data.basket_diff > 0 ? 'diff-positive' : 'diff-negative';

  container.innerHTML = `
    <div style="background:#F8FAFC;padding:16px 20px;border-radius:10px;margin-bottom:16px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;">
      <div>
        <strong>खरेदी अ:</strong> ${data.trip_a.merchant} (${data.trip_a.date}) — <strong>${formatINR(data.trip_a.total)}</strong>
      </div>
      <div>
        <strong>खरेदी ब:</strong> ${data.trip_b.merchant} (${data.trip_b.date}) — <strong>${formatINR(data.trip_b.total)}</strong>
      </div>
      <div class="${basketDiffCls}" style="font-size:1.1rem;">
        बजेट फरक: ${data.basket_diff > 0 ? '+' : ''}${formatINR(data.basket_diff)} (${data.basket_var_pct > 0 ? '+' : ''}${data.basket_var_pct}%)
      </div>
    </div>
    <div class="table-responsive" style="overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;">
      <table class="table comparison-table" style="min-width:580px;width:100%;">
        <thead>
          <tr>
            <th>वस्तूचे नाव</th>
            <th>खरेदी अ (दर)</th>
            <th>खरेदी अ (रक्कम)</th>
            <th>खरेदी ब (दर)</th>
            <th>खरेदी ब (रक्कम)</th>
            <th>दर फरक (%)</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * ==============================================================================
 * MODULE 4: VOLATILITY & PRICE TREND VISUALIZER (30/60/90 Days)
 * ==============================================================================
 */
async function loadPriceTrends(days = 30) {
  document.querySelectorAll('.trend-day-btn').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.dataset.days, 10) === days);
  });

  try {
    const resp = await fetch(`/api/v1/analyzer/trends?days=${days}`);
    const data = await resp.json();

    if (!resp.ok) return;

    renderSurgesAndDips(data.surges, data.dips);
    renderInteractiveTrendSvg(data.series);

  } catch (err) {
    console.error("Trends fetch failed", err);
  }
}

function renderSurgesAndDips(surges, dips) {
  const surgeContainer = document.getElementById('surge-items-container');
  const dipContainer = document.getElementById('dip-items-container');

  if (surgeContainer) {
    if (surges.length === 0) {
      surgeContainer.innerHTML = '<div style="color:#64748B;font-size:0.9rem;padding:12px;">या कालावधीत कोणतीही मोठी भाववाढ नोंदवलेली नाही.</div>';
    } else {
      surgeContainer.innerHTML = surges.map(s => `
        <div class="trend-item-row surge">
          <div>
            <strong style="color:#1E293B;">${s.name}</strong>
            <div style="font-size:0.8rem;color:#64748B;">${formatINR(s.old_rate)} ➔ ${formatINR(s.new_rate)} / ${s.unit}</div>
          </div>
          <div style="text-align:right;">
            <span class="badge badge-surge">+${s.pct_change}%</span>
            <div style="font-size:0.8rem;color:#DC2626;font-weight:600;">+${formatINR(s.diff_amount)}</div>
          </div>
        </div>
      `).join('');
    }
  }

  if (dipContainer) {
    if (dips.length === 0) {
      dipContainer.innerHTML = '<div style="color:#64748B;font-size:0.9rem;padding:12px;">या कालावधीत लक्षणीय दर कपात नोंदवलेली नाही.</div>';
    } else {
      dipContainer.innerHTML = dips.map(d => `
        <div class="trend-item-row dip">
          <div>
            <strong style="color:#1E293B;">${d.name}</strong>
            <div style="font-size:0.8rem;color:#64748B;">${formatINR(d.old_rate)} ➔ ${formatINR(d.new_rate)} / ${d.unit}</div>
          </div>
          <div style="text-align:right;">
            <span class="badge badge-dip">${d.pct_change}%</span>
            <div style="font-size:0.8rem;color:#0284C7;font-weight:600;">${formatINR(d.diff_amount)}</div>
          </div>
        </div>
      `).join('');
    }
  }
}

function renderInteractiveTrendSvg(series) {
  const chartBox = document.getElementById('trend-chart-wrapper');
  if (!chartBox) return;

  if (!series || series.length === 0) {
    chartBox.innerHTML = '<div style="text-align:center;color:#64748B;padding:40px;">किमान २ खरेदी नोंदींनंतर येथे परस्परसंवादी आलेख दिसेल.</div>';
    return;
  }

  const width = 800;
  const height = 300;
  const padLeft = 60;
  const padRight = 40;
  const padTop = 30;
  const padBottom = 40;

  let minRate = Infinity;
  let maxRate = -Infinity;
  series.forEach(s => {
    s.points.forEach(p => {
      if (p.rate < minRate) minRate = p.rate;
      if (p.rate > maxRate) maxRate = p.rate;
    });
  });

  if (minRate === Infinity) { minRate = 0; maxRate = 100; }
  minRate = Math.max(0, Math.floor(minRate * 0.9));
  maxRate = Math.ceil(maxRate * 1.1);
  if (minRate === maxRate) maxRate += 20;

  const colors = ['#FF6A00', '#2563EB', '#16A34A', '#9333EA', '#DC2626', '#0891B2'];

  let pathsHtml = '';
  let legendHtml = '';

  series.forEach((s, idx) => {
    const color = colors[idx % colors.length];
    legendHtml += `
      <div style="display:flex;align-items:center;gap:6px;font-size:0.85rem;font-weight:600;">
        <span style="display:inline-block;width:12px;height:12px;background:${color};border-radius:3px;"></span>
        <span>${s.name}</span>
      </div>
    `;

    if (s.points.length < 2) return;

    const nPoints = s.points.length;
    const pathD = s.points.map((pt, pIdx) => {
      const x = padLeft + (pIdx / (nPoints - 1)) * (width - padLeft - padRight);
      const y = height - padBottom - ((pt.rate - minRate) / (maxRate - minRate)) * (height - padTop - padBottom);
      return `${pIdx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');

    pathsHtml += `<path d="${pathD}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round"/>`;

    s.points.forEach((pt, pIdx) => {
      const x = padLeft + (pIdx / (nPoints - 1)) * (width - padLeft - padRight);
      const y = height - padBottom - ((pt.rate - minRate) / (maxRate - minRate)) * (height - padTop - padBottom);
      pathsHtml += `
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4.5" fill="#FFFFFF" stroke="${color}" stroke-width="2.5">
          <title>${s.name}: ₹${pt.rate} (${pt.date})</title>
        </circle>
      `;
    });
  });

  chartBox.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:10px;">
      <h3 style="font-size:1.15rem;font-weight:700;">किराणा दर हालचालींचा तुलनात्मक आलेख (Price Trends)</h3>
      <div style="display:flex;gap:14px;flex-wrap:wrap;">
        ${legendHtml}
      </div>
    </div>
    <div style="width:100%;overflow-x:auto;">
      <svg viewBox="0 0 ${width} ${height}" style="width:100%;max-width:${width}px;height:auto;background:#FFFFFF;border-radius:8px;">
        <line x1="${padLeft}" y1="${padTop}" x2="${width - padRight}" y2="${padTop}" stroke="#E2E8F0" stroke-dasharray="4"/>
        <line x1="${padLeft}" y1="${(padTop + height - padBottom)/2}" x2="${width - padRight}" y2="${(padTop + height - padBottom)/2}" stroke="#E2E8F0" stroke-dasharray="4"/>
        <line x1="${padLeft}" y1="${height - padBottom}" x2="${width - padRight}" y2="${height - padBottom}" stroke="#CBD5E1"/>

        <text x="${padLeft - 8}" y="${padTop + 4}" font-size="11" fill="#64748B" text-anchor="end">₹${maxRate}</text>
        <text x="${padLeft - 8}" y="${(padTop + height - padBottom)/2 + 4}" font-size="11" fill="#64748B" text-anchor="end">₹${Math.round((minRate+maxRate)/2)}</text>
        <text x="${padLeft - 8}" y="${height - padBottom + 4}" font-size="11" fill="#64748B" text-anchor="end">₹${minRate}</text>

        ${pathsHtml}
      </svg>
    </div>
  `;
}

// ==============================================================================
// 3-Way Audit Receipt Scanner (Gemini Multimodal Vision OCR)
// ==============================================================================
function initAnalyzerReceiptScanner() {
  const triggerBtn = document.getElementById('btn-analyzer-camera-scan');
  const modal = document.getElementById('analyzerPhotoSourceModal');
  const closeBtn = document.getElementById('close-analyzer-photo-modal');
  const camBtn = document.getElementById('btn-analyzer-action-camera');
  const galBtn = document.getElementById('btn-analyzer-action-gallery');
  const camInput = document.getElementById('analyzer-camera-input');
  const galInput = document.getElementById('analyzer-gallery-input');
  const loader = document.getElementById('analyzer-photo-processing-loader');

  if (!triggerBtn) return;

  function openModal() {
    if (modal) {
      modal.classList.add('active');
      modal.style.display = 'flex';
    }
  }

  function closeModal() {
    if (modal) {
      modal.classList.remove('active');
      modal.style.display = 'none';
    }
  }

  triggerBtn.addEventListener('click', (e) => {
    e.preventDefault();
    openModal();
  });

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }

  // Desktop WebRTC Live Webcam Modal Elements (Analyzer)
  const webcamModal = document.getElementById('analyzerWebcamLiveModal');
  const webcamVideo = document.getElementById('analyzer-webcam-video-feed');
  const webcamCanvas = document.getElementById('analyzer-webcam-snapshot-canvas');
  const closeWebcamBtn = document.getElementById('close-analyzer-webcam-modal');
  const cancelWebcamBtn = document.getElementById('btn-analyzer-cancel-webcam');
  const captureSnapshotBtn = document.getElementById('btn-analyzer-capture-snapshot');
  let webcamStream = null;

  function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent || navigator.vendor || window.opera);
  }

  function stopWebcam() {
    if (webcamStream) {
      webcamStream.getTracks().forEach(track => {
        try { track.stop(); } catch (err) {}
      });
      webcamStream = null;
    }
    if (webcamVideo) {
      webcamVideo.srcObject = null;
    }
  }

  function hideWebcamModal() {
    stopWebcam();
    if (webcamModal) {
      webcamModal.classList.remove('active');
      webcamModal.style.display = 'none';
    }
  }

  async function openLiveWebcam() {
    closeModal();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      if (camInput) camInput.click();
      return;
    }

    if (webcamModal) {
      webcamModal.classList.add('active');
      webcamModal.style.display = 'flex';
    }

    try {
      webcamStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      });
      if (webcamVideo) {
        webcamVideo.srcObject = webcamStream;
        webcamVideo.play();
      }
    } catch (err) {
      console.warn("[Analyzer Webcam Warning]:", err);
      stopWebcam();
      hideWebcamModal();
      const warnMsg = "कॅमेरा सुरू करता आला नाही किंवा परवानगी नाकारली आहे. कृपया फाइल निवडा.";
      if (typeof showToast === 'function') {
        showToast(warnMsg, 'warn', 4000);
      }
      if (camInput) camInput.click();
    }
  }

  if (closeWebcamBtn) closeWebcamBtn.addEventListener('click', hideWebcamModal);
  if (cancelWebcamBtn) cancelWebcamBtn.addEventListener('click', hideWebcamModal);
  if (webcamModal) {
    webcamModal.addEventListener('click', (e) => {
      if (e.target === webcamModal) hideWebcamModal();
    });
  }

  if (captureSnapshotBtn && webcamVideo && webcamCanvas) {
    captureSnapshotBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const vw = webcamVideo.videoWidth || 1280;
      const vh = webcamVideo.videoHeight || 720;
      webcamCanvas.width = vw;
      webcamCanvas.height = vh;
      const ctx = webcamCanvas.getContext('2d');
      ctx.drawImage(webcamVideo, 0, 0, vw, vh);

      hideWebcamModal();

      webcamCanvas.toBlob((blob) => {
        if (blob) {
          handleFileSelected(blob);
        }
      }, 'image/jpeg', 0.95);
    });
  }

  if (camBtn) {
    camBtn.addEventListener('click', (e) => {
      e.preventDefault();
      if (!isMobileDevice() && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        openLiveWebcam();
      } else if (camInput) {
        camInput.click();
      }
    });
  }

  if (galBtn && galInput) {
    galBtn.addEventListener('click', (e) => {
      e.preventDefault();
      galInput.click();
    });
  }

  async function handleFileSelected(file) {
    if (!file) return;
    closeModal();

    if (loader) {
      loader.classList.remove('d-none');
      loader.classList.add('active');
      loader.style.display = 'flex';
    }

    try {
      const formData = new FormData();
      formData.append('image', file);

      const resp = await fetch('/api/scan-grocery-image', {
        method: 'POST',
        body: formData
      });

      if (!resp.ok) {
        throw new Error(`सर्व्हर त्रुटी: ${resp.status}`);
      }

      const scanData = await resp.json();

      if (scanData.success && Array.isArray(scanData.items) && scanData.items.length > 0) {
        // Map scanned items (with extracted prices) into batch audit format
        const auditItems = scanData.items.map(it => {
          const qty = parseFloat(it.quantity || it.qty || 1.0) || 1.0;
          const price = parseFloat(it.price || it.target_price || 0.0) || 0.0;
          const unit = it.unit || 'किलो';
          const unitLower = unit.toLowerCase().trim();
          const normQty = (unitLower === 'ग्रॅम' || unitLower === 'gm' || unitLower === 'g' || unitLower === 'मिली' || unitLower === 'ml') ? (qty / 1000.0) : qty;
          const billedRate = (price > 0 && normQty > 0) ? (price / normQty) : 0;
          return {
            commodity_name: it.item_name || it.name,
            quantity: qty,
            unit: unit,
            billed_rate: billedRate > 0 ? billedRate : null,
            store_rate: billedRate > 0 ? billedRate : null,
            price: price
          };
        });

        // Run Batch 3-Way Audit Engine
        const batchResp = await fetch('/api/batch-audit-list', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            list_name: "स्कॅन पावती - थेट ३-वे ऑडिट",
            receipt_title: "स्कॅन पावती - थेट ३-वे ऑडिट",
            items: auditItems
          })
        });

        if (!batchResp.ok) {
          throw new Error(`ऑडिट सर्व्हर त्रुटी: ${batchResp.status}`);
        }

        const auditData = await batchResp.json();
        if (auditData.status === 'success') {
          renderBatchAuditResults(auditData);
          if (typeof showToast === 'function') {
            showToast(`✅ स्कॅन केलेल्या पावतीतील ${scanData.items.length} वस्तूंचे ३-वे ऑडिट पूर्ण झाले!`, 'success', 4000);
          }
          const cardsGrid = document.querySelector('.audit-3way-grid');
          if (cardsGrid) {
            cardsGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        } else {
          throw new Error(auditData.message || "ऑडिट प्रक्रिया पूर्ण होऊ शकली नाही.");
        }
      } else {
        const errorMsg = "⚠️ पावतीचा फोटो स्पष्ट दिसत नाही किंवा वस्तू ओळखता आल्या नाहीत. कृपया पुन्हा स्पष्ट फोटो काढा.";
        if (typeof showToast === 'function') {
          showToast(errorMsg, 'error', 4500);
        } else {
          alert(errorMsg);
        }
      }
    } catch (err) {
      console.error("[AnalyzerReceiptScanner Error]:", err);
      const errorMsg = "⚠️ पावती स्कॅन करताना त्रुटी आली: " + (err.message || "कृपया पुन्हा प्रयत्न करा.");
      if (typeof showToast === 'function') {
        showToast(errorMsg, 'error', 4500);
      } else {
        alert(errorMsg);
      }
    } finally {
      if (loader) {
        loader.classList.add('d-none');
        loader.classList.remove('active');
        loader.style.display = 'none';
      }
      if (camInput) camInput.value = '';
      if (galInput) galInput.value = '';
    }
  }

  if (camInput) {
    camInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) handleFileSelected(file);
    });
  }

  if (galInput) {
    galInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) handleFileSelected(file);
    });
  }
}

/**
 * Seasonal / Event List Replay Controller (PILLAR 3)
 */
function initSimulatorReplayEvents() {
  document.querySelectorAll('.btn-replay-event').forEach(btn => {
    btn.onclick = async () => {
      const occasion = btn.getAttribute('data-occasion') || 'दिवाळी';
      try {
        const resp = await fetch(`/api/analytics/seasonal-replay?occasion=${encodeURIComponent(occasion)}`);
        const data = await resp.json();
        if (data.found && data.suggested_items && data.suggested_items.length > 0) {
          const container = document.getElementById('sim-items-container');
          if (container) container.innerHTML = '';
          data.suggested_items.forEach(it => {
            const rawName = (it.name || it.commodity_name || '').toLowerCase();
            const matched = catalogItems.find(c => rawName.includes(c.marathi_name.toLowerCase()) || c.marathi_name.toLowerCase().includes(rawName));
            const skuId = matched ? matched.sku_id : (catalogItems[0] ? catalogItems[0].sku_id : 1);
            const qty = parseFloat(it.qty || it.quantity || 1.0) || 1.0;
            addSimulatorRow(skuId, qty);
          });
          recalculateSimulation();
          if (typeof showToast === 'function') {
            showToast(`🎉 "${data.event_title}" (${data.event_date || 'मागील नोंद'}) मधील ${data.suggested_items.length} वस्तू सिम्युलेटरमध्ये लोड झाल्या!`, 'success', 4000);
          }
        } else {
          if (typeof showToast === 'function') {
            showToast(`ℹ️ "${occasion}" ची मागील खरेदी नोंद सापडली नाही.`, 'info');
          }
        }
      } catch (err) {
        console.error("Replay error:", err);
      }
    };
  });
}

/**
 * Personal Household Inflation Index (PILLAR 3)
 */
async function loadPersonalInflationIndex() {
  const badgeEl = document.getElementById('personal-inflation-badge');
  const seriesEl = document.getElementById('personal-inflation-series-container');
  if (!badgeEl || !seriesEl) return;

  try {
    const resp = await fetch('/api/analytics/personal-inflation');
    const data = await resp.json();
    if (data.status === 'success') {
      const overall = data.overall_inflation_pct || 0.0;
      const isPositive = overall > 0;
      badgeEl.innerText = `${isPositive ? '+' : ''}${overall.toFixed(1)}% MoM`;
      badgeEl.style.background = isPositive ? '#FEE2E2' : '#DCFCE7';
      badgeEl.style.color = isPositive ? '#991B1B' : '#166534';

      let html = '';
      (data.series || []).forEach(s => {
        const mom = s.mom_inflation_pct || 0.0;
        const momColor = mom > 0 ? '#DC2626' : (mom < 0 ? '#16A34A' : '#475569');
        const momSign = mom > 0 ? '+' : '';
        html += `
          <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:10px 12px; text-align:center;">
            <div style="font-size:0.8rem; color:#64748B; font-weight:700;">${s.month}</div>
            <div style="font-size:1.05rem; font-weight:800; color:#1E293B; margin:4px 0;">₹${s.total_spend.toLocaleString('en-IN')}</div>
            <div style="font-size:0.78rem; font-weight:700; color:${momColor};">
              ${momSign}${mom}% MoM
            </div>
            <div style="font-size:0.72rem; color:#94A3B8;">${s.trips_count} फेऱ्या</div>
          </div>
        `;
      });
      seriesEl.innerHTML = html || '<div style="color:#64748B; font-size:0.85rem;">खरेदी नोंदींनुसार महागाई निर्देशांक लवकरच उपलब्ध होईल.</div>';
    }
  } catch (err) {
    console.error("Failed to load personal inflation:", err);
  }
}

/**
 * Historical Receipt Upload & Baseline Ingestion Controller (DIRECT ENTRY)
 * Multi-page preview, Bootstrap 5 scrollable modal, pinned footer & seamless row combine
 */
function initHistoricalBillModal() {
  const openBtn = document.getElementById('btn-open-historical-bill-modal');
  const modal = document.getElementById('uploadHistoricalBillModal');
  const closeBtn = document.getElementById('closeHistoricalBillModal') || document.getElementById('close-historical-bill-modal');
  const cancelBtn = document.getElementById('btnCancelHistoricalBill') || document.getElementById('btn-hist-bill-cancel');
  const saveBtn = document.getElementById('btnSaveHistoricalBill') || document.getElementById('btn-save-hist-bill-to-db');

  const dateInput = document.getElementById('historical-bill-date');
  const titleInput = document.getElementById('historical-bill-title');
  const chips = document.querySelectorAll('.hist-bill-chip');

  const camBtn = document.getElementById('btnTriggerCamera') || document.getElementById('btn-hist-bill-camera');
  const galBtn = document.getElementById('btnTriggerGallery') || document.getElementById('btn-hist-bill-gallery');
  const addMoreBtn = document.getElementById('btnAddMorePhoto');

  const fileInput = document.getElementById('historicalBillInput') || document.getElementById('hist-bill-gallery-input');
  const camInput = document.getElementById('historicalBillCameraInput') || document.getElementById('hist-bill-camera-input');
  const previewContainer = document.getElementById('imagePreviewContainer');

  const reviewArea = document.getElementById('hist-bill-review-area');
  const tbody = document.getElementById('hist-bill-items-table-body');
  const totalBadge = document.getElementById('hist-bill-total-badge');
  const loader = document.getElementById('analyzer-photo-processing-loader');

  // In-memory array of uploaded images: Array of { id, file, dataUrl }
  let uploadedImages = [];
  // In-memory array of transcribed items
  let scannedItems = [];

  // Desktop WebRTC Live Webcam Modal Elements (Historical Bill Scanner)
  const webcamModal = document.getElementById('analyzerLiveWebcamModal');
  const webcamVideo = document.getElementById('webcamVideoFeed');
  const webcamCanvas = document.getElementById('webcamCanvas');
  const captureWebcamBtn = document.getElementById('btnCaptureWebcam');
  const cancelWebcamBtn = document.getElementById('btnCancelWebcam');
  const closeWebcamModalBtn = document.getElementById('closeAnalyzerLiveWebcamModal');
  let webcamStream = null;

  function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent || navigator.vendor || window.opera);
  }

  function stopWebcam() {
    if (webcamStream) {
      webcamStream.getTracks().forEach(track => {
        try { track.stop(); } catch (err) {}
      });
      webcamStream = null;
    }
    if (webcamVideo) {
      webcamVideo.srcObject = null;
    }
  }

  function hideWebcamModal() {
    stopWebcam();
    if (webcamModal) {
      webcamModal.classList.remove('active');
      webcamModal.style.display = 'none';
    }
  }

  async function openLiveWebcam() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      if (camInput) camInput.click();
      return;
    }

    if (webcamModal) {
      webcamModal.classList.add('active');
      webcamModal.style.display = 'flex';
    }

    try {
      webcamStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      });
      if (webcamVideo) {
        webcamVideo.srcObject = webcamStream;
        webcamVideo.play();
      }
    } catch (err) {
      console.warn("[Historical Webcam Warning]:", err);
      stopWebcam();
      hideWebcamModal();
      const warnMsg = "कॅमेरा सुरू करता आला नाही किंवा परवानगी नाकारली आहे. कृपया फाइल निवडा.";
      if (typeof showToast === 'function') {
        showToast(warnMsg, 'warn', 4000);
      }
      if (camInput) camInput.click();
    }
  }

  if (closeWebcamModalBtn) closeWebcamModalBtn.addEventListener('click', hideWebcamModal);
  if (cancelWebcamBtn) cancelWebcamBtn.addEventListener('click', hideWebcamModal);
  if (webcamModal) {
    webcamModal.addEventListener('click', (e) => {
      if (e.target === webcamModal) hideWebcamModal();
    });
  }

  if (captureWebcamBtn && webcamVideo && webcamCanvas) {
    captureWebcamBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const vw = webcamVideo.videoWidth || 1280;
      const vh = webcamVideo.videoHeight || 720;
      webcamCanvas.width = vw;
      webcamCanvas.height = vh;
      const ctx = webcamCanvas.getContext('2d');
      ctx.drawImage(webcamVideo, 0, 0, vw, vh);

      hideWebcamModal();

      webcamCanvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], `receipt_${Date.now()}.jpg`, { type: 'image/jpeg' });
          processFiles([file]);
        }
      }, 'image/jpeg', 0.95);
    });
  }

  function closeModal() {
    hideWebcamModal();
    if (modal) {
      modal.classList.remove('active');
      modal.classList.remove('show');
      modal.style.display = 'none';
      document.body.classList.remove('modal-open');
      const backdrop = document.querySelector('.modal-backdrop');
      if (backdrop) backdrop.remove();
    }
  }

  function openModal() {
    if (modal) {
      modal.classList.add('active');
      modal.classList.add('show');
      modal.style.display = 'flex';
      if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split('T')[0];
      }
    }
  }

  if (openBtn) openBtn.onclick = openModal;
  if (closeBtn) closeBtn.onclick = closeModal;
  if (cancelBtn) cancelBtn.onclick = closeModal;

  // Handle bootstrap data-bs-dismiss attributes inside modal
  if (modal) {
    modal.querySelectorAll('[data-bs-dismiss="modal"]').forEach(btn => {
      btn.onclick = closeModal;
    });
  }

  // Preset Chips
  chips.forEach(chip => {
    chip.onclick = () => {
      const t = chip.getAttribute('data-title');
      if (titleInput && t) titleInput.value = t;
    };
  });

  // Triggers
  if (camBtn) {
    camBtn.onclick = (e) => {
      e.preventDefault();
      if (!isMobileDevice() && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        openLiveWebcam();
      } else if (camInput) {
        camInput.click();
      }
    };
  }
  if (galBtn && fileInput) {
    galBtn.onclick = () => fileInput.click();
  }
  if (addMoreBtn) {
    addMoreBtn.onclick = () => {
      if (!isMobileDevice() && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        openLiveWebcam();
      } else if (fileInput) {
        fileInput.click();
      } else if (camInput) {
        camInput.click();
      }
    };
  }

  // Thumbnail Rendering
  function renderThumbnails() {
    if (!previewContainer) return;

    if (uploadedImages.length === 0) {
      previewContainer.innerHTML = '';
      previewContainer.classList.add('d-none');
      previewContainer.style.display = 'none';
      if (addMoreBtn) {
        addMoreBtn.classList.add('d-none');
        addMoreBtn.style.display = 'none';
      }
      return;
    }

    previewContainer.classList.remove('d-none');
    previewContainer.style.display = 'flex';

    let html = '';
    uploadedImages.forEach((imgObj, idx) => {
      const pageLabel = `पान ${idx + 1}`;
      html += `
        <div class="position-relative d-inline-block text-center hist-thumb-card" data-img-id="${imgObj.id}" style="position:relative; width:80px; margin:4px; flex-shrink:0;">
          <img src="${imgObj.dataUrl}" alt="${pageLabel}" style="width:80px; height:80px; object-fit:cover; border-radius:6px; border:2px solid #CBD5E1; box-shadow:0 2px 4px rgba(0,0,0,0.1); display:block;">
          <span class="badge bg-dark" style="position:absolute; bottom:2px; left:50%; transform:translateX(-50%); font-size:0.7rem; padding:2px 6px; border-radius:4px; background:rgba(15,23,42,0.85); color:#fff; white-space:nowrap;">
            ${pageLabel}
          </span>
          <button type="button" class="btn-remove-thumb" data-id="${imgObj.id}" title="काढून टाका" style="position:absolute; top:-6px; right:-6px; width:22px; height:22px; border-radius:50%; background:#EF4444; color:#fff; border:2px solid #fff; font-size:12px; font-weight:bold; line-height:1; display:flex; align-items:center; justify-content:center; cursor:pointer; padding:0; box-shadow:0 2px 4px rgba(0,0,0,0.2);">
            ✕
          </button>
        </div>
      `;
    });

    previewContainer.innerHTML = html;

    // Attach remove handlers
    previewContainer.querySelectorAll('.btn-remove-thumb').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const idToRemove = btn.getAttribute('data-id');
        removeUploadedImage(idToRemove);
      };
    });

    // Update "+ आणखी एक फोटो जोडा" button
    if (addMoreBtn) {
      addMoreBtn.classList.remove('d-none');
      addMoreBtn.style.display = 'inline-flex';
      const nextPage = uploadedImages.length + 1;
      addMoreBtn.innerHTML = `<i class="bi bi-plus-circle"></i> + आणखी एक फोटो जोडा (पान ${nextPage})`;
    }
  }

  function updateTotalScannedCount(overrideCount = null) {
    const counterBadge = document.getElementById('totalScannedCount');
    if (!counterBadge) return;
    const count = (overrideCount !== null) ? overrideCount : (tbody ? tbody.querySelectorAll('tr').length : 0);
    const devDigits = typeof toDevanagariDigits === 'function' ? toDevanagariDigits(count) : count;
    counterBadge.innerText = `एकूण वस्तू: ${devDigits}`;
    counterBadge.setAttribute('data-count', count);
  }

  function removeUploadedImage(id) {
    uploadedImages = uploadedImages.filter(img => img.id !== id);
    renderThumbnails();

    if (uploadedImages.length === 0) {
      if (reviewArea) reviewArea.style.display = 'none';
      if (tbody) tbody.innerHTML = '';
      scannedItems = [];
      if (totalBadge) totalBadge.innerText = '₹0.00';
      updateTotalScannedCount(0);
    } else {
      recalculateScannedTotal();
    }
  }

  function recalculateScannedTotal() {
    let sum = 0.0;
    if (tbody) {
      tbody.querySelectorAll('.hist-row-price').forEach(inp => {
        const p = parseFloat(inp.value) || 0.0;
        sum += p;
      });
    }
    if (totalBadge) totalBadge.innerText = formatINR(sum);
    updateTotalScannedCount();
    return sum;
  }

  function renderReviewTable(items) {
    if (!reviewArea || !tbody) return;
    reviewArea.style.display = 'block';

    // 1. Frontend DOM Reset before inserting newly extracted items
    tbody.innerHTML = '';

    // 2. Programmatic Deduplication: unique commodity key filter before rendering
    const seen = new Set();
    const uniqueItems = items.filter(item => {
      const name = (item.item_name || item.name || item.commodity_name || '').trim().toLowerCase();
      if (!name) return false;
      if (seen.has(name)) return false;
      seen.add(name);
      return true;
    });

    // Update in-memory scannedItems
    scannedItems = uniqueItems;

    let html = '';
    uniqueItems.forEach((it, idx) => {
      const name = it.item_name || it.name || it.commodity_name || `वस्तू #${idx+1}`;
      const qty = it.quantity !== undefined && it.quantity !== null && it.quantity !== "" ? String(it.quantity) : (String(it.qty) || '1 किलो');
      const price = parseFloat(it.price || it.entered_total || it.target_price || it.billed_rate || 0.0) || 0.0;

      // Dynamic unit rate derivation across every single item without hardcoding
      const { unitRate, baseUnit } = calculateDynamicLineRate(price, qty);

      html += `
        <tr style="border-bottom:1px solid #E2E8F0;" data-item-idx="${idx}" id="hist-row-tr-${idx}">
          <td style="padding:6px 8px;">
            <input type="text" class="form-control form-control-sm hist-row-name" value="${escapeHtml(name)}" style="font-weight:600; font-size:0.85rem; width:100%; border:1px solid #CBD5E1; border-radius:4px; padding:4px 6px;" />
          </td>
          <td style="padding:6px 8px; text-align:center;">
            <input type="text" class="form-control form-control-sm item-qty-input hist-row-qty" value="${escapeHtml(String(qty))}" placeholder="उदा. 2 kg / 250 ग्रॅम" style="text-align:center; font-size:0.85rem; width:100%; border:1px solid #CBD5E1; border-radius:4px; padding:4px 6px;" />
            <input type="hidden" class="hist-row-unit" value="${escapeHtml(baseUnit)}" />
          </td>
          <td style="padding:6px 8px; text-align:right; white-space:nowrap;">
            <span class="badge bg-light text-dark border hist-row-unit-rate" data-unit-base-rate="${unitRate}" style="font-size:0.82rem; font-weight:700;">
              ₹${unitRate.toFixed(2)} / ${baseUnit}
            </span>
          </td>
          <td style="padding:6px 8px; text-align:right;">
            <input type="number" step="any" min="0" class="form-control form-control-sm hist-row-price" data-line-total-amount="${price.toFixed(2)}" value="${price.toFixed(2)}" style="text-align:right; font-weight:700; color:#0F766E; font-size:0.85rem; width:100%; border:1px solid #CBD5E1; border-radius:4px; padding:4px 6px;" />
          </td>
          <td style="padding:6px 4px; text-align:center;">
            <button type="button" class="btn btn-sm btn-link text-danger hist-row-delete" title="काढून टाका" style="padding:0; border:none; background:none; cursor:pointer; font-size:1rem;">🗑️</button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;

    function updateRowFinancials(row) {
      if (!row) return;
      const qtyInp = row.querySelector('.hist-row-qty');
      const priceInp = row.querySelector('.hist-row-price');
      const rateBadge = row.querySelector('.hist-row-unit-rate');
      const unitHidden = row.querySelector('.hist-row-unit');
      if (!qtyInp || !priceInp || !rateBadge) return;

      const qtyStr = qtyInp.value.trim() || '1 किलो';
      const totalPrice = parseFloat(priceInp.value) || 0.0;
      const { unitRate, baseUnit } = calculateDynamicLineRate(totalPrice, qtyStr);

      rateBadge.innerText = `₹${unitRate.toFixed(2)} / ${baseUnit}`;
      rateBadge.setAttribute('data-unit-base-rate', unitRate);
      priceInp.setAttribute('data-line-total-amount', totalPrice);
      if (unitHidden) unitHidden.value = baseUnit;
    }

    // Price and Quantity input change: dynamically recalculate unit rate and grand total across all rows
    tbody.querySelectorAll('tr').forEach(row => {
      const priceInp = row.querySelector('.hist-row-price');
      const qtyInp = row.querySelector('.hist-row-qty');
      if (priceInp) {
        priceInp.oninput = () => {
          updateRowFinancials(row);
          recalculateScannedTotal();
        };
      }
      if (qtyInp) {
        qtyInp.oninput = () => {
          updateRowFinancials(row);
          recalculateScannedTotal();
        };
      }
    });

    // Row delete
    tbody.querySelectorAll('.hist-row-delete').forEach(btn => {
      btn.onclick = () => {
        const row = btn.closest('tr');
        if (row) {
          row.remove();
          recalculateScannedTotal();
          updateTotalScannedCount();
        }
      };
    });

    recalculateScannedTotal();
    updateTotalScannedCount();
  }

  // -------------------------------------------------------------
  // DYNAMIC ZERO-HARDCODING QUANTITY & UNIT RATE ENGINE
  // -------------------------------------------------------------
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

  // -------------------------------------------------------------
  // Live Voice-Driven Correction Feature ("बोलून यादी दुरुस्त करा")
  // -------------------------------------------------------------
  const btnVoiceCorrection = document.getElementById('btnVoiceCorrection');
  const voiceStatus = document.getElementById('voiceStatus');

  function parseSpokenMarathiNumber(str) {
    if (!str) return null;
    let clean = str.trim();
    
    // 1. Convert Devanagari digits to Latin
    const devDigits = {'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'};
    for (const [d, a] of Object.entries(devDigits)) {
      clean = clean.split(d).join(a);
    }

    // 2. Direct regex match for numerals
    const numMatch = clean.match(/(\d+(?:\.\d+)?)/);
    if (numMatch) {
      return parseFloat(numMatch[1]);
    }

    // 3. Marathi number word dictionary & compound parser
    const marathiWords = {
      'शून्य': 0, 'एक': 1, 'दोन': 2, 'तीन': 3, 'चार': 4, 'पाच': 5, 'सहा': 6, 'सात': 7, 'आठ': 8, 'नऊ': 9, 'दहा': 10,
      'अकरा': 11, 'बारा': 12, 'तेरा': 13, 'चौदा': 14, 'पंधरा': 15, 'सोळा': 16, 'सतरा': 17, 'अठरा': 18, 'एकोणीस': 19,
      'वीस': 20, 'एकवीस': 21, 'बावीस': 22, 'तेवीस': 23, 'चोवीस': 24, 'पंचवीस': 25, 'सव्वीस': 26, 'सत्तावीस': 27, 'अठ्ठावीस': 28, 'एकोणतीस': 29,
      'तीस': 30, 'एकतीस': 31, 'बत्तीस': 32, 'तेहतीस': 33, 'चौतीस': 34, 'पस्तीस': 35, 'छत्तीस': 36, 'सदतीस': 37, 'अडतीस': 38, 'एकेचाळीस': 41,
      'चाळीस': 40, 'बेचाळीस': 42, 'त्रेचाळीस': 43, 'चव्वेचाळीस': 44, 'पंचेचाळीस': 45, 'शेहेचाळीस': 46, 'सत्तेचाळीस': 47, 'अठ्ठेचाळीस': 48, 'एकोणपन्नास': 49,
      'पन्नास': 50, 'एक्कावन्न': 51, 'बावन्न': 52, 'त्रेपन्न': 53, 'चौपन्न': 54, 'पंचावन्न': 55, 'छप्पन्न': 56, 'सत्तावन्न': 57, 'अठ्ठावन्न': 58, 'एकोणसाठ': 59,
      'साठ': 60, 'एकसष्ठ': 61, 'बासष्ठ': 62, 'त्रेसष्ठ': 63, 'चौसष्ठ': 64, 'पासष्ठ': 65, 'सहासष्ठ': 66, 'सदुसष्ठ': 67, 'अडुसष्ठ': 68, 'एकोणसत्तर': 69,
      'सत्तर': 70, 'एकाहत्तर': 71, 'बाहत्तर': 72, 'त्र्याहत्तर': 73, 'चौर्‍याहत्तर': 74, 'पंचाहत्तर': 75, 'शहात्तर': 76, 'सत्याहत्तर': 77, 'अठ्ठ्याहत्तर': 78, 'एकोणऐंशी': 79,
      'ऐंशी': 80, 'एक्यांशी': 81, 'ब्यांशी': 82, 'त्र्यांशी': 83, 'चौऱ्यांशी': 84, 'पंच्यांशी': 85, 'शहांशी': 86, 'सत्त्यांशी': 87, 'अठ्ठ्यांशी': 88, 'एकोणनव्वद': 89,
      'नव्वद': 90, 'एक्याण्णव': 91, 'ब्याण्णव': 92, 'त्र्याण्णव': 93, 'चौऱ्याण्णव': 94, 'पंच्याण्णव': 95, 'शहाण्णव': 96, 'सत्त्याण्णव': 97, 'अठ्ठाण्णव': 98, 'नव्व्याण्णव': 99,
      'शंभर': 100, 'एकशे': 100, 'दीडशे': 150, 'दोनशे': 200, 'अडीचशे': 250, 'तीनशे': 300, 'चारशे': 400, 'पाचशे': 500,
      'सहाशे': 600, 'सातशे': 700, 'आठशे': 800, 'नऊशे': 900, 'हजार': 1000
    };

    const words = clean.split(/\s+/);
    let total = 0;
    let currentGroup = 0;
    let matchedAny = false;

    for (let i = 0; i < words.length; i++) {
      const w = words[i].replace(/[.,]/g, '');
      if (w === 'हजार') {
        currentGroup = (currentGroup === 0 ? 1 : currentGroup) * 1000;
        total += currentGroup;
        currentGroup = 0;
        matchedAny = true;
      } else if (w.endsWith('शे') && marathiWords[w]) {
        currentGroup += marathiWords[w];
        matchedAny = true;
      } else if (marathiWords[w] !== undefined) {
        currentGroup += marathiWords[w];
        matchedAny = true;
      }
    }
    total += currentGroup;
    return matchedAny ? total : null;
  }

  function flashElement(el) {
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    const originalBg = el.style.backgroundColor;
    const originalBorder = el.style.borderColor;
    const originalTransition = el.style.transition;
    
    el.style.transition = 'all 0.3s ease';
    el.style.backgroundColor = '#DCFCE7'; // Light green
    el.style.borderColor = '#16A34A';     // Green border
    el.style.boxShadow = '0 0 10px rgba(34, 197, 94, 0.7)';

    setTimeout(() => {
      el.style.backgroundColor = originalBg || '';
      el.style.borderColor = originalBorder || '';
      el.style.boxShadow = '';
      el.style.transition = originalTransition || '';
    }, 1800);
  }

  function speakMarathiFeedback(text) {
    if (!window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'mr-IN';
      utterance.rate = 1.0;
      const voices = window.speechSynthesis.getVoices();
      const mrVoice = voices.find(v => v.lang.includes('mr') || v.lang.includes('hi'));
      if (mrVoice) {
        utterance.voice = mrVoice;
      }
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("Speech synthesis error:", e);
    }
  }

  function processVoiceCorrection(phrase) {
    if (!phrase || !phrase.trim()) return;
    const raw = phrase.trim();
    console.log("[Voice Correction Heard]:", raw);

    let cleanPhrase = raw.replace(/\b(करा|करून टाका|कर|ठेवा|द्या|बदला)\b/g, '').trim();

    let targetField = 'price';
    const isQty = /(?:प्रमाण|वजन|किलो|ग्रॅम|ग्राम|gm|kg|लिटर|पाकीट|नग|तोळा|डबा|डबी|बाटली)/i.test(cleanPhrase) && !/(?:रुपये|रु|भाव|दर|किंमत)/i.test(cleanPhrase);
    if (isQty) {
      targetField = 'qty';
    }

    const rows = tbody ? Array.from(tbody.querySelectorAll('tr')) : [];
    if (rows.length === 0) {
      showToast("⚠️ यादीमध्ये सध्या कोणतीही वस्तू उपलब्ध नाही.", "warn");
      return;
    }

    let bestRow = null;
    let bestScore = 0;
    let matchedName = "";

    rows.forEach(row => {
      const nameInput = row.querySelector('.hist-row-name');
      if (!nameInput) return;
      const rowName = nameInput.value.trim().toLowerCase();
      if (!rowName) return;

      const rowBase = rowName.replace(/\[.*?\]|\(.*?\)/g, '').trim();
      const rowTokens = rowBase.split(/\s+/).filter(t => t.length > 1);

      let matchCount = 0;
      rowTokens.forEach(tok => {
        if (cleanPhrase.toLowerCase().includes(tok)) {
          matchCount++;
        }
      });

      let score = 0;
      if (cleanPhrase.toLowerCase().includes(rowBase)) {
        score = 2.0;
      } else if (matchCount > 0) {
        score = matchCount / rowTokens.length;
      }

      if (score > bestScore) {
        bestScore = score;
        bestRow = row;
        matchedName = nameInput.value.trim();
      }
    });

    if (!bestRow || bestScore < 0.3) {
      showToast(`⚠️ बोललेली वस्तू यादीमध्ये सापडली नाही: "${raw}"`, "warn");
      speakMarathiFeedback("वस्तू सापडली नाही");
      return;
    }

    if (targetField === 'price') {
      const newPrice = parseSpokenMarathiNumber(cleanPhrase);
      if (newPrice === null || isNaN(newPrice)) {
        showToast(`⚠️ दर समजला नाही: "${raw}"`, "warn");
        speakMarathiFeedback("दर समजला नाही");
        return;
      }

      const priceInput = bestRow.querySelector('.hist-row-price');
      if (priceInput) {
        priceInput.value = newPrice;
        flashElement(priceInput);
        recalculateScannedTotal();

        const msg = `${matchedName} दर अपडेट केला: ₹${newPrice}`;
        showToast(`✅ ${msg}`, "success");
        speakMarathiFeedback(`${matchedName} दर अपडेट केला: ${newPrice} रुपये`);
      }
    } else {
      let qtyStr = "";
      const qtyMatch = cleanPhrase.match(/([०-९\d]+(?:\.[०-९\d]+)?\s*(?:किलो|ग्रॅम|ग्राम|gm|kg|लिटर|पाकीट|नग|तोळा|डबा|डबी|बाटली|ली)|अर्धा\s*किलो|पाव\s*किलो|पाऊण\s*किलो|दीड\s*किलो)/i);
      if (qtyMatch) {
        qtyStr = qtyMatch[0];
      } else {
        const num = parseSpokenMarathiNumber(cleanPhrase);
        if (num !== null) {
          qtyStr = `${num} किलो`;
        }
      }

      if (!qtyStr) {
        showToast(`⚠️ प्रमाण समजले नाही: "${raw}"`, "warn");
        return;
      }

      const qtyInput = bestRow.querySelector('.hist-row-qty');
      if (qtyInput) {
        qtyInput.value = qtyStr;
        flashElement(qtyInput);
        const msg = `${matchedName} प्रमाण अपडेट केले: ${qtyStr}`;
        showToast(`✅ ${msg}`, "success");
        speakMarathiFeedback(`${matchedName} प्रमाण अपडेट केले`);
      }
    }
  }

  // Setup Web Speech Recognition
  if (btnVoiceCorrection) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      btnVoiceCorrection.addEventListener('click', () => {
        showToast("⚠️ आपल्या ब्राउझरमध्ये व्हॉईस रेकग्निशन उपलब्ध नाही. कृपया Google Chrome किंवा Microsoft Edge वापरा.", "warn");
      });
    } else {
      const recognition = new SpeechRecognition();
      recognition.lang = 'mr-IN';
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      let isVoiceListening = false;

      recognition.onstart = () => {
        isVoiceListening = true;
        if (voiceStatus) {
          voiceStatus.className = "badge bg-danger ms-2";
          voiceStatus.innerHTML = "🔴 ऐकत आहे...";
        }
        btnVoiceCorrection.classList.add('btn-danger');
        btnVoiceCorrection.classList.remove('btn-outline-primary');
      };

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        processVoiceCorrection(transcript);
      };

      recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        if (voiceStatus) {
          voiceStatus.className = "badge bg-warning text-dark ms-2";
          voiceStatus.textContent = event.error === 'no-speech' ? "आवाज आला नाही" : "माईक त्रुटी";
        }
      };

      recognition.onend = () => {
        isVoiceListening = false;
        setTimeout(() => {
          if (!isVoiceListening && voiceStatus) {
            voiceStatus.className = "badge bg-secondary ms-2";
            voiceStatus.textContent = "माईक बंद";
          }
          if (btnVoiceCorrection) {
            btnVoiceCorrection.classList.remove('btn-danger');
            btnVoiceCorrection.classList.add('btn-outline-primary');
          }
        }, 1200);
      };

      btnVoiceCorrection.addEventListener('click', (e) => {
        e.preventDefault();
        if (isVoiceListening) {
          recognition.stop();
        } else {
          try {
            recognition.start();
          } catch (err) {
            console.warn("Recognition start error:", err);
          }
        }
      });
    }
  }

  // Handle OCR scan for newly added files
  async function processFiles(files) {
    if (!files || files.length === 0) return;

    if (loader) {
      loader.classList.remove('d-none');
      loader.classList.add('active');
      loader.style.display = 'flex';
    }

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // 1. Read file as DataURL for thumbnail preview
        const dataUrl = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => resolve(e.target.result);
          reader.onerror = (e) => reject(e);
          reader.readAsDataURL(file);
        });

        const imageId = 'img_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
        uploadedImages.push({
          id: imageId,
          file: file,
          dataUrl: dataUrl
        });

        // 2. Perform OCR scan
        const formData = new FormData();
        formData.append('image', file);

        const resp = await fetch('/api/scan-grocery-image', {
          method: 'POST',
          body: formData
        });
        const data = await resp.json();

        if (data.success && Array.isArray(data.items) && data.items.length > 0) {
          // Merge sequentially into scannedItems without dropping items
          data.items.forEach(it => {
            scannedItems.push(it);
          });
        }
      }

      // Programmatic Deduplication: enforce unique commodity key filter before rendering
      const seen = new Set();
      const uniqueItems = [];
      scannedItems.forEach(item => {
        const rawName = item.item_name || item.name || item.commodity_name || '';
        const key = rawName.trim().toLowerCase();
        if (key && !seen.has(key)) {
          seen.add(key);
          uniqueItems.push(item);
        }
      });
      scannedItems = uniqueItems;

      // Render updated thumbnails and combined review table
      renderThumbnails();

      if (scannedItems.length > 0) {
        renderReviewTable(scannedItems);
        updateTotalScannedCount();
        showToast(`✅ ${uploadedImages.length} पानांमधून एकूण ${scannedItems.length} वस्तू यशस्वीरित्या स्कॅन झाल्या.`, "success");
      } else {
        showToast("⚠️ पावतीतील वस्तू वाचता आल्या नाहीत, कृपया स्पष्ट फोटो अपलोड करा.", "error");
      }
    } catch (err) {
      console.error("[Historical Bill Scan Error]:", err);
      showToast("स्कॅनिंग करताना अडचण आली: " + err.message, "error");
    } finally {
      if (loader) {
        loader.classList.add('d-none');
        loader.classList.remove('active');
        loader.style.display = 'none';
      }
      if (fileInput) fileInput.value = '';
      if (camInput) camInput.value = '';
    }
  }

  // File Input Change Handlers
  if (fileInput) {
    fileInput.onchange = (e) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) processFiles(files);
    };
  }

  if (camInput) {
    camInput.onchange = (e) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) processFiles(files);
    };
  }

  // Save to History Handler
  if (saveBtn) {
    saveBtn.onclick = async () => {
      if (!tbody) return;
      const rows = tbody.querySelectorAll('tr');
      const itemsToSave = [];
      let grandTotal = 0.0;

      rows.forEach(r => {
        const nameInp = r.querySelector('.hist-row-name');
        const qtyInp = r.querySelector('.item-qty-input') || r.querySelector('.hist-row-qty');
        const unitInp = r.querySelector('.hist-row-unit');
        const priceInp = r.querySelector('.hist-row-price');

        const name = nameInp ? nameInp.value.trim() : '';
        const qtyStr = qtyInp ? qtyInp.value.trim() : '1 किलो';
        const lineTotal = priceInp ? (parseFloat(priceInp.value) || 0.0) : 0.0;
        
        // Zero-hardcoding dynamic mathematical derivation across every row
        const { unitRate, normalizedQty, baseUnit } = calculateDynamicLineRate(lineTotal, qtyStr);

        if (name) {
          itemsToSave.push({
            name: name,
            commodity_name: name,
            quantity: qtyStr,              // Preserved original string with written units
            qty: qtyStr,
            quantity_norm: normalizedQty,  // Scaled numerical magnitude (e.g. 0.25 for 250 gm)
            normalized_quantity: normalizedQty,
            unit: baseUnit,                // Canonical base unit ('किलो', 'ली', 'पाकीट')
            display_unit: baseUnit,
            unit_base_rate: unitRate,      // Strictly normalized unit base rate = lineTotal / normalizedQty
            derived_rate: unitRate,
            billed_rate: unitRate,
            line_total_amount: lineTotal,  // Exact currency sum billed for the item
            entered_total: lineTotal,
            target_price: unitRate,
            price: lineTotal
          });
          grandTotal += lineTotal;
        }
      });

      if (itemsToSave.length === 0) {
        showToast("कमीत कमी एक वस्तू आवश्यक आहे.", "warn");
        return;
      }

      const title = (titleInput && titleInput.value.trim()) || "मागील किराणा पावती";
      const purchaseDate = (dateInput && dateInput.value) || new Date().toISOString().split('T')[0];

      try {
        if (saveBtn) {
          saveBtn.disabled = true;
          saveBtn.innerHTML = `⏳ जतन करत आहे...`;
        }

        // Direct persistence to /api/save-historical-bill (writes to GroceryTrip, TripItem, and SavedGroceryList)
        const billPayload = {
          session_id: "hist-scan-" + Date.now(),
          title: title,
          occasion_type: "regular",
          purchase_date: purchaseDate,
          merchant_name: "किराणा पावती",
          settled_total: grandTotal,
          items: itemsToSave
        };

        const resp = await fetch('/api/save-historical-bill', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(billPayload)
        });

        const resData = await resp.json();

        if (resp.ok && resData.success) {
          showToast(`✅ "${title}" इतिहासामध्ये यशस्वीरित्या जतन झाली! आता सिम्युलेटरकडे रिअल बेसलाईन उपलब्ध आहे.`, 'success', 4500);
          closeModal();
          
          // Reset modal state
          uploadedImages = [];
          scannedItems = [];
          renderThumbnails();
          if (reviewArea) reviewArea.style.display = 'none';
          if (tbody) tbody.innerHTML = '';
          if (totalBadge) totalBadge.innerText = '₹0.00';

          // Immediately refresh simulator and recalculate with new baseline
          await loadCatalogForSimulator();
          await recalculateSimulation();
          if (typeof loadPersonalInflationIndex === 'function') {
            loadPersonalInflationIndex();
          }
        } else {
          throw new Error(resData.detail || resData.message || "इतिहास साठवण्यात अडचण आली.");
        }
      } catch (err) {
        console.error("Save historical bill error:", err);
        showToast("जतन करताना त्रुटी: " + err.message, "error");
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `💾 इतिहासात सेव्ह करा (Save to History)`;
        }
      }
    };
  }
}

window.loadPriceTrends = loadPriceTrends;
window.removeSimulatorRow = removeSimulatorRow;
