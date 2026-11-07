/**
 * Smart Kirana Enterprise - Page 1 Controller (index.html)
 * AI Batch Ingestion, Reverse POS Math, Volatility Auditing, WebRTC UPI Settlement
 */

let state = {
  sessionId: crypto.randomUUID ? crypto.randomUUID() : 'sess-' + Date.now(),
  items: [],
  grandTotal: 0.0,
  basketVariance: 0.0,
  basketStatus: "संतुलित बजेट",
  merchantVpa: "patil.kirana@upi",
  merchantName: "पाटील किराणा स्टोअर्स",
  scannerInstance: null
};

document.addEventListener('DOMContentLoaded', () => {
  const safeInit = (name, fn) => {
    try {
      fn();
    } catch (e) {
      console.error(`[Home Init Error in ${name}]:`, e);
    }
  };

  safeInit('SampleLoader', initSampleLoader);
  safeInit('IngestionForm', initIngestionForm);
  safeInit('PathwaySwitcher', initPathwaySwitcher);
  safeInit('VerificationModal', initVerificationModal);
  safeInit('DraftsManager', initDraftsManager);
  safeInit('DuplicatePromptModal', initDuplicatePromptModal);
  safeInit('FestivalSurgeBanner', initFestivalSurgeBanner);
  safeInit('Scanner', initScanner);
  safeInit('CommitButton', initCommitButton);
  safeInit('AutoRestoreDraft', checkAutoRestoreDraft);
});

// Sample Lists for instant one-click testing
const SAMPLE_LISTS = {
  sample1: `साखर२किलो\nshengdanatel2L\nतुरीची डाल 1kg\nतांदूळ 500 gm\nसक्कर 2 kg`,
  sample2: `जिरे - 100 gm\nचहा पावडर - 250 gm\nसाखर - 5 kg\nशेंगदाणा तेल - 2 L`,
  sample3: `चहा पावडर अर्धा किलो\nहळद पाव किलो\nmitha 10rupees\nसाबण ४ नग`
};

function initSampleLoader() {
  const sampleBtns = document.querySelectorAll('.sample-btn');
  const textarea = document.getElementById('raw-list-input');
  
  sampleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const sampleKey = btn.dataset.sample;
      if (textarea && SAMPLE_LISTS[sampleKey]) {
        textarea.value = SAMPLE_LISTS[sampleKey];
        showToast("नमुना किराणा यादी भरली आहे.", "info");
      }
    });
  });
}

// Global verification state
let verificationOriginalCount = 0;

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Helper to convert ASCII digits to Devanagari numerals
function toDevanagariDigits(val) {
  if (val === null || val === undefined) return '';
  const devDigits = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'];
  return String(val).replace(/[0-9]/g, d => devDigits[d]);
}

/**
 * ==============================================================================
 * MODULE 1: ZERO-LOSS LARGE-SCALE UNSTRUCTURED PARSING (BATCH CHUNKING ENGINE)
 * ==============================================================================
 */
function initIngestionForm() {
  const form = document.getElementById('list-ingestion-form');
  const textarea = document.getElementById('raw-list-input');
  const submitBtn = document.getElementById('parse-list-btn');
  const alertBox = document.getElementById('pipeline-alert');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const rawText = textarea.value.trim();
    if (!rawText) {
      showToast("कृपया आधी किराणा यादी टाईप करा किंवा पेस्ट करा.", "error");
      return;
    }

    // Intelligent Text Normalization & Pre-splitting: commas, newlines, semicolons, आणि, तसेच
    const rawItems = window.splitRawGroceryInput
      ? window.splitRawGroceryInput(rawText)
      : rawText.split(/(?:\r?\n|[,;]|\s+(?:आणि|तसेच)\s+)/gi).map(t => t.trim()).filter(t => t.length > 0);

    const totalInputCount = rawItems.length;
    if (totalInputCount === 0) {
      showToast("कृपया आधी किराणा यादी टाईप करा किंवा पेस्ट करा.", "error");
      return;
    }

    if (alertBox) {
      alertBox.style.display = 'none';
      alertBox.className = 'pipeline-alert';
    }

    // Explicit Offline State: immediately route to deterministic local parser & open verification dialog
    if (!navigator.onLine) {
      if (window.parseListLocally) {
        let localItems = window.parseListLocally(rawText);
        if (window.deduplicateParsedItems) {
          localItems = window.deduplicateParsedItems(localItems, false);
        }
        if (alertBox) {
          alertBox.style.display = 'flex';
          alertBox.className = 'pipeline-alert pipeline-alert-warn';
          alertBox.innerHTML = `⚠️ आपण ऑफलाइन आहात. स्थानिक पार्सर वापरून ${localItems.length} वस्तू शोधल्या.`;
        }
        openVerificationModal(localItems, localItems.length, true);
        showToast(`स्थानिक पार्सरने ${localItems.length} वस्तूंची पडताळणी यादी तयार केली.`, "warn");
        return;
      }
    }

    // UI Loading & Skeleton Processing State
    const emptyState = document.getElementById('grid-empty-state');
    const tableWrap = document.getElementById('grid-table-wrap');
    const skeletonWrap = document.getElementById('grid-loading-skeleton');
    const stickyFooter = document.getElementById('sticky-billing-footer');
    const procTitle = document.getElementById('processing-title');
    const procSubtitle = document.getElementById('processing-subtitle');
    const procFill = document.getElementById('processing-progress-fill');

    // Disable button to prevent double-submits
    submitBtn.disabled = true;
    submitBtn.classList.add('btn-loading');
    submitBtn.innerHTML = `
      <span class="btn-spinner" aria-hidden="true"></span>
      <span>यादी तपासली जात आहे...</span>
    `;

    // Zero-CLS: Show shimmer skeleton while processing
    if (emptyState) emptyState.style.display = 'none';
    if (tableWrap) tableWrap.style.display = 'none';
    if (stickyFooter) stickyFooter.style.display = 'none';
    if (skeletonWrap) skeletonWrap.style.display = 'flex';

    if (procTitle) procTitle.innerText = "⚡ स्थानिक जलद विश्लेषण (०-सेकंद फास्ट पास)...";
    if (procSubtitle) procSubtitle.innerText = `यादी तपासली जात आहे... ० पैकी ${toDevanagariDigits(totalInputCount)} वस्तू (२०%)`;
    if (procFill) procFill.style.width = '20%';

    showToast(`⚡ ${totalInputCount} वस्तूंचे हायब्रीड विश्लेषण सुरू आहे...`, "info", 3000);

    // Live progress animation timers
    const timer1 = setTimeout(() => {
      if (procTitle) procTitle.innerText = "🤖 जटिल व ब्रँडेड वस्तूंचे सह-प्रक्रियाकरण (Gemini AI)...";
      if (procSubtitle) procSubtitle.innerText = `अचूक तपासणी सुरू आहे... (६०%)`;
      if (procFill) procFill.style.width = '60%';
    }, 450);

    const timer2 = setTimeout(() => {
      if (procTitle) procTitle.innerText = "🔄 यादी जुळवणी आणि दुबार नोंदींचे शुद्धीकरण...";
      if (procSubtitle) procSubtitle.innerText = `अंतिम जुळवणी सुरू आहे... (८५%)`;
      if (procFill) procFill.style.width = '85%';
    }, 1600);

    // High-Speed Symbiotic Pipeline with 4500ms timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4500);

    let finalParsedItems = [];
    let isFallbackOccurred = false;
    let fallbackNotice = null;

    try {
      let rawServerItems = [];

      if (totalInputCount > 25) {
        // MODULE 1: Batch-chunked concurrent parsing using Promise.all() for >25 items
        const CHUNK_SZ = 25;
        const chunkPromises = [];
        for (let i = 0; i < totalInputCount; i += CHUNK_SZ) {
          const chunkLines = rawItems.slice(i, i + CHUNK_SZ);
          const chunkStart = i;
          chunkPromises.push(
            fetch('/api/v1/lists/parse', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                session_id: `${state.sessionId}-c${chunkStart}`,
                raw_items: chunkLines,
                raw_text: chunkLines.join('\n'),
                mode: 'auto'
              }),
              signal: controller.signal
            }).then(r => r.json()).then(resData => ({ chunkStart, resData }))
          );
        }

        const chunkResponses = await Promise.all(chunkPromises);
        // Sort by chunkStart to preserve exact input sequence
        chunkResponses.sort((a, b) => a.chunkStart - b.chunkStart);

        chunkResponses.forEach(({ chunkStart, resData }) => {
          if (resData.items && Array.isArray(resData.items)) {
            resData.items.forEach((itm, localI) => {
              itm.line_index = chunkStart + localI;
              rawServerItems.push(itm);
            });
          }
          if (resData.ai_fallback) {
            isFallbackOccurred = true;
            fallbackNotice = resData.fallback_notice_mr;
          }
        });

      } else {
        const resp = await fetch('/api/v1/lists/parse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: state.sessionId,
            raw_items: rawItems,
            raw_text: rawItems.join('\n'),
            mode: 'auto'
          }),
          signal: controller.signal
        });

        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "यादी तपासण्यात अडचण आली.");
        }
        rawServerItems = data.items || [];
        
        // MODULE 1: Unmask Gemini AI parse status
        if (data.ai_active === true) {
          isFallbackOccurred = false;
          fallbackNotice = null;
        } else if (data.ai_fallback) {
          isFallbackOccurred = true;
          fallbackNotice = data.fallback_notice_mr;
        }

        if (data.merged_duplicates && data.merged_duplicates.length > 0) {
          showToast("एकसारख्या दुबार वस्तू काढून यादी शुद्ध केली.", "info");
        }
      }

      clearTimeout(timeoutId);
      clearTimeout(timer1);
      clearTimeout(timer2);

      if (procTitle) procTitle.innerText = "✓ यादी यशस्वीरीत्या शुद्ध झाली!";
      if (procSubtitle) procSubtitle.innerText = `सर्व वस्तू तपासल्या आहेत (१००%)`;
      if (procFill) procFill.style.width = '100%';
      // Deduplicate items on client side as well for strict deduplication
      finalParsedItems = window.deduplicateParsedItems
        ? window.deduplicateParsedItems(rawServerItems, false)
        : rawServerItems;

      // Render Alert notice (Unconditionally suppressed when AI is active)
      if (alertBox) {
        if (isFallbackOccurred && fallbackNotice) {
          alertBox.style.display = 'flex';
          alertBox.className = 'pipeline-alert pipeline-alert-warn';
          alertBox.innerHTML = `⚠️ ${fallbackNotice}`;
        } else {
          alertBox.style.display = 'none';
        }
      }

      // Open Intermediate Verification & Edit Modal with unique deduplicated count
      openVerificationModal(finalParsedItems, finalParsedItems.length, isFallbackOccurred);
      showToast(`एकूण ${finalParsedItems.length} वस्तूंची पडताळणी यादी तयार झाली.`, "success");

    } catch (err) {
      clearTimeout(timeoutId);
      clearTimeout(timer1);
      clearTimeout(timer2);
      console.warn("[Symbiotic Pipeline Client Fallback] Fetch failed or timed out:", err);

      if (window.parseListLocally) {
        let localItems = window.parseListLocally(rawText);
        if (window.deduplicateParsedItems) {
          localItems = window.deduplicateParsedItems(localItems, false);
        }
        if (localItems.length > 0) {
          if (alertBox) {
            alertBox.style.display = 'flex';
            alertBox.className = 'pipeline-alert pipeline-alert-warn';
            alertBox.innerHTML = `⚠️ सर्व्हर प्रतिसाद वेळेत आला नाही, स्थानिक पार्सरने यादी तयार केली.`;
          }
          openVerificationModal(localItems, localItems.length, true);
          showToast(`स्थानिक पार्सरने ${localItems.length} वस्तूंची पडताळणी यादी तयार केली.`, "warn");
          return;
        }
      }
      showToast(err.message || "यादी प्रोसेस करताना अडचण आली.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.classList.remove('btn-loading');
      submitBtn.innerHTML = `✨ यादी शुद्ध करा व काउंटरवर पाठवा`;
      if (skeletonWrap) {
        skeletonWrap.style.display = 'none';
      }
      if (state.items.length === 0 && emptyState) {
        emptyState.style.display = 'block';
      }
    }
  });
}

/**
 * ==============================================================================
 * MODULE 2: INTERMEDIATE VERIFICATION & EDIT MODAL ("पडताळणी व संपादन")
 * ==============================================================================
 */
function initVerificationModal() {
  const modal = document.getElementById('verification-modal');
  const closeBtn = document.getElementById('close-verification-modal');
  const cancelBtn = document.getElementById('v-cancel-btn');
  const addRowBtn = document.getElementById('v-add-row-btn');
  const addRowTopBtn = document.getElementById('v-add-row-top-btn');
  const confirmBtn = document.getElementById('v-confirm-btn');
  const saveDraftBtn = document.getElementById('v-save-draft-btn');

  function closeModal() {
    if (modal) modal.classList.remove('active');
    showToast("पडताळणी रद्द केली. आपण मूळ यादीत बदल करू शकता.", "info");
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', closeModal);
    closeBtn.addEventListener('touchend', (e) => { e.preventDefault(); closeModal(); });
  }
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('touchend', (e) => { e.preventDefault(); closeModal(); });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }

  // Add row at bottom
  if (addRowBtn) {
    const handleAddBottom = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      addVerificationRow(null, false);
    };
    addRowBtn.addEventListener('click', handleAddBottom);
    addRowBtn.addEventListener('touchend', handleAddBottom);
  }

  // MODULE 4: Fixed Action to immediately insert a blank editable input row at Row 0 (top) without scrolling
  if (addRowTopBtn) {
    const handleAddTop = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      addVerificationRow(null, true);
    };
    addRowTopBtn.addEventListener('click', handleAddTop);
    addRowTopBtn.addEventListener('touchend', handleAddTop);
  }

  if (confirmBtn) {
    const handleConfirm = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      confirmAndSendToCounter();
    };
    confirmBtn.addEventListener('click', handleConfirm);
    confirmBtn.addEventListener('touchend', handleConfirm);
  }

  if (saveDraftBtn) {
    const handleSave = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      saveDraftFromVerificationModal();
    };
    saveDraftBtn.addEventListener('click', handleSave);
    saveDraftBtn.addEventListener('touchend', handleSave);
  }
}

function updateVerificationCounts() {
  const rows = document.querySelectorAll('#v-table-body tr');
  const currentCount = rows.length;

  const titleCountEl = document.getElementById('v-title-count');
  if (titleCountEl) {
    titleCountEl.innerText = toDevanagariDigits(currentCount);
  }

  // MODULE 4: Sticky Reconciliation Badge (visual parity indicator)
  const reconTextEl = document.getElementById('v-reconciliation-text');
  if (reconTextEl) {
    reconTextEl.innerText = `एकूण इनपुट ओळी: ${toDevanagariDigits(verificationOriginalCount)} | फॉर्ममधील वस्तू: ${toDevanagariDigits(currentCount)}`;
  }

  const badgeEl = document.getElementById('v-verification-badge');
  if (badgeEl) {
    const isExact = (currentCount === verificationOriginalCount && currentCount > 0);
    const cls = isExact ? 'v-badge-success' : 'v-badge-warn';
    badgeEl.innerHTML = `<span class="v-badge ${cls}">एकूण वस्तू: ${toDevanagariDigits(currentCount)}/${toDevanagariDigits(verificationOriginalCount)}</span>`;
  }

  const noteEl = document.getElementById('v-count-status-note');
  if (noteEl) {
    noteEl.innerText = `एकूण वस्तू: ${toDevanagariDigits(currentCount)}/${toDevanagariDigits(verificationOriginalCount)}`;
  }

  // Update Sr. Nos.
  rows.forEach((row, i) => {
    const srCell = row.querySelector('.v-td-sr');
    if (srCell) srCell.innerText = toDevanagariDigits(i + 1);
  });
}

function addVerificationRow(itemData = null, insertAtTop = false) {
  const tableBody = document.getElementById('v-table-body');
  if (!tableBody) return;

  const currentCount = tableBody.children.length;
  const tr = document.createElement('tr');
  tr.id = `v-row-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
  tr._originalItemData = itemData || {};

  const nameVal = itemData ? (itemData.name || itemData.original_raw || '') : '';
  const qtyVal = itemData ? ((itemData.display_qty !== undefined && itemData.display_qty !== null) ? itemData.display_qty : (itemData.qty || 1)) : 1;
  const rawUnit = itemData ? (itemData.display_unit || itemData.unit || 'किलो') : 'किलो';
  let matchedUnit = 'किलो';
  if (/ग्रॅम|gm|g/i.test(rawUnit)) matchedUnit = 'ग्रॅम';
  else if (/लिटर|L|l/i.test(rawUnit)) matchedUnit = 'लिटर';
  else if (/पाकीट|packet/i.test(rawUnit)) matchedUnit = 'पाकीट';
  else if (/नग|pcs/i.test(rawUnit)) matchedUnit = 'नग';
  else matchedUnit = 'किलो';

  const priceVal = (itemData && itemData.target_price && itemData.target_price > 0)
    ? parseFloat(itemData.target_price).toFixed(2)
    : ((itemData && itemData.estimated_price && itemData.estimated_price > 0) ? parseFloat(itemData.estimated_price).toFixed(2) : '');

  tr.innerHTML = `
    <td class="v-td-sr">${toDevanagariDigits(currentCount + 1)}</td>
    <td>
      <input type="text" class="v-input v-item-name" value="${escapeHtml(nameVal)}" placeholder="उदा. अगरबत्ती [विलास], गोडतेल [फॉर्च्यून]" />
    </td>
    <td>
      <input type="number" step="0.1" min="0.01" class="v-input v-item-qty" value="${qtyVal}" />
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
      <button type="button" class="v-delete-btn" title="वस्तू हटवा" aria-label="वस्तू हटवा" style="background:transparent;border:none;cursor:pointer;font-size:1.1rem;color:#DC2626;">🗑️</button>
    </td>
  `;

  // Attach delete row listener
  const delBtn = tr.querySelector('.v-delete-btn');
  if (delBtn) {
    delBtn.addEventListener('click', () => {
      tr.remove();
      updateVerificationCounts();
    });
  }

  // MODULE 4: Insert at Row 0 if insertAtTop is true, otherwise append
  if (insertAtTop && tableBody.firstChild) {
    tableBody.insertBefore(tr, tableBody.firstChild);
  } else {
    tableBody.appendChild(tr);
  }
  updateVerificationCounts();

  if (!itemData) {
    const nameInp = tr.querySelector('.v-item-name');
    if (nameInp) nameInp.focus();
    const wrapper = document.getElementById('v-table-wrapper');
    if (wrapper) {
      if (insertAtTop) {
        wrapper.scrollTop = 0;
      } else {
        wrapper.scrollTop = wrapper.scrollHeight;
      }
    }
  }
}

function openVerificationModal(parsedItems, totalInputCount, isFallback = false) {
  const modal = document.getElementById('verification-modal');
  const tableBody = document.getElementById('v-table-body');
  if (!modal || !tableBody) return;

  // MODULE 1: Clear prior rendering buffer before render
  tableBody.innerHTML = '';

  // Enforce unique item identity and strict deduplication
  const cleanItems = window.deduplicateParsedItems
    ? window.deduplicateParsedItems(parsedItems, false)
    : (parsedItems || []);

  // MODULE 3: Total count in badge strictly matches unique deduplicated input count
  verificationOriginalCount = cleanItems.length;

  cleanItems.forEach(item => {
    addVerificationRow(item);
  });

  updateVerificationCounts();

  modal.classList.add('active');
  const wrapper = document.getElementById('v-table-wrapper');
  if (wrapper) wrapper.scrollTop = 0;
}

function confirmAndSendToCounter() {
  const modal = document.getElementById('verification-modal');
  const rows = document.querySelectorAll('#v-table-body tr');
  const verifiedItems = [];

  rows.forEach((row, index) => {
    const nameInput = row.querySelector('.v-item-name');
    const qtyInput = row.querySelector('.v-item-qty');
    const unitSelect = row.querySelector('.v-item-unit');
    const priceInput = row.querySelector('.v-item-price');

    if (!nameInput) return;
    const name = nameInput.value.trim();
    if (!name) return; // Skip empty rows

    const qty = parseFloat(qtyInput ? qtyInput.value : 1.0) || 1.0;
    const unit = unitSelect ? unitSelect.value : 'नग';
    const priceVal = priceInput ? parseFloat(priceInput.value) : null;
    const targetPrice = (!isNaN(priceVal) && priceVal > 0) ? priceVal : null;

    const cachedItem = row._originalItemData || {};

    // Unit & Canonical Normalization
    let quantityNorm = qty;
    let canonicalUnit = 'kg';
    let displayUnit = unit;
    let internalUnit = unit;

    if (unit === 'ग्रॅम' || unit === 'gm') {
      quantityNorm = qty / 1000.0;
      canonicalUnit = 'kg';
      displayUnit = 'ग्रॅम';
      internalUnit = 'gm';
    } else if (unit === 'किलो' || unit === 'kg') {
      quantityNorm = qty;
      canonicalUnit = 'kg';
      displayUnit = 'किलो';
      internalUnit = 'kg';
    } else if (unit === 'लिटर' || unit === 'L') {
      quantityNorm = qty;
      canonicalUnit = 'L';
      displayUnit = 'लिटर';
      internalUnit = 'L';
    } else if (unit === 'पाकीट' || unit === 'packet') {
      quantityNorm = qty;
      canonicalUnit = 'packet';
      displayUnit = 'पाकीट';
      internalUnit = 'पाकीट';
    } else if (unit === 'नग' || unit === 'pcs') {
      quantityNorm = qty;
      canonicalUnit = 'pcs';
      displayUnit = 'नग';
      internalUnit = 'नग';
    }

    const enteredTotal = (targetPrice && targetPrice > 0) ? targetPrice : 0.0;

    verifiedItems.push({
      line_index: index,
      sku_id: cachedItem.sku_id || null,
      name: name,
      qty: qty,
      unit: internalUnit,
      display_qty: qty,
      display_unit: displayUnit,
      quantity_norm: quantityNorm,
      canonical_unit: canonicalUnit,
      confidence: cachedItem.confidence || 0.95,
      original_raw: cachedItem.original_raw || name,
      parse_source: cachedItem.parse_source || 'verified',
      corrected: (name !== (cachedItem.original_raw || '')),
      needs_review: false,
      status: cachedItem.status || 'matched',
      baseline_rate: cachedItem.baseline_rate || null,
      target_price: targetPrice,
      enteredTotal: enteredTotal,
      derivedRate: 0.0,
      currentBadge: cachedItem.baseline_rate ? "संतुलित" : "नवीन नोंद",
      variancePct: 0.0,
      fulfilled: false
    });
  });

  if (verifiedItems.length === 0) {
    showToast("कृपया काउंटरवर पाठवण्यासाठी किमान एक वस्तू भरा.", "error");
    return;
  }

  // Deduplicate before setting state to avoid any duplicate rows
  const finalVerified = window.deduplicateParsedItems
    ? window.deduplicateParsedItems(verifiedItems, false)
    : verifiedItems;

  // Set verified dataset into application state
  state.items = finalVerified;

  // Close verification modal
  if (modal) {
    modal.classList.remove('active');
  }

  // Populate Reverse POS billing table seamlessly
  renderCounterGrid();

  // Smoothly scroll to billing grid
  const billingSection = document.querySelector('.billing-grid-card');
  if (billingSection) {
    billingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  showToast(`यादी निश्चित झाली. एकूण ${state.items.length} वस्तू काउंटरवर पाठवल्या आहेत.`, "success");
}

/**
 * ==============================================================================
 * MODULE 2: OFFLINE DRAFT AUTOSAVE & QUICK RESTORE ENGINE
 * ==============================================================================
 */
function initDraftsManager() {
  const saveBtn = document.getElementById('save-draft-btn');
  const openBtn = document.getElementById('open-drafts-btn');
  const draftsModal = document.getElementById('drafts-modal');
  const closeBtn = document.getElementById('close-drafts-modal');

  // Initialize SavedListsManager callbacks
  if (window.SavedListsManager) {
    window.SavedListsManager.init({
      onLoadToCounter: (items, listName) => {
        loadDraftOntoCounter(items, listName);
        if (draftsModal) draftsModal.classList.remove('active');
      },
      onEditInModal: (items, listName) => {
        openVerificationModal(items, items.length);
        if (draftsModal) draftsModal.classList.remove('active');
      }
    });
  }

  if (saveBtn) {
    const handleSaveInput = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      saveDraftFromCurrentInput();
    };
    saveBtn.addEventListener('click', handleSaveInput);
    saveBtn.addEventListener('touchend', handleSaveInput);
  }

  if (openBtn) {
    const handleOpenDrafts = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      openDraftsModal();
    };
    openBtn.addEventListener('click', handleOpenDrafts);
    openBtn.addEventListener('touchend', handleOpenDrafts);
  }

  if (closeBtn && draftsModal) {
    const handleCloseDrafts = (e) => {
      if (e && e.type === 'touchend') e.preventDefault();
      draftsModal.classList.remove('active');
    };
    closeBtn.addEventListener('click', handleCloseDrafts);
    closeBtn.addEventListener('touchend', handleCloseDrafts);
    draftsModal.addEventListener('click', (e) => {
      if (e.target === draftsModal) draftsModal.classList.remove('active');
    });
  }
}

async function saveDraftFromVerificationModal() {
  const items = extractItemsFromVerificationTable();
  if (items.length === 0) {
    showToast("कृपया सेव्ह करण्यासाठी किमान एक वस्तू यादीत ठेवा.", "warn");
    return;
  }
  let estBudget = 0;
  items.forEach(it => {
    const q = it.qty || 1;
    const p = it.target_price || it.estimated_price || 0;
    estBudget += (q * p);
  });
  estBudget = Math.round(estBudget * 100) / 100;

  const payload = {
    list_name: `किराणा यादी (${items.length} वस्तू)`,
    title: `किराणा यादी (${items.length} वस्तू)`,
    total_items: items.length,
    estimated_budget: estBudget,
    items: items
  };

  // 1. Send POST request to /api/save-grocery-list
  try {
    await fetch('/api/save-grocery-list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (err) {
    console.warn("Server save error:", err);
  }

  // 2. Sync to localStorage key 'smart_kirana_drafts'
  try {
    let localLists = JSON.parse(localStorage.getItem('smart_kirana_drafts') || '[]');
    const localEntry = {
      id: "loc_" + Date.now(),
      list_name: payload.list_name,
      created_at: new Date().toLocaleString("mr-IN"),
      total_items: payload.total_items,
      estimated_budget: payload.estimated_budget,
      items: items
    };
    localLists.unshift(localEntry);
    localStorage.setItem('smart_kirana_drafts', JSON.stringify(localLists.slice(0, 30)));
  } catch (e) {
    console.warn("LocalStorage save error:", e);
  }

  // 3. Close verification modal immediately
  const vModal = document.getElementById('verification-modal');
  if (vModal) vModal.classList.remove('active');

  // 4. Open Saved Lists Panel ("खरेदी इतिहास व सेव्ह केलेल्या याद्या")
  openDraftsModal();
  showToast("यादी यशस्वीरित्या सेव्ह झाली!", "success");
}

function openDraftsModal() {
  const modal = document.getElementById('drafts-modal');
  if (!modal) return;
  modal.classList.add('active');

  if (window.SavedListsManager) {
    window.SavedListsManager.renderSavedListsContainer('#saved-lists-container');
  }
}

function extractItemsFromVerificationTable() {
  const rows = document.querySelectorAll('#v-table-body tr');
  const items = [];

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
    const cachedItem = row._originalItemData || {};

    let quantityNorm = qty;
    let canonicalUnit = 'kg';
    if (unit === 'ग्रॅम' || unit === 'gm') {
      quantityNorm = qty / 1000.0;
      canonicalUnit = 'kg';
    } else if (unit === 'लिटर' || unit === 'L') {
      quantityNorm = qty;
      canonicalUnit = 'L';
    } else if (unit === 'पाकीट') {
      quantityNorm = qty;
      canonicalUnit = 'packet';
    } else if (unit === 'नग') {
      quantityNorm = qty;
      canonicalUnit = 'pcs';
    }

    items.push({
      line_index: index,
      sku_id: cachedItem.sku_id || null,
      name: name,
      qty: qty,
      unit: unit,
      display_qty: qty,
      display_unit: unit,
      quantity_norm: quantityNorm,
      canonical_unit: canonicalUnit,
      confidence: cachedItem.confidence || 0.95,
      original_raw: cachedItem.original_raw || name,
      parse_source: 'draft',
      target_price: targetPrice,
      estimated_price: targetPrice,
      enteredTotal: targetPrice || 0.0,
      derivedRate: 0.0,
      currentBadge: "नवीन नोंद",
      variancePct: 0.0,
      fulfilled: false
    });
  });

  return items;
}

async function saveDraftFromCurrentInput() {
  const textarea = document.getElementById('raw-list-input');
  const rawText = textarea ? textarea.value.trim() : '';

  let items = [];
  if (state.items && state.items.length > 0) {
    items = state.items;
  } else if (rawText && window.parseListLocally) {
    items = window.parseListLocally(rawText);
  }

  if (items.length === 0 && !rawText) {
    showToast("कृपया आधी यादी टाईप करा किंवा काउंटरवर वस्तू भरा.", "warn");
    return;
  }

  let estBudget = 0.0;
  items.forEach(it => {
    const q = it.qty || it.quantity || 1;
    const p = it.target_price || it.estimated_price || it.enteredTotal || 0;
    estBudget += (q * p);
  });

  const payload = {
    list_name: `किराणा यादी (${items.length} वस्तू)`,
    title: `किराणा यादी (${items.length} वस्तू)`,
    total_items: items.length,
    estimated_budget: estBudget,
    items: items
  };

  try {
    await fetch('/api/save-grocery-list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (err) {
    console.warn("Server save error:", err);
  }

  try {
    let localLists = JSON.parse(localStorage.getItem('smart_kirana_drafts') || '[]');
    const localEntry = {
      id: "loc_" + Date.now(),
      list_name: payload.list_name,
      created_at: new Date().toLocaleString("mr-IN"),
      total_items: payload.total_items,
      estimated_budget: payload.estimated_budget,
      items: items
    };
    localLists.unshift(localEntry);
    localStorage.setItem('smart_kirana_drafts', JSON.stringify(localLists.slice(0, 30)));
  } catch(e) {}

  openDraftsModal();
  showToast("यादी यशस्वीरित्या सेव्ह झाली!", "success");
}

async function persistDraftState(items, title, rawText = "") {
  const draftPayload = {
    session_id: state.sessionId,
    title: title || `किराणा यादी ड्राफ्ट`,
    raw_text: rawText || (document.getElementById('raw-list-input') ? document.getElementById('raw-list-input').value : ''),
    items: items,
    saved_at: new Date().toISOString()
  };

  try {
    localStorage.setItem('smart_kirana_drafts', JSON.stringify([draftPayload]));
  } catch (err) {
    console.warn("[Draft Engine] LocalStorage error:", err);
  }

  showToast("यादी यशस्वीरित्या सेव्ह झाली!", "success");
}

function loadDraftOntoCounter(items) {
  if (!items || items.length === 0) return;

  const hasScannedItems = items.some(it => it && (it.parse_source === 'scanned_verified' || it.parse_source === 'scanned_ocr'));
  const cleanItems = (window.deduplicateParsedItems && !hasScannedItems)
    ? window.deduplicateParsedItems(items, false)
    : items;

  state.items = cleanItems.map((it, idx) => {
    const rawU = it.display_unit || it.unit || 'किलो';
    const qty = parseFloat(it.display_qty || it.qty || 1.0) || 1.0;
    const targetPrice = parseFloat(it.target_price || it.estimated_price || 0.0) || 0.0;
    const normQty = it.quantity_norm || ((rawU === 'ग्रॅम' || rawU === 'gm' || rawU === 'ml') ? (qty / 1000.0) : qty);

    return {
      line_index: idx,
      sku_id: it.sku_id || null,
      name: it.name,
      qty: qty,
      unit: rawU,
      display_qty: qty,
      display_unit: rawU,
      quantity_norm: normQty,
      canonical_unit: it.canonical_unit || (rawU === 'ग्रॅम' ? 'kg' : (rawU === 'लिटर' ? 'L' : 'kg')),
      confidence: it.confidence || 0.95,
      original_raw: it.original_raw || it.name,
      parse_source: it.parse_source || 'draft',
      target_price: targetPrice,
      enteredTotal: targetPrice,
      derivedRate: 0.0,
      currentBadge: it.baseline_rate ? "संतुलित" : "नवीन नोंद",
      variancePct: 0.0,
      fulfilled: false
    };
  });

  renderCounterGrid();

  const billingSection = document.querySelector('.billing-grid-card');
  if (billingSection) {
    billingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  showToast(`📂 ड्राफ्ट यादी यशस्वीरीत्या काउंटरवर लोड झाली! (एकूण ${state.items.length} वस्तू)`, "success");
}

function checkAutoRestoreDraft() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('restore') === 'draft') {
    try {
      const stored = localStorage.getItem('smart_kirana_draft');
      if (stored) {
        const data = JSON.parse(stored);
        if (data.items && data.items.length > 0) {
          loadDraftOntoCounter(data.items);
        }
      }
    } catch (e) {}
  }
}


// Render Billing Counter Grid
function renderCounterGrid() {
  const tableBody = document.getElementById('counter-table-body');
  const emptyState = document.getElementById('grid-empty-state');
  const tableWrap = document.getElementById('grid-table-wrap');
  const skeletonWrap = document.getElementById('grid-loading-skeleton');
  const stickyFooter = document.getElementById('sticky-billing-footer');

  if (skeletonWrap) skeletonWrap.style.display = 'none';
  if (!tableBody) return;

  if (state.items.length === 0) {
    if (emptyState) emptyState.style.display = 'block';
    if (tableWrap) tableWrap.style.display = 'none';
    if (stickyFooter) stickyFooter.style.display = 'none';
    return;
  }

  if (emptyState) emptyState.style.display = 'none';
  if (tableWrap) tableWrap.style.display = 'block';
  if (stickyFooter) stickyFooter.style.display = 'flex';

  tableBody.innerHTML = '';

  state.items.forEach((item, index) => {
    const tr = document.createElement('tr');
    tr.id = `item-row-${index}`;
    tr.className = 'table-row-animated';
    tr.style.animationDelay = `${index * 0.04}s`;

    // AI corrected tag if text changed
    const aiTagHtml = item.corrected
      ? `<span class="ai-tag" title="मूळ: ${item.original_raw}">आपोआप दुरुस्त केले</span>`
      : '';

    const canonUnitMR = (item.canonical_unit === 'kg' ? 'किलो' : (item.canonical_unit === 'L' ? 'लिटर' : (item.canonical_unit || item.display_unit)));
    const pastRateText = item.baseline_rate
      ? `${formatINR(item.baseline_rate)} / ${canonUnitMR}`
      : `<span style="color:#94A3B8">— नवीन</span>`;

    // Quantity display with budget intent note: e.g. "१ पाकीट (१० रु. अंदाज)"
    const rawQtyVal = (item.display_qty !== undefined && item.display_qty !== null) ? item.display_qty : item.qty;
    let qtyDisplayHtml;
    if (item.target_price !== undefined && item.target_price !== null && item.target_price > 0) {
      const devQty = toDevanagariDigits(rawQtyVal);
      const devPrice = toDevanagariDigits(Math.round(item.target_price));
      qtyDisplayHtml = `${devQty} ${item.display_unit} (${devPrice} रु. अंदाज)`;
    } else {
      qtyDisplayHtml = `${rawQtyVal} ${item.display_unit}`;
    }

    const placeholderVal = item.target_price ? parseFloat(item.target_price).toFixed(2) : "0.00";
    const inputVal = item.enteredTotal > 0 ? parseFloat(item.enteredTotal).toFixed(2) : "";

    if (item.fulfilled) {
      tr.classList.add('row-fulfilled');
    }

    tr.innerHTML = `
      <td class="item-name-cell">
        <strong>${item.name}</strong>
        <div class="sub-meta">
          <span>${item.display_unit}</span>
          ${aiTagHtml}
          <span class="badge ${getBadgeClass(item.currentBadge)}" id="badge-${index}">${item.currentBadge}</span>
        </div>
      </td>
      <td class="item-qty-cell">${qtyDisplayHtml}</td>
      <td class="today-rate-cell" id="today-rate-${index}">—</td>
      <td class="amount-cell">
        <div class="merchant-input-wrap">
          <span class="rupee-symbol">₹</span>
          <input 
            type="number" 
            step="0.01" 
            min="0"
            inputmode="decimal"
            class="merchant-total-input" 
            data-index="${index}"
            placeholder="${placeholderVal}"
            value="${inputVal}"
          />
        </div>
      </td>
      <td class="check-cell">
        <input 
          type="checkbox" 
          class="item-fulfilled-checkbox" 
          data-index="${index}" 
          ${item.fulfilled ? 'checked' : ''} 
          aria-label="वस्तू दिली" 
          title="वस्तू दिली"
        />
      </td>
    `;
    tableBody.appendChild(tr);
  });

  // Attach fulfilled checkbox toggle events
  document.querySelectorAll('.item-fulfilled-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      const idx = parseInt(e.target.dataset.index, 10);
      const isChecked = e.target.checked;
      if (state.items[idx]) {
        state.items[idx].fulfilled = isChecked;
      }
      const row = e.target.closest('tr');
      if (row) {
        if (isChecked) {
          row.classList.add('row-fulfilled');
        } else {
          row.classList.remove('row-fulfilled');
        }
      }
    });
  });

  // Attach live input events
  document.querySelectorAll('.merchant-total-input').forEach(input => {
    input.addEventListener('input', (e) => {
      const idx = parseInt(e.target.dataset.index, 10);
      const val = parseFloat(e.target.value);
      handleMerchantInputChange(idx, isNaN(val) ? 0 : val);
    });

    // Advance to next row on Enter
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const nextInput = document.querySelector(`.merchant-total-input[data-index="${parseInt(e.target.dataset.index) + 1}"]`);
        if (nextInput) nextInput.focus();
      }
    });
  });

  // Immediately calculate live math for pre-filled budget items
  state.items.forEach((item, index) => {
    if (item.enteredTotal > 0) {
      handleMerchantInputChange(index, item.enteredTotal);
    }
  });

  recalculateGrandTotal();
}

// Live Math on Gross Amount Input
function handleMerchantInputChange(index, enteredTotal) {
  const item = state.items[index];
  if (!item) return;

  item.enteredTotal = enteredTotal;

  const rateCell = document.getElementById(`today-rate-${index}`);
  const badgeCell = document.getElementById(`badge-${index}`);

  if (enteredTotal <= 0 || item.qty <= 0) {
    item.derivedRate = 0.0;
    item.unit_base_rate = 0.0;
    item.line_total = 0.0;
    item.variancePct = 0.0;
    item.currentBadge = item.baseline_rate ? "संतुलित" : "नवीन नोंद";
    if (rateCell) rateCell.innerHTML = "—";
    if (badgeCell) {
      badgeCell.className = `badge ${getBadgeClass(item.currentBadge)}`;
      badgeCell.innerText = item.currentBadge;
    }
  } else {
    // Single Source of Truth Reverse POS derivation via reverse_pos.js
    const posRes = (window.ReversePOS && typeof window.ReversePOS.calculateUnitRate === 'function')
      ? window.ReversePOS.calculateUnitRate(enteredTotal, item.qty, item.unit)
      : {
          lineTotal: enteredTotal,
          normalizedQuantity: (item.unit === 'gm' || item.unit === 'g' || item.unit === 'ml') ? item.qty / 1000.0 : item.qty,
          unitBaseRate: Math.round((enteredTotal / ((item.unit === 'gm' || item.unit === 'g' || item.unit === 'ml') ? item.qty / 1000.0 : item.qty)) * 100) / 100,
          baseUnit: (item.unit === 'gm' || item.unit === 'g') ? 'किलो' : ((item.unit === 'ml') ? 'ली' : (item.canonical_unit || item.unit || 'किलो'))
        };

    const ratePerCanonical = posRes.unitBaseRate;
    item.derivedRate = ratePerCanonical;
    item.unit_base_rate = ratePerCanonical;
    item.line_total = posRes.lineTotal;
    item.normalized_quantity = posRes.normalizedQuantity;

    const baseUnitLabel = posRes.baseUnit;

    if (rateCell) {
      rateCell.innerHTML = `<strong>${formatINR(ratePerCanonical)}</strong> <span style="font-size:0.75rem;color:#64748B;">/${baseUnitLabel}</span>`;
    }

    // Volatility Badge calculation against canonical baseline
    if (!item.baseline_rate) {
      item.currentBadge = "नवीन नोंद";
      item.variancePct = 0.0;
    } else {
      const variance = ((ratePerCanonical - item.baseline_rate) / item.baseline_rate) * 100.0;
      item.variancePct = Math.round(variance * 100) / 100;

      if (variance > 6.0) {
        item.currentBadge = "भाववाढ";
      } else if (variance < -2.0) {
        item.currentBadge = "स्वस्त";
      } else {
        item.currentBadge = "संतुलित";
      }
    }

    if (badgeCell) {
      badgeCell.className = `badge ${getBadgeClass(item.currentBadge)}`;
      badgeCell.innerText = item.currentBadge;
    }
  }

  recalculateGrandTotal();
}

function getBadgeClass(badge) {
  switch (badge) {
    case "संतुलित": return "badge-balanced";
    case "भाववाढ": return "badge-surge";
    case "स्वस्त": return "badge-dip";
    case "नवीन नोंद": return "badge-new";
    default: return "badge-balanced";
  }
}

// Sticky Footer Grand Total & Basket Audit
function recalculateGrandTotal() {
  let sum = 0.0;
  let totalEnteredWithBaseline = 0.0;
  let totalExpectedBaseline = 0.0;

  state.items.forEach(it => {
    if (it.enteredTotal > 0) {
      sum += it.enteredTotal;
      const normQty = it.quantity_norm || ((it.unit === 'gm' || it.unit === 'g' || it.unit === 'ml') ? (it.qty / 1000.0) : it.qty);
      if (it.baseline_rate && normQty > 0) {
        totalEnteredWithBaseline += it.enteredTotal;
        totalExpectedBaseline += (it.baseline_rate * normQty);
      }
    }
  });

  state.grandTotal = Math.round(sum * 100) / 100;

  const totalEl = document.getElementById('footer-grand-total');
  if (totalEl) {
    totalEl.innerText = formatINR(state.grandTotal);
  }

  // Basket Variance
  if (totalExpectedBaseline > 0) {
    const basketVar = ((totalEnteredWithBaseline - totalExpectedBaseline) / totalExpectedBaseline) * 100;
    state.basketVariance = Math.round(basketVar * 100) / 100;
    state.basketStatus = (basketVar <= 5.0) ? "संतुलित बजेट" : "असंतुलित खर्च";
  } else {
    state.basketVariance = 0.0;
    state.basketStatus = "संतुलित बजेट";
  }

  const basketStatusEl = document.getElementById('footer-basket-status');
  if (basketStatusEl) {
    const isBalanced = state.basketStatus === "संतुलित बजेट";
    basketStatusEl.innerHTML = `
      <span class="badge ${isBalanced ? 'badge-balanced' : 'badge-surge'}" style="font-size:0.95rem;padding:6px 14px;">
        ${state.basketStatus} ${state.basketVariance !== 0 ? `(${state.basketVariance > 0 ? '+' : ''}${state.basketVariance}%)` : ''}
      </span>
    `;
  }

  // Enable/disable Pay & Commit buttons
  const payBtn = document.getElementById('pay-qr-btn');
  const commitBtn = document.getElementById('commit-trip-btn');
  const hasZeroOrMissing = state.items.some(it => it.enteredTotal <= 0);

  if (payBtn) payBtn.disabled = (state.grandTotal <= 0 || hasZeroOrMissing);
  if (commitBtn) commitBtn.disabled = (state.grandTotal <= 0 || hasZeroOrMissing);
}

// QR Scanner & Settlement
function initScanner() {
  const qrModal = document.getElementById('qr-modal');
  const openBtn = document.getElementById('pay-qr-btn');
  const closeBtn = document.getElementById('close-qr-modal');
  const videoEl = document.getElementById('qr-video');
  const fileInput = document.getElementById('qr-file-input');
  const manualVpaForm = document.getElementById('manual-vpa-form');

  if (!qrModal) return;

  state.scannerInstance = new KiranaQRScanner({
    videoElement: videoEl,
    onSuccess: (rawCode, parsed) => {
      handleQrResolved(rawCode, parsed);
    },
    onError: (errMsg) => {
      showToast(errMsg, "warn");
    }
  });

  if (openBtn) {
    openBtn.addEventListener('click', async () => {
      if (state.grandTotal <= 0) {
        showToast("कृपया आधी दुकानदाराचे बिल भरा.", "error");
        return;
      }
      qrModal.classList.add('active');
      const started = await state.scannerInstance.startCamera();
      if (!started) {
        // Camera denied or unavailable -> switch to file/manual tab
      }
    });
  }

  function closeModal() {
    qrModal.classList.remove('active');
    state.scannerInstance.stopCamera();
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  qrModal.addEventListener('click', (e) => {
    if (e.target === qrModal) closeModal();
  });

  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        state.scannerInstance.decodeFromImageFile(e.target.files[0]);
      }
    });
  }

  if (manualVpaForm) {
    manualVpaForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const vpaInput = document.getElementById('manual-vpa-input');
      const vpa = vpaInput ? vpaInput.value.trim() : "";
      if (!vpa || !vpa.includes('@')) {
        showToast("कृपया वैध UPI आयडी टाका (उदा. shop@upi)", "error");
        return;
      }
      handleQrResolved(`upi://pay?pa=${encodeURIComponent(vpa)}&pn=${encodeURIComponent(state.merchantName)}`);
    });
  }
}

function handleQrResolved(qrText, parsedInfo) {
  const qrModal = document.getElementById('qr-modal');
  if (qrModal) qrModal.classList.remove('active');
  if (state.scannerInstance) {
    state.scannerInstance.stopCamera();
  }

  // Parse UPI text
  let vpa = (parsedInfo && parsedInfo.vpa) ? parsedInfo.vpa : state.merchantVpa;
  let name = (parsedInfo && parsedInfo.pn) ? parsedInfo.pn : state.merchantName;

  if (typeof qrText === 'string') {
    if (qrText.startsWith('upi://pay') || qrText.includes('pa=')) {
      try {
        const fakeUrl = qrText.startsWith('http') ? qrText : qrText.replace(/^upi:\/\/pay\??/, 'http://upi.org/?');
        const url = new URL(fakeUrl);
        vpa = url.searchParams.get('pa') || vpa;
        name = url.searchParams.get('pn') || name;
      } catch (e) {
        const paMatch = qrText.match(/[?&]pa=([^&]+)/);
        const pnMatch = qrText.match(/[?&]pn=([^&]+)/);
        if (paMatch) vpa = decodeURIComponent(paMatch[1]);
        if (pnMatch) name = decodeURIComponent(pnMatch[1]);
      }
    } else if (qrText.includes('@')) {
      vpa = qrText.trim();
    }
  }

  state.merchantVpa = vpa;
  state.merchantName = name;

  // Auto-populate the merchant info fields on the interface
  const merchantNameInput = document.getElementById('merchant-name-input');
  const merchantVpaInput = document.getElementById('merchant-vpa-input');
  if (merchantNameInput) merchantNameInput.value = name;
  if (merchantVpaInput) merchantVpaInput.value = vpa;

  // Construct NPCI deep link with exact Grand Total override
  const grandTotal = state.grandTotal || 0.0;
  const deepLink = `upi://pay?pa=${encodeURIComponent(vpa)}&pn=${encodeURIComponent(name)}&am=${grandTotal.toFixed(2)}&cu=INR&tn=${encodeURIComponent("किराणा बिल")}`;

  showToast(`UPI पेमेंट सुरू केले जात आहे: ₹${grandTotal.toFixed(2)} (${name})`, "info");

  // Dispatch intent
  window.location.href = deepLink;

  // Listen for user return to ask if payment succeeded
  const handleReturn = () => {
    if (document.visibilityState === 'visible') {
      document.removeEventListener('visibilitychange', handleReturn);
      setTimeout(() => {
        promptPaymentConfirmation();
      }, 800);
    }
  };
  document.addEventListener('visibilitychange', handleReturn);
}

function promptPaymentConfirmation() {
  const confirmModal = document.getElementById('payment-confirm-modal');
  if (confirmModal) {
    confirmModal.classList.add('active');
  }
}

// Database Trip Commit
function initCommitButton() {
  const commitBtn = document.getElementById('commit-trip-btn');
  const confirmYesBtn = document.getElementById('payment-confirm-yes');
  const confirmNoBtn = document.getElementById('payment-confirm-no');
  const confirmModal = document.getElementById('payment-confirm-modal');

  if (confirmYesBtn) {
    confirmYesBtn.addEventListener('click', () => {
      if (confirmModal) confirmModal.classList.remove('active');
      commitTripToDatabase();
    });
  }

  if (confirmNoBtn) {
    confirmNoBtn.addEventListener('click', () => {
      if (confirmModal) confirmModal.classList.remove('active');
      showToast("पेमेंट अपूर्ण राहिले. आपण पुन्हा प्रयत्न करू शकता.", "warn");
    });
  }

  if (commitBtn) {
    commitBtn.addEventListener('click', () => {
      commitTripToDatabase();
    });
  }
}

async function commitTripToDatabase() {
  const commitBtn = document.getElementById('commit-trip-btn');
  if (commitBtn) {
    commitBtn.disabled = true;
    commitBtn.innerHTML = `⏳ जतन होत आहे...`;
  }

  const payload = {
    session_id: state.sessionId,
    merchant_vpa: state.merchantVpa,
    merchant_name: state.merchantName,
    settled_total: state.grandTotal,
    basket_variance: state.basketVariance,
    basket_status: state.basketStatus,
    status: "settled",
    upi_ref: `UPI-${Date.now().toString().slice(-8)}`,
    items: state.items.map(it => {
      const normQty = it.normalized_quantity || it.quantity_norm || ((it.unit === 'gm' || it.unit === 'g' || it.unit === 'ml') ? (it.qty / 1000.0) : it.qty);
      const totalAmount = it.line_total || it.enteredTotal || 0.0;
      const baseRate = it.unit_base_rate || it.derivedRate || 0.0;
      return {
        sku_id: it.sku_id,
        name: it.name,
        quantity_norm: normQty,
        normalized_quantity: normQty,
        unit: it.canonical_unit || (it.unit === 'gm' ? 'kg' : (it.unit === 'ml' ? 'L' : it.unit)),
        display_unit: it.canonical_unit || it.display_unit || 'किलो',
        line_total: totalAmount,
        line_total_amount: totalAmount,
        entered_total: totalAmount,
        unit_base_rate: baseRate,
        derived_rate: baseRate,
        baseline_rate: it.baseline_rate,
        variance_pct: it.variancePct,
        badge: it.currentBadge,
        raw_input: it.original_raw,
        parse_source: it.parse_source,
        ai_confidence: it.confidence
      };
    })
  };

  try {
    const resp = await fetch('/api/v1/trips', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "खरेदी जतन करता आली नाही.");
    }

    showToast("खरेदी यशस्वीरित्या डेटाबेसमध्ये जतन झाली!", "success");
    showReceiptModal(data);

  } catch (err) {
    console.error(err);
    showToast(err.message || "डेटाबेस एरर. कृपया पुन्हा प्रयत्न करा.", "error");
  } finally {
    if (commitBtn) {
      commitBtn.disabled = false;
      commitBtn.innerHTML = `💾 डेटाबेस हिस्ट्रीमध्ये सेव्ह करा`;
    }
  }
}

function showReceiptModal(tripData) {
  const modal = document.getElementById('receipt-modal');
  const previewBody = document.getElementById('receipt-preview-content');
  if (!modal || !previewBody) return;

  let itemsHtml = '';
  tripData.items.forEach(it => {
    itemsHtml += `
      <tr>
        <td style="padding:6px 8px;border-bottom:1px solid #EEE;">${it.name}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #EEE;text-align:center;">${it.quantity_norm} ${it.display_unit}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #EEE;text-align:right;">${formatINR(it.derived_rate)}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #EEE;text-align:right;"><strong>${formatINR(it.entered_total)}</strong></td>
      </tr>
    `;
  });

  previewBody.innerHTML = `
    <div style="text-align:center;margin-bottom:14px;">
      <h2 style="font-size:1.4rem;font-weight:800;color:#1E293B;">पावती - ${tripData.merchant_name}</h2>
      <p style="font-size:0.85rem;color:#64748B;">तारीख: ${tripData.trip_date} | संदर्भ क्र: ${tripData.upi_ref || tripData.session_id.slice(0,8)}</p>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:0.9rem;margin-bottom:16px;">
      <thead>
        <tr style="background:#F8FAFC;border-bottom:2px solid #CBD5E1;">
          <th style="padding:8px;text-align:left;">वस्तू</th>
          <th style="padding:8px;text-align:center;">प्रमाण</th>
          <th style="padding:8px;text-align:right;">दर</th>
          <th style="padding:8px;text-align:right;">रक्कम</th>
        </tr>
      </thead>
      <tbody>
        ${itemsHtml}
      </tbody>
    </table>
    <div style="display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:2px solid #1E293B;font-size:1.2rem;font-weight:800;">
      <span>एकूण देय रक्कम:</span>
      <span style="color:#FF6A00;">${formatINR(tripData.settled_total)}</span>
    </div>
    <div style="display:flex;gap:8px;justify-content:center;margin-top:14px;flex-wrap:wrap;">
      <a href="/receipt/${tripData.trip_id}" target="_blank" class="btn btn-primary btn-sm">
        🖨️ संपूर्ण पावती प्रिंट / सेव्ह करा
      </a>
      <a href="/analyzer?tab=audit-3way&session_id=${tripData.session_id}" class="btn btn-secondary btn-sm">
        📊 ३-वे दर विश्लेषण व ऑडिट पहा
      </a>
    </div>
  `;

  modal.classList.add('active');
  const closeBtn = document.getElementById('close-receipt-modal');
  if (closeBtn) closeBtn.onclick = () => modal.classList.remove('active');
}

/**
 * ==============================================================================
 * MODULE 3 & 4 & 6: DUAL PATHWAY, DUPLICATE DETECTOR & FESTIVAL SURGE CONTROLLER
 * ==============================================================================
 */

function initPathwaySwitcher() {
  const textBtn = document.getElementById('pathway-text-btn');
  const catBtn = document.getElementById('pathway-catalog-btn');
  const textSection = document.getElementById('pathway-text-section');
  const catSection = document.getElementById('pathway-catalog-section');

  const showText = (e) => {
    if (e && e.type === 'touchend') e.preventDefault();
    if (textBtn) {
      textBtn.classList.add('active');
      textBtn.style.background = '#0F766E';
      textBtn.style.color = '#FFFFFF';
    }
    if (catBtn) {
      catBtn.classList.remove('active');
      catBtn.style.background = 'transparent';
      catBtn.style.color = '#475569';
    }
    if (textSection) textSection.style.display = 'block';
    if (catSection) catSection.style.display = 'none';
  };

  const showCatalog = (e) => {
    if (e && e.type === 'touchend') e.preventDefault();
    if (catBtn) {
      catBtn.classList.add('active');
      catBtn.style.background = '#0F766E';
      catBtn.style.color = '#FFFFFF';
    }
    if (textBtn) {
      textBtn.classList.remove('active');
      textBtn.style.background = 'transparent';
      textBtn.style.color = '#475569';
    }
    if (textSection) textSection.style.display = 'none';
    if (catSection) catSection.style.display = 'block';

    // Ensure catalog renders when opening tab
    if (window.VisualCatalog) {
      window.VisualCatalog.init('#home-visual-catalog-container', onVisualCatalogItemAdded);
    }
  };

  if (textBtn) {
    textBtn.addEventListener('click', showText);
    textBtn.addEventListener('touchend', showText);
  }

  if (catBtn) {
    catBtn.addEventListener('click', showCatalog);
    catBtn.addEventListener('touchend', showCatalog);
  }

  // Pre-initialize Point-and-Click Visual Catalog
  if (window.VisualCatalog) {
    window.VisualCatalog.init('#home-visual-catalog-container', onVisualCatalogItemAdded);
  }
}

function onVisualCatalogItemAdded(newItem) {
  const vModal = document.getElementById('verification-modal');
  const isModalOpen = (vModal && vModal.classList.contains('active'));

  checkAndHandleDuplicate(newItem, isModalOpen, () => {
    if (isModalOpen) {
      addVerificationRow(newItem, true /* insert at top / Row 0 */);
      showToast(`'${newItem.name}' पडताळणी यादीत जोडले.`, "success");
    } else {
      appendCatalogItemToCounter(newItem);
    }
  });
}

function appendCatalogItemToCounter(newItem) {
  const rawU = newItem.unit || 'किलो';
  const qty = parseFloat(newItem.qty) || 1.0;
  const targetPrice = parseFloat(newItem.target_price || newItem.estimated_price || 0.0) || 0.0;

  let normQty = qty;
  let canonicalUnit = 'kg';
  if (rawU === 'ग्रॅम' || rawU === 'gm' || rawU === 'g') {
    normQty = qty / 1000.0;
    canonicalUnit = 'kg';
  } else if (rawU === 'लिटर' || rawU === 'L' || rawU === 'l') {
    normQty = qty;
    canonicalUnit = 'L';
  } else if (rawU === 'पाकीट' || rawU === 'packet') {
    normQty = qty;
    canonicalUnit = 'packet';
  } else if (rawU === 'नग' || rawU === 'pcs') {
    normQty = qty;
    canonicalUnit = 'pcs';
  }

  const counterItem = {
    line_index: state.items.length,
    sku_id: newItem.sku_id || null,
    name: newItem.name,
    qty: qty,
    unit: rawU,
    display_qty: qty,
    display_unit: rawU,
    quantity_norm: normQty,
    canonical_unit: canonicalUnit,
    confidence: 1.0,
    original_raw: newItem.name,
    parse_source: 'catalog',
    target_price: targetPrice,
    enteredTotal: targetPrice,
    derivedRate: 0.0,
    currentBadge: newItem.baseline_rate ? "संतुलित" : "नवीन नोंद",
    baseline_rate: newItem.baseline_rate || null,
    variancePct: 0.0,
    fulfilled: false
  };

  state.items.push(counterItem);
  renderCounterGrid();

  showToast(`🛒 '${newItem.name}' काउंटरवर थेट जोडले!`, "success", 2500);
}

let duplicateCallbackConfirm = null;
let duplicateCallbackReject = null;

function initDuplicatePromptModal() {
  const modal = document.getElementById('duplicate-prompt-modal');
  const confirmBtn = document.getElementById('duplicate-confirm-btn');
  const rejectBtn = document.getElementById('duplicate-reject-btn');

  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      if (modal) modal.classList.remove('active');
      if (typeof duplicateCallbackConfirm === 'function') {
        duplicateCallbackConfirm();
      }
      duplicateCallbackConfirm = null;
      duplicateCallbackReject = null;
    });
  }

  if (rejectBtn) {
    rejectBtn.addEventListener('click', () => {
      if (modal) modal.classList.remove('active');
      if (typeof duplicateCallbackReject === 'function') {
        duplicateCallbackReject();
      }
      duplicateCallbackConfirm = null;
      duplicateCallbackReject = null;
    });
  }
}

function showDuplicatePromptModal(itemName, onConfirm, onReject) {
  duplicateCallbackConfirm = onConfirm;
  duplicateCallbackReject = onReject;
  const modal = document.getElementById('duplicate-prompt-modal');
  const msgEl = document.getElementById('duplicate-prompt-message');
  if (msgEl) {
    msgEl.innerHTML = `⚠️ <strong>'${escapeHtml(itemName)}'</strong> आधीच यादीत उपलब्ध आहे! पुन्हा स्वतंत्र जोडायचे आहे का?`;
  }
  if (modal) modal.classList.add('active');
}

function checkAndHandleDuplicate(newItem, isModalOpen, onProceed) {
  const newNameRaw = (newItem.name || '').trim();
  const newBase = newNameRaw.replace(/\[.*?\]/, '').trim().toLowerCase();
  const newBrandMatch = newNameRaw.match(/\[(.*?)\]/);
  const newBrand = newBrandMatch ? newBrandMatch[1].trim().toLowerCase() : '';

  let exactMatch = false;
  let differentBrand = false;
  let existingIndex = -1;

  if (isModalOpen) {
    const rows = document.querySelectorAll('#v-table-body tr');
    rows.forEach((r, idx) => {
      const inp = r.querySelector('.v-item-name');
      if (!inp) return;
      const existingVal = inp.value.trim();
      const exBase = existingVal.replace(/\[.*?\]/, '').trim().toLowerCase();
      const exBrandMatch = existingVal.match(/\[(.*?)\]/);
      const exBrand = exBrandMatch ? exBrandMatch[1].trim().toLowerCase() : '';

      if (exBase === newBase && exBrand === newBrand) {
        exactMatch = true;
        existingIndex = idx;
      } else if (exBase === newBase && exBrand !== newBrand) {
        differentBrand = true;
      }
    });
  } else {
    state.items.forEach((it, idx) => {
      const exName = (it.name || '').trim();
      const exBase = exName.replace(/\[.*?\]/, '').trim().toLowerCase();
      const exBrandMatch = exName.match(/\[(.*?)\]/);
      const exBrand = exBrandMatch ? exBrandMatch[1].trim().toLowerCase() : '';

      if (exBase === newBase && exBrand === newBrand) {
        exactMatch = true;
        existingIndex = idx;
      } else if (exBase === newBase && exBrand !== newBrand) {
        differentBrand = true;
      }
    });
  }

  if (exactMatch) {
    // Same item + same brand -> duplicate warning prompt modal
    showDuplicatePromptModal(
      newNameRaw,
      () => {
        onProceed();
      },
      () => {
        if (isModalOpen) {
          const rows = document.querySelectorAll('#v-table-body tr');
          if (rows[existingIndex]) {
            const qtyInp = rows[existingIndex].querySelector('.v-item-qty');
            if (qtyInp) {
              qtyInp.focus();
              qtyInp.style.backgroundColor = '#FEF08A';
              setTimeout(() => { qtyInp.style.backgroundColor = ''; }, 1500);
            }
          }
        } else {
          const rowInput = document.querySelector(`.merchant-total-input[data-index="${existingIndex}"]`);
          if (rowInput) {
            rowInput.focus();
            rowInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            rowInput.style.backgroundColor = '#FEF08A';
            setTimeout(() => { rowInput.style.backgroundColor = ''; }, 1500);
          }
        }
        showToast(`'${newNameRaw}' चे प्रमाण बदलण्यासाठी हायलाइट केले आहे.`, "info");
      }
    );
  } else if (differentBrand) {
    // Same commodity + different brand -> toast and retain both
    showToast(`नवीन ब्रँडची नोंद जोडली! ('${newNameRaw}')`, "info", 3500);
    onProceed();
  } else {
    onProceed();
  }
}

async function initFestivalSurgeBanner() {
  const banner = document.getElementById('festival-surge-banner');
  const titleEl = document.getElementById('fest-surge-title');
  const textEl = document.getElementById('fest-surge-text');
  const badgeEl = document.getElementById('fest-days-badge');
  const chipsEl = document.getElementById('fest-surge-chips');

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
    console.warn("[FestivalSurge] Advice fetch failed:", e);
  }
}

window.loadDraftOntoCounter = loadDraftOntoCounter;
window.appendCatalogItemToCounter = appendCatalogItemToCounter;
window.renderCounterGrid = renderCounterGrid;
window.recalculateGrandTotal = recalculateGrandTotal;

