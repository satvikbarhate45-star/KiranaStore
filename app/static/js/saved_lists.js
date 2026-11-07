/**
 * Smart Kirana Enterprise - Saved Lists Manager (MODULE 5)
 * Dual-Layer Persistence: Browser localStorage ('smart_kirana_drafts') + Database table (saved_grocery_lists)
 * Displays cards with timestamp, item count, budget, and 1-click counter routing.
 */

const SavedListsManager = (function () {
  const LOCAL_STORAGE_KEY = "smart_kirana_drafts";
  const LEGACY_STORAGE_KEY = "smart_kirana_saved_lists";
  let onLoadToCounterCallback = null;
  let onEditInModalCallback = null;

  function init(options) {
    if (options && options.onLoadToCounter) {
      onLoadToCounterCallback = options.onLoadToCounter;
    }
    if (options && options.onEditInModal) {
      onEditInModalCallback = options.onEditInModal;
    }
  }

  // Dual-Layer Save: Server DB + LocalStorage
  async function saveList(listName, items, estimatedBudget = 0) {
    if (!items || items.length === 0) {
      if (typeof showToast === "function") {
        showToast("यादीत किमान एक वस्तू असणे आवश्यक आहे.", "warn");
      } else {
        alert("यादीत किमान एक वस्तू असणे आवश्यक आहे.");
      }
      return null;
    }

    const payload = {
      list_name: listName || `किराणा यादी (${items.length} वस्तू)`,
      total_items: items.length,
      estimated_budget: parseFloat(estimatedBudget) || 0.0,
      items: items
    };

    // 1. Save to LocalStorage immediately ('smart_kirana_drafts' & fallback sync)
    try {
      const localLists = getLocalSavedLists();
      const localEntry = {
        id: "loc_" + Date.now(),
        list_name: payload.list_name,
        created_at: new Date().toLocaleString("mr-IN"),
        total_items: payload.total_items,
        estimated_budget: payload.estimated_budget,
        items: items
      };
      localLists.unshift(localEntry);
      const jsonStr = JSON.stringify(localLists.slice(0, 30));
      localStorage.setItem(LOCAL_STORAGE_KEY, jsonStr);
      localStorage.setItem(LEGACY_STORAGE_KEY, jsonStr);
    } catch (e) {
      console.warn("[SavedLists] LocalStorage write failed:", e);
    }

    // 2. Save to Server DB table 'saved_grocery_lists'
    let serverSaved = false;
    try {
      const resp = await fetch("/api/v1/lists/saved", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        serverSaved = true;
      }
    } catch (e) {
      console.warn("[SavedLists] Server DB save failed, saved locally:", e);
    }

    // Always show user confirmation toast as specified in prompt
    if (typeof showToast === "function") {
      showToast("यादी यशस्वीरित्या सेव्ह झाली!", "success");
    }

    return { success: true, serverSaved: serverSaved };
  }

  function getLocalSavedLists() {
    try {
      let raw = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (!raw) {
        raw = localStorage.getItem(LEGACY_STORAGE_KEY);
      }
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  async function fetchAllSavedLists() {
    let serverLists = [];
    try {
      const resp = await fetch("/api/v1/lists/saved");
      if (resp.ok) {
        serverLists = await resp.json();
      }
    } catch (e) {
      console.warn("[SavedLists] Server fetch failed, using local storage:", e);
    }

    const localLists = getLocalSavedLists();
    // Merge server & local without exact duplicates
    const combined = [...serverLists];
    localLists.forEach((loc) => {
      if (!combined.some((s) => s.list_name === loc.list_name && s.total_items === loc.total_items)) {
        combined.push(loc);
      }
    });

    return combined;
  }

  async function deleteSavedList(id) {
    // Delete from LocalStorage
    try {
      const localLists = getLocalSavedLists().filter((l) => l.id !== id && String(l.id) !== String(id));
      const jsonStr = JSON.stringify(localLists);
      localStorage.setItem(LOCAL_STORAGE_KEY, jsonStr);
      localStorage.setItem(LEGACY_STORAGE_KEY, jsonStr);
    } catch (e) {
      console.warn("[SavedLists] Local delete failed:", e);
    }

    // If numeric ID, delete from server
    if (typeof id === "number" || (!String(id).startsWith("loc_") && !isNaN(Number(id)))) {
      try {
        await fetch(`/api/v1/lists/saved/${id}`, { method: "DELETE" });
      } catch (e) {
        console.warn("[SavedLists] Server delete failed:", e);
      }
    }

    if (typeof showToast === "function") {
      showToast("यादी यशस्वीरीत्या हटवली गेली.", "info");
    }
  }

  async function renderSavedListsContainer(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    container.innerHTML = `<div style="text-align:center;padding:24px;color:#64748B;">याद्या लोड होत आहेत...</div>`;
    const lists = await fetchAllSavedLists();

    if (lists.length === 0) {
      container.innerHTML = `
        <div style="text-align:center;padding:36px 20px;color:#64748B;">
          <div style="font-size:2.4rem;margin-bottom:8px;">📂</div>
          <h4 style="margin-bottom:4px;color:#1E293B;">अद्याप कोणतीही यादी सेव्ह केलेली नाही</h4>
          <p style="font-size:0.88rem;">किराणा यादी तयार करून 'यादी सेव्ह करा' बटणावर क्लिक करा.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="saved-lists-grid" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:16px;">
        ${lists
          .map((list) => {
            const budgetStr = list.estimated_budget ? `₹${parseFloat(list.estimated_budget).toFixed(2)}` : "उपलब्ध नाही";
            return `
            <div class="saved-list-card" data-id="${list.id}" style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);display:flex;flex-direction:column;justify-content:space-between;">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                  <h4 style="margin:0;font-size:1.05rem;font-weight:700;color:#0F172A;">${list.list_name}</h4>
                  <span style="font-size:0.78rem;background:#E0F2FE;color:#0369A1;padding:2px 8px;border-radius:12px;font-weight:600;">
                    ${list.total_items} वस्तू
                  </span>
                </div>
                
                <div style="font-size:0.82rem;color:#64748B;margin-bottom:12px;">
                  <span>📅 ${list.created_at || "आज"}</span>
                  <span style="margin:0 6px;">•</span>
                  <span>अंदाजे बजेट: <strong style="color:#0F766E;">${budgetStr}</strong></span>
                </div>

                <div class="saved-items-preview" style="font-size:0.82rem;color:#475569;background:#F8FAFC;padding:8px 10px;border-radius:6px;max-height:85px;overflow-y:auto;margin-bottom:14px;line-height:1.5;">
                  ${(list.items || [])
                    .map((it) => {
                      const n = it.name || it.item_name || "वस्तू";
                      const q = it.quantity || it.qty || 1;
                      const u = it.unit || "किलो";
                      return `<div>• ${n} - ${q} ${u}</div>`;
                    })
                    .join("")}
                </div>
              </div>

              <!-- Card Actions -->
              <div style="display:flex;gap:8px;align-items:center;">
                <button 
                  type="button" 
                  class="btn btn-primary btn-sm btn-load-to-counter" 
                  style="flex:2;font-size:0.84rem;font-weight:600;display:flex;align-items:center;justify-content:center;gap:4px;"
                >
                  🛒 यादी काउंटरला पाठवा
                </button>
                <button 
                  type="button" 
                  class="btn btn-secondary btn-sm btn-edit-saved" 
                  title="यादी संपादन करा"
                  style="flex:1;font-size:0.84rem;"
                >
                  ✏️ संपादन
                </button>
                <button 
                  type="button" 
                  class="btn btn-secondary btn-sm btn-delete-saved" 
                  title="हटवा"
                  style="padding:5px 8px;color:#DC2626;"
                >
                  🗑️
                </button>
              </div>
            </div>
          `;
          })
          .join("")}
      </div>
    `;

    // Attach card event listeners
    container.querySelectorAll(".saved-list-card").forEach((card) => {
      const id = card.dataset.id;
      const listData = lists.find((l) => String(l.id) === String(id));
      if (!listData) return;

      const loadBtn = card.querySelector(".btn-load-to-counter");
      if (loadBtn) {
        const handleLoad = (e) => {
          if (e && e.type === "touchend") e.preventDefault();
          if (typeof onLoadToCounterCallback === "function") {
            onLoadToCounterCallback(listData.items || [], listData.list_name);
          }
        };
        loadBtn.addEventListener("click", handleLoad);
        loadBtn.addEventListener("touchend", handleLoad);
      }

      const editBtn = card.querySelector(".btn-edit-saved");
      if (editBtn) {
        const handleEdit = (e) => {
          if (e && e.type === "touchend") e.preventDefault();
          if (typeof onEditInModalCallback === "function") {
            onEditInModalCallback(listData.items || [], listData.list_name, id);
          }
        };
        editBtn.addEventListener("click", handleEdit);
        editBtn.addEventListener("touchend", handleEdit);
      }

      const delBtn = card.querySelector(".btn-delete-saved");
      if (delBtn) {
        const handleDelete = async (e) => {
          if (e && e.type === "touchend") e.preventDefault();
          if (confirm(`'${listData.list_name}' ही यादी नक्की हटवायची आहे का?`)) {
            await deleteSavedList(id);
            renderSavedListsContainer(containerSelector);
          }
        };
        delBtn.addEventListener("click", handleDelete);
        delBtn.addEventListener("touchend", handleDelete);
      }
    });
  }

  return {
    init: init,
    saveList: saveList,
    deleteSavedList: deleteSavedList,
    fetchAllSavedLists: fetchAllSavedLists,
    renderSavedListsContainer: renderSavedListsContainer
  };
})();

window.SavedListsManager = SavedListsManager;
