/**
 * Smart Kirana Enterprise - Visual Grocery Catalog Engine (MODULE 3)
 * Dual Pathway Ingestion: Point-and-Click Zero-Error Visual Catalog
 * Covers 6 Maharashtra Staple Categories + In-Card Packaging & Steppers + Pinned Essentials
 */

const VisualCatalog = (function () {
  let catalogData = null;
  let activeCategory = "cooking_staples";
  let onAddItemCallback = null;
  let activeAddedCount = 0;

  async function init(containerSelector, addCallback) {
    onAddItemCallback = addCallback;
    const container = document.querySelector(containerSelector);
    if (!container) return;

    try {
      const resp = await fetch("/api/v1/catalog/visual-groceries");
      if (!resp.ok) throw new Error("कॅटलॉग डेटा लोड करण्यात अडचण");
      catalogData = await resp.json();
      renderCatalogUI(container);
    } catch (err) {
      console.error("[VisualCatalog] Init failed:", err);
      container.innerHTML = `
        <div class="alert alert-warning" style="margin:12px 0;padding:12px 16px;border-radius:8px;background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;">
          ⚠️ कॅटलॉग डेटा लोड करता आला नाही. कृपया रीफ्रेश करा किंवा थेट मोकळा मजकूर वापरा.
        </div>
      `;
    }
  }

  function parsePackagingDetails(packStr, defaultUnit) {
    if (!packStr) return { qty: 1.0, unit: defaultUnit || "किलो" };
    const str = packStr.trim();

    // Check liters
    const lMatch = str.match(/([0-9.]+)\s*(?:l|ltr|लिटर)/i);
    if (lMatch) return { qty: parseFloat(lMatch[1]), unit: "लिटर" };

    // Check ml
    const mlMatch = str.match(/([0-9.]+)\s*(?:ml|मिली)/i);
    if (mlMatch) return { qty: parseFloat(mlMatch[1]), unit: "मिली" };

    // Check kg
    const kgMatch = str.match(/([0-9.]+)\s*(?:kg|किलो)/i);
    if (kgMatch) return { qty: parseFloat(kgMatch[1]), unit: "किलो" };

    // Check grams
    const gMatch = str.match(/([0-9.]+)\s*(?:g|gm|ग्रॅम)/i);
    if (gMatch) return { qty: parseFloat(gMatch[1]), unit: "ग्रॅम" };

    // Check pieces / नग
    const pcsMatch = str.match(/([0-9.]+)\s*(?:नग|pcs|तुकडे)/i);
    if (pcsMatch) return { qty: parseFloat(pcsMatch[1]), unit: "नग" };

    // Check packets
    const pktMatch = str.match(/([0-9.]+)\s*(?:पाकीट|packet|डबी)/i);
    if (pktMatch) return { qty: parseFloat(pktMatch[1]), unit: "पाकीट" };

    return { qty: 1.0, unit: defaultUnit || "किलो" };
  }

  function renderCatalogUI(container) {
    if (!catalogData || !catalogData.categories) return;

    const html = `
      <div class="visual-catalog-wrapper" style="margin-top:6px;">
        <!-- Top Live Search Bar -->
        <div class="catalog-search-box" style="margin-bottom:14px;position:relative;">
          <input 
            type="text" 
            id="catalog-search-input" 
            class="form-control" 
            placeholder="🔍 वस्तूचे नाव किंवा ब्रँड शोधा (उदा. गोडतेल, साखर, फॉर्च्यून, हळद, तूर डाळ)..."
            style="font-size:0.92rem;padding:10px 16px;border-radius:8px;border:1.5px solid #CBD5E1;box-shadow:0 1px 3px rgba(0,0,0,0.04);width:100%;"
          />
        </div>

        <!-- Category Tabs (6 distinct Maharashtra Staple Tabs) -->
        <div class="catalog-tabs-bar" style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px;margin-bottom:16px;-webkit-overflow-scrolling:touch;">
          ${catalogData.categories
            .map(
              (cat) => `
            <button 
              type="button" 
              class="catalog-tab-btn ${cat.id === activeCategory ? "active" : ""}" 
              data-cat-id="${cat.id}"
              style="white-space:nowrap;padding:8px 16px;border-radius:20px;border:1.5px solid ${
                cat.id === activeCategory ? "#0F766E" : "#E2E8F0"
              };background:${
                cat.id === activeCategory ? "#0F766E" : "#F8FAFC"
              };color:${
                cat.id === activeCategory ? "#FFFFFF" : "#334155"
              };font-weight:700;font-size:0.86rem;cursor:pointer;transition:all 0.2s;"
            >
              ${cat.name_mr}
            </button>
          `
            )
            .join("")}
        </div>

        <!-- Sticky Basket Counter Bar -->
        <div id="catalog-active-basket-bar" style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;padding:10px 16px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="font-size:0.88rem;color:#166534;font-weight:700;display:flex;align-items:center;gap:6px;">
            <span>🛍️</span>
            <span id="catalog-basket-text">कॅटलॉगमधून वस्तू निवडा आणि थेट यादीत जोडा.</span>
          </div>
          <button 
            type="button" 
            id="catalog-go-to-counter-btn" 
            class="btn btn-primary btn-sm"
            style="background:#0F766E;border:none;padding:6px 14px;font-size:0.82rem;font-weight:700;border-radius:6px;cursor:pointer;"
          >
            📋 काउंटर यादी पहा
          </button>
        </div>

        <!-- Interactive Products Grid -->
        <div id="catalog-items-grid" class="catalog-items-grid" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(160px, 1fr));gap:12px;margin-bottom:20px;">
          <!-- Dynamically populated -->
        </div>

        <!-- Pinned Essentials Quick-Add Bar (Frequently Forgotten Items) -->
        <div class="pinned-essentials-bar" style="background:#F8FAFC;border:1.5px dashed #CBD5E1;border-radius:10px;padding:12px 16px;margin-top:16px;">
          <div style="font-size:0.86rem;font-weight:700;color:#1E293B;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
            <span style="font-size:1.1rem;">📌</span>
            <span>नेहमी विसरल्या जाणाऱ्या जीवनावश्यक वस्तू (Quick Add Essentials):</span>
          </div>
          <div class="pinned-chips-list" style="display:flex;flex-wrap:wrap;gap:8px;">
            ${(catalogData.pinned_essentials || [])
              .map(
                (p) => `
              <button 
                type="button" 
                class="pinned-chip-btn" 
                data-name="${p.name}" 
                data-qty="${p.qty}" 
                data-unit="${p.unit}" 
                data-brand="${p.brand || ""}"
                style="background:#FFFFFF;border:1px solid #0F766E;color:#0F766E;padding:6px 12px;border-radius:16px;font-size:0.84rem;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:4px;box-shadow:0 1px 2px rgba(0,0,0,0.04);transition:all 0.15s;"
              >
                <span>➕</span>
                <span>${p.name} ${p.brand ? "[" + p.brand + "]" : ""} (${p.qty} ${p.unit})</span>
              </button>
            `
              )
              .join("")}
          </div>
        </div>
      </div>
    `;

    container.innerHTML = html;
    renderItems(activeCategory);
    attachEvents(container);
  }

  function renderItems(catId, searchQuery = "") {
    const grid = document.getElementById("catalog-items-grid");
    if (!grid || !catalogData) return;

    let itemsToRender = [];
    if (searchQuery && searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      catalogData.categories.forEach((cat) => {
        cat.items.forEach((it) => {
          const matchName = it.name_mr.toLowerCase().includes(q);
          const matchBrand = (it.brands || []).some((b) => b.toLowerCase().includes(q));
          if (matchName || matchBrand) {
            itemsToRender.push(it);
          }
        });
      });
    } else {
      const cat = catalogData.categories.find((c) => c.id === catId);
      if (cat) itemsToRender = cat.items;
    }

    if (itemsToRender.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:36px;color:#64748B;background:#FFFFFF;border-radius:8px;border:1px dashed #CBD5E1;">
          <div style="font-size:2rem;margin-bottom:6px;">🔍</div>
          <strong style="color:#1E293B;">कोणतीही वस्तू सापडली नाही</strong>
          <p style="font-size:0.85rem;margin-top:4px;">कृपया दुसरा शब्द शोधा किंवा श्रेणी टॅब बदला.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = itemsToRender
      .map((item) => {
        const brandOptions = (item.brands || ["सामान्य"])
          .map((b) => `<option value="${b === "सामान्य" ? "" : b}">${b}</option>`)
          .join("");

        const packagingList = item.packagings || item.units || [item.default_unit || "पाकीट"];
        const packOptions = packagingList
          .map((p, pIdx) => `<option value="${p}" ${pIdx === 0 ? "selected" : ""}>${p}</option>`)
          .join("");

        return `
        <div class="catalog-item-card" data-item-id="${item.id}" style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:10px;padding:12px;box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;flex-direction:column;justify-content:space-between;transition:transform 0.15s, box-shadow 0.15s;">
          <div>
            <div style="font-weight:700;font-size:1rem;color:#0F172A;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
              <span>${item.name_mr}</span>
              ${item.base_price ? `<span style="font-size:0.8rem;color:#0F766E;background:#CCFBF1;padding:2px 6px;border-radius:4px;font-weight:600;">₹${item.base_price}</span>` : ""}
            </div>
            
            <!-- Brand Dropdown -->
            <div style="margin-bottom:8px;">
              <label style="font-size:0.75rem;color:#64748B;font-weight:600;display:block;margin-bottom:2px;">ब्रँड निवडा:</label>
              <select class="catalog-brand-select form-control" style="font-size:0.82rem;padding:5px 8px;height:auto;border-radius:6px;">
                ${brandOptions}
              </select>
            </div>

            <!-- Packaging Dropdown -->
            <div style="margin-bottom:8px;">
              <label style="font-size:0.75rem;color:#64748B;font-weight:600;display:block;margin-bottom:2px;">पॅकिंग / साईझ:</label>
              <select class="catalog-packaging-select form-control" style="font-size:0.82rem;padding:5px 8px;height:auto;border-radius:6px;">
                ${packOptions}
              </select>
            </div>

            <!-- Quantity Stepper Row -->
            <div style="margin-bottom:12px;">
              <label style="font-size:0.75rem;color:#64748B;font-weight:600;display:block;margin-bottom:2px;">नगांची संख्या (Packs):</label>
              <div style="display:flex;align-items:center;border:1px solid #CBD5E1;border-radius:6px;overflow:hidden;background:#FFFFFF;">
                <button type="button" class="stepper-minus-btn" style="border:none;background:#F1F5F9;padding:6px 12px;cursor:pointer;font-weight:800;color:#334155;font-size:1rem;">-</button>
                <input type="number" class="stepper-qty-input" value="1" min="1" max="99" style="width:100%;text-align:center;border:none;font-size:0.9rem;font-weight:700;padding:5px 0;-moz-appearance:textfield;" />
                <button type="button" class="stepper-plus-btn" style="border:none;background:#F1F5F9;padding:6px 12px;cursor:pointer;font-weight:800;color:#334155;font-size:1rem;">+</button>
              </div>
            </div>
          </div>

          <button 
            type="button" 
            class="catalog-add-btn btn btn-primary btn-sm" 
            data-name="${item.name_mr}" 
            data-default-unit="${item.default_unit || "पाकीट"}"
            data-price="${item.base_price || 0}"
            style="width:100%;padding:8px 0;font-size:0.88rem;font-weight:700;border-radius:6px;background:#0F766E;border-color:#0F766E;display:flex;align-items:center;justify-content:center;gap:6px;cursor:pointer;"
          >
            <span>➕</span>
            <span>यादीत जोडा</span>
          </button>
        </div>
      `;
      })
      .join("");
  }

  function attachEvents(container) {
    // 1. Category Tab switching (Desktop Click + Mobile Touch)
    container.querySelectorAll(".catalog-tab-btn").forEach((btn) => {
      const handleTabSwitch = (e) => {
        if (e && e.type === "touchend") e.preventDefault();
        container.querySelectorAll(".catalog-tab-btn").forEach((b) => {
          b.classList.remove("active");
          b.style.background = "#F8FAFC";
          b.style.color = "#334155";
          b.style.borderColor = "#E2E8F0";
        });
        btn.classList.add("active");
        btn.style.background = "#0F766E";
        btn.style.color = "#FFFFFF";
        btn.style.borderColor = "#0F766E";
        activeCategory = btn.dataset.catId;
        const searchInput = document.getElementById("catalog-search-input");
        if (searchInput) searchInput.value = "";
        renderItems(activeCategory);
      };

      btn.addEventListener("click", handleTabSwitch);
      btn.addEventListener("touchend", handleTabSwitch);
    });

    // 2. Real-time Live Search
    const searchInput = container.querySelector("#catalog-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const val = e.target.value;
        if (val && val.trim()) {
          renderItems(null, val);
        } else {
          renderItems(activeCategory);
        }
      });
    }

    // 3. Go to counter button
    const goToCounterBtn = container.querySelector("#catalog-go-to-counter-btn");
    if (goToCounterBtn) {
      const handleGoCounter = (e) => {
        if (e && e.type === "touchend") e.preventDefault();
        const billingSection = document.querySelector(".billing-grid-card");
        if (billingSection) {
          billingSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      };
      goToCounterBtn.addEventListener("click", handleGoCounter);
      goToCounterBtn.addEventListener("touchend", handleGoCounter);
    }

    // 4. Grid Click Handlers (Delegation for Steppers and Add to List)
    const grid = container.querySelector("#catalog-items-grid");
    if (grid) {
      grid.addEventListener("click", (e) => {
        const card = e.target.closest(".catalog-item-card");
        if (!card) return;

        const qtyInput = card.querySelector(".stepper-qty-input");

        if (e.target.classList.contains("stepper-minus-btn")) {
          let curr = parseInt(qtyInput.value, 10) || 1;
          if (curr > 1) {
            qtyInput.value = curr - 1;
          }
        } else if (e.target.classList.contains("stepper-plus-btn")) {
          let curr = parseInt(qtyInput.value, 10) || 1;
          qtyInput.value = curr + 1;
        } else if (e.target.closest(".catalog-add-btn")) {
          const btn = e.target.closest(".catalog-add-btn");
          const baseName = btn.dataset.name;
          const defaultUnit = btn.dataset.defaultUnit || "पाकीट";
          const basePrice = parseFloat(btn.dataset.price) || 0.0;

          const brandSelect = card.querySelector(".catalog-brand-select");
          const brandVal = brandSelect ? brandSelect.value.trim() : "";

          const packSelect = card.querySelector(".catalog-packaging-select");
          const packVal = packSelect ? packSelect.value.trim() : "";

          const multiplierPacks = parseInt(qtyInput.value, 10) || 1;
          const packInfo = parsePackagingDetails(packVal, defaultUnit);

          const finalQuantity = Math.round(packInfo.qty * multiplierPacks * 100) / 100;
          const finalUnit = packInfo.unit;

          // Format canonical name with brand brackets: "गोडतेल [फॉर्च्यून]"
          const fullName = brandVal ? `${baseName} [${brandVal}]` : baseName;
          const estLineTotal = basePrice > 0 ? Math.round(basePrice * finalQuantity * 100) / 100 : 0.0;

          activeAddedCount++;
          updateBasketBarText(fullName, finalQuantity, finalUnit);

          // Invoke callback to directly append to active billing table
          if (typeof onAddItemCallback === "function") {
            onAddItemCallback({
              name: fullName,
              base_name: baseName,
              brand: brandVal,
              packaging: packVal,
              quantity: finalQuantity,
              qty: finalQuantity,
              unit: finalUnit,
              display_qty: finalQuantity,
              display_unit: finalUnit,
              estimated_price: estLineTotal,
              target_price: estLineTotal > 0 ? estLineTotal : null
            });
          }

          // Visual Confirmation on Button
          const origHtml = btn.innerHTML;
          btn.innerHTML = `<span>✓</span> <span>जोडले!</span>`;
          btn.style.background = "#059669";
          btn.style.borderColor = "#059669";
          setTimeout(() => {
            btn.innerHTML = origHtml;
            btn.style.background = "#0F766E";
            btn.style.borderColor = "#0F766E";
          }, 800);
        }
      });
    }

    // 5. Pinned Essentials Chips Click
    container.querySelectorAll(".pinned-chip-btn").forEach((chip) => {
      const handleChipClick = (e) => {
        if (e && e.type === "touchend") e.preventDefault();
        const name = chip.dataset.name;
        const qty = parseFloat(chip.dataset.qty) || 1.0;
        const unit = chip.dataset.unit || "पाकीट";
        const brand = chip.dataset.brand || "";
        const fullName = brand ? `${name} [${brand}]` : name;

        activeAddedCount++;
        updateBasketBarText(fullName, qty, unit);

        if (typeof onAddItemCallback === "function") {
          onAddItemCallback({
            name: fullName,
            base_name: name,
            brand: brand,
            packaging: `${qty} ${unit}`,
            quantity: qty,
            qty: qty,
            unit: unit,
            display_qty: qty,
            display_unit: unit,
            estimated_price: 0.0,
            target_price: null
          });
        }

        const origBg = chip.style.background;
        chip.style.background = "#DCFCE7";
        chip.style.borderColor = "#16A34A";
        setTimeout(() => {
          chip.style.background = origBg;
          chip.style.borderColor = "#0F766E";
        }, 500);
      };

      chip.addEventListener("click", handleChipClick);
      chip.addEventListener("touchend", handleChipClick);
    });
  }

  function updateBasketBarText(lastItemName, qty, unit) {
    const barText = document.getElementById("catalog-basket-text");
    if (barText) {
      barText.innerHTML = `✅ '<strong>${lastItemName}</strong>' (${qty} ${unit}) सक्रिय यादीत जोडले! (एकूण ${activeAddedCount} वस्तू जोडल्या)`;
    }
  }

  return {
    init: init
  };
})();

window.VisualCatalog = VisualCatalog;
