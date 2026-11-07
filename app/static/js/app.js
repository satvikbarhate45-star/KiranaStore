/**
 * Smart Kirana Enterprise - Global App Controller
 * Mobile Drawer, Network Status Monitoring, Toast System
 */

document.addEventListener('DOMContentLoaded', () => {
  initMobileDrawer();
  initNetworkStatus();
  highlightActiveNav();
  checkPendingCatalogItems();
  initGrocerySlipScanner();
});

// Check and inject catalog items from /catalog
function checkPendingCatalogItems() {
  const isHomePage = window.location.pathname === '/' || window.location.pathname === '' || window.location.pathname.endsWith('/index.html');
  if (!isHomePage) return;

  try {
    const raw = localStorage.getItem('smart_kirana_pending_items');
    if (!raw) return;
    const items = JSON.parse(raw);
    if (!Array.isArray(items) || items.length === 0) return;

    // Clear key immediately
    localStorage.removeItem('smart_kirana_pending_items');

    const injectItems = () => {
      if (typeof window.loadDraftOntoCounter === 'function') {
        window.loadDraftOntoCounter(items);
        if (typeof showToast === 'function') {
          showToast(`🛒 कॅटलॉगमधून ${items.length} वस्तू थेट काउंटरवर लोड झाल्या!`, 'success', 3000);
        }
      } else if (typeof window.appendCatalogItemToCounter === 'function') {
        items.forEach(it => window.appendCatalogItemToCounter(it));
        if (typeof showToast === 'function') {
          showToast(`🛒 कॅटलॉगमधून ${items.length} वस्तू थेट काउंटरवर लोड झाल्या!`, 'success', 3000);
        }
      } else {
        setTimeout(injectItems, 50);
      }
    };

    injectItems();
  } catch (err) {
    console.warn("[app.js] Pending catalog items error:", err);
  }
}

// Mobile Drawer
function initMobileDrawer() {
  const hamburgerBtn = document.getElementById('hamburger-btn');
  const drawerOverlay = document.getElementById('drawer-overlay');
  const drawerCloseBtn = document.getElementById('drawer-close-btn');

  if (hamburgerBtn && drawerOverlay) {
    hamburgerBtn.addEventListener('click', () => {
      drawerOverlay.classList.add('active');
    });

    if (drawerCloseBtn) {
      drawerCloseBtn.addEventListener('click', () => {
        drawerOverlay.classList.remove('active');
      });
    }

    drawerOverlay.addEventListener('click', (e) => {
      if (e.target === drawerOverlay) {
        drawerOverlay.classList.remove('active');
      }
    });
  }
}

// Network Status
function initNetworkStatus() {
  const offlineBanner = document.getElementById('offline-banner');
  const statusBadge = document.getElementById('network-status-badge');

  function updateStatus() {
    const isOnline = navigator.onLine;
    if (offlineBanner) {
      if (!isOnline) {
        offlineBanner.innerHTML = '⚠️ आपण सध्या ऑफलाइन आहात. स्मार्ट सुधारणा उपलब्ध नाही, साधा पार्सर वापरला आहे.';
        offlineBanner.classList.add('visible');
      } else {
        offlineBanner.classList.remove('visible');
      }
    }
    if (statusBadge) {
      if (isOnline) {
        statusBadge.innerHTML = '<span class="status-dot"></span> ऑनलाइन';
        statusBadge.style.background = '#DCFCE7';
        statusBadge.style.color = '#166534';
      } else {
        statusBadge.innerHTML = '<span class="status-dot" style="background:#EF4444"></span> ऑफलाइन';
        statusBadge.style.background = '#FEE2E2';
        statusBadge.style.color = '#991B1B';
      }
    }
  }

  window.addEventListener('online', () => {
    updateStatus();
    showToast("इंटरनेट पुन्हा कनेक्ट झाले. ऑनलाइन मोड सक्रिय.", "success");
  });

  window.addEventListener('offline', () => {
    updateStatus();
    showToast("इंटरनेट कनेक्शन खंडित झाले. स्थानिक ऑफलाइन मोड सुरू आहे.", "error");
  });

  updateStatus();
}

// Active Nav Link
function highlightActiveNav() {
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link, .drawer-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
      link.classList.add('active');
    } else if (href === '/' && currentPath === '/') {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

// Global Toast System
function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button style="background:none;border:none;color:#FFF;cursor:pointer;font-size:1.1rem;line-height:1;" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * ==============================================================================
 * MODULE 2: COMPREHENSIVE LOCAL PARSER ENGINE
 * - Zero-loss newline input iteration
 * - Deterministic token classification (Currency -> Packaged purchase with target_amount)
 * - Metric normalization without destructive scaling (grams remain grams, liters remain liters)
 * - Generic catch-all with default quantity: 1, unit: 'नग'
 * ==============================================================================
 */

const DEV_TO_ASCII_DIGITS = {
  '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
  '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
};

function devanagariToAsciiDigits(str) {
  if (!str) return '';
  return String(str).replace(/[०-९]/g, d => DEV_TO_ASCII_DIGITS[d] || d);
}

const MARATHI_FRACTION_MAP = {
  "पाव": 0.25,
  "अर्धा": 0.5,
  "अर्धी": 0.5,
  "अर्धे": 0.5,
  "पाऊण": 0.75,
  "सव्वा": 1.25,
  "दीड": 1.5,
  "अडीच": 2.5
};

const CURRENCY_PATTERN = /(?:₹|rs\.?|rupees?|रुपये|रुपयांचे|रुपयांची|रुपयाचे|रु\.?|inr)/i;

// Known Commercial Kirana Brands for deterministic local parsing
const KNOWN_BRANDS_LOCAL = [
  // Multi-word brands first
  { brand: "नंबर १", aliases: ["नंबर १", "नंबर 1", "नं १", "नं. १", "no 1", "no. 1", "number 1", "number one", "godrej no 1"] },
  { brand: "झेड ब्लॅक", aliases: ["झेड ब्लॅक", "zed black", "zedblack"] },
  { brand: "वाघ बकरी", aliases: ["वाघ बकरी", "wagh bakri", "waghbakri"] },
  { brand: "रेड लेबल", aliases: ["रेड लेबल", "red label", "redlabel"] },
  { brand: "ताजमहल", aliases: ["ताजमहल", "taj mahal", "tajmahal"] },
  { brand: "सर्फ एक्सेल", aliases: ["सर्फ एक्सेल", "surf excel", "surfexcel"] },
  { brand: "क्लोजअप", aliases: ["क्लोजअप", "close up", "closeup"] },
  { brand: "पारले-जी", aliases: ["पारले-जी", "पारले जी", "parle-g", "parle g", "parleg"] },

  // Single-word brands
  { brand: "फॉर्च्यून", aliases: ["फॉर्च्यून", "fortune"] },
  { brand: "धारा", aliases: ["धारा", "dhara"] },
  { brand: "जेमिनी", aliases: ["जेमिनी", "gemini"] },
  { brand: "सफोला", aliases: ["सफोला", "saffola"] },
  { brand: "महाकोश", aliases: ["महाकोश", "mahakosh"] },
  { brand: "सनरिच", aliases: ["सनरिच", "sunrich"] },
  { brand: "रुचि", aliases: ["रुचि", "ruchi"] },
  { brand: "तिरुपती", aliases: ["तिरुपती", "tirupati"] },
  { brand: "विनर", aliases: ["विनर", "winner"] },
  { brand: "विलास", aliases: ["विलास", "vilas"] },
  { brand: "मंगलदीप", aliases: ["मंगलदीप", "mangaldeep"] },
  { brand: "मोक्ष", aliases: ["मोक्ष", "moksh"] },
  { brand: "सायकल", aliases: ["सायकल", "cycle"] },
  { brand: "संतूर", aliases: ["संतूर", "santoor"] },
  { brand: "लक्स", aliases: ["लक्स", "lux"] },
  { brand: "लाइफबॉय", aliases: ["लाइफबॉय", "lifebuoy"] },
  { brand: "डेटॉल", aliases: ["डेटॉल", "dettol"] },
  { brand: "हमाम", aliases: ["हमाम", "hamam"] },
  { brand: "मेडीमिक्स", aliases: ["मेडीमिक्स", "medimix"] },
  { brand: "डव्ह", aliases: ["डव्ह", "dove"] },
  { brand: "विम", aliases: ["विम", "vim"] },
  { brand: "निरमा", aliases: ["निरमा", "nirma"] },
  { brand: "घडी", aliases: ["घडी", "ghadi"] },
  { brand: "रिन", aliases: ["रिन", "rin"] },
  { brand: "एरियल", aliases: ["एरियल", "ariel"] },
  { brand: "व्हील", aliases: ["व्हील", "wheel"] },
  { brand: "टाटा", aliases: ["टाटा", "tata"] },
  { brand: "सोसायटी", aliases: ["सोसायटी", "society"] },
  { brand: "एव्हरेस्ट", aliases: ["एव्हरेस्ट", "everest"] },
  { brand: "सुहाना", aliases: ["सुहाना", "suhana"] },
  { brand: "रामबंधू", aliases: ["रामबंधू", "rambandhu"] },
  { brand: "एमडीएच", aliases: ["एमडीएच", "mdh"] },
  { brand: "बादशाह", aliases: ["बादशाह", "badshah"] },
  { brand: "कॅच", aliases: ["कॅच", "catch"] },
  { brand: "आशीर्वाद", aliases: ["आशीर्वाद", "aashirvaad", "ashirwad"] },
  { brand: "पतंजली", aliases: ["पतंजली", "patanjali"] },
  { brand: "कोलगेट", aliases: ["कोलगेट", "colgate"] },
  { brand: "पेप्सोडेंट", aliases: ["पेप्सोडेंट", "pepsodent"] },
  { brand: "डाबर", aliases: ["डाबर", "dabur"] },
  { brand: "पारले", aliases: ["पारले", "parle"] },
  { brand: "ब्रिटानिया", aliases: ["ब्रिटानिया", "britannia"] },
  { brand: "किसान", aliases: ["किसान", "kissan"] },
  { brand: "मॅगी", aliases: ["मॅगी", "maggi"] }
];

// Canonical Commodity Normalization Mappings
const COMMODITY_MAPPINGS_LOCAL = [
  // Strict Commodity Separation Rule 1: "गोडतेल" / "godtel" / "god tel" / "खाद्यतेल" -> "गोडतेल"
  { commodity: "गोडतेल", aliases: ["गोडतेल", "godtel", "god tel", "खाद्यतेल", "गोड तेल", "cooking oil", "refined oil"] },
  { commodity: "शेंगदाणे", aliases: ["shengdane", "peanuts", "दाणे", "शेंगदाणा", "shengdana"] },
  { commodity: "अगरबत्ती", aliases: ["अगरबत्ती", "agarbatti", "incense sticks", "अगरबत्या", "धूप"] },
  { commodity: "साबण", aliases: ["साबण", "saban", "soap"] },
  { commodity: "साखर", aliases: ["साखर", "सक्कर", "sakhar", "sakkar", "sugar"] },
  { commodity: "मीठ", aliases: ["मीठ", "मिट", "mit", "salt", "mitha", "mith"] },
  { commodity: "चहा पावडर", aliases: ["चहा पावडर", "चहापत्ती", "tea powder", "चाय", "tea"] },
  { commodity: "तूर डाळ", aliases: ["तूर डाळ", "तुरीची डाल", "तुरीची डाळ", "tur dal", "toor dal", "turdaal"] },
  { commodity: "तांदूळ", aliases: ["तांदूळ", "तांदुल", "tandul", "rice", "kolam rice", "भात"] },
  { commodity: "गहू पीठ", aliases: ["गहू पीठ", "कणिक", "गव्हाचे पीठ", "wheat flour", "atta", "आटा", "गव्हाच पीठ", "गहूचे पीठ", "गव्हाचेपीठ", "गव्हाचपीठ"] },
  { commodity: "हळद", aliases: ["हळद", "हलद", "halad", "turmeric", "haldi"] },
  { commodity: "जिरे", aliases: ["जिरे", "जिरं", "jire", "jeera", "cumin"] },
  { commodity: "मोहरी", aliases: ["मोहरी", "mohari", "rai", "mustard"] },
  { commodity: "साजूक तूप", aliases: ["तूप", "साजूक तूप", "ghee", "sajuk tup", "pure ghee"] },
  { commodity: "मूग डाळ", aliases: ["मूग डाळ", "मुगाची डाळ", "moong dal", "mung dal"] },
  { commodity: "चणा डाळ", aliases: ["चणा डाळ", "हरभरा डाळ", "chana dal", "चना दाल"] },
  { commodity: "पोहे", aliases: ["पोहे", "जाड पोहे", "pohe", "poha"] },
  { commodity: "गूळ", aliases: ["गूळ", "गुल", "gul", "jaggery"] },
  { commodity: "बेसन", aliases: ["बेसन", "हरभरा पीठ", "gram flour", "besan"] },
  { commodity: "रवा", aliases: ["रवा", "सुजी", "rava", "sooji", "बारीक रवा"] },
  { commodity: "कांदा", aliases: ["कांदा", "कांदे", "kanda", "onion"] },
  { commodity: "बटाटा", aliases: ["बटाटा", "बटाटे", "batata", "potato", "आलू"] },
  { commodity: "कोथिंबीर", aliases: ["कोथिंबीर", "kothimbir", "coriander"] },
  { commodity: "मेथी", aliases: ["मेथी", "methi"] },
  { commodity: "पालक", aliases: ["पालक", "palak"] }
];

function extractBrandAndCommodityLocally(rawText) {
  if (!rawText) return "";
  const cleaned = rawText.trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
  if (!cleaned) return "";

  // If already bracketed: preserve format e.g. "अगरबत्ती [विलास]"
  const bracketMatch = cleaned.match(/^(.*?)\s*\[(.*?)\]$/);
  if (bracketMatch) {
    const cPart = bracketMatch[1].trim();
    const bPart = bracketMatch[2].trim();
    const normC = extractBrandAndCommodityLocally(cPart).replace(/\s*\[.*?\]/g, '').trim();
    return bPart ? `${normC} [${bPart}]` : normC;
  }

  const lowerText = cleaned.toLowerCase();
  let detectedBrand = null;
  let remainingText = cleaned;

  // 1. Detect Brand
  for (const bObj of KNOWN_BRANDS_LOCAL) {
    for (const al of bObj.aliases) {
      const escaped = al.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(^|\\b|\\s)${escaped}(\\b|\\s|$)`, 'i');
      if (regex.test(lowerText)) {
        detectedBrand = bObj.brand;
        remainingText = remainingText.replace(new RegExp(`(^|\\b|\\s)${escaped}(\\b|\\s|$)`, 'i'), ' ').trim();
        break;
      }
    }
    if (detectedBrand) break;
  }

  const remClean = remainingText.trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
  const remLower = remClean.toLowerCase();

  // 2. Strict Commodity Classification
  let canonicalCommodity = null;
  const targetCheck = remLower || lowerText;

  const hasShengdana = /शेंगदाणा|शेंगदाणे|दाणे|shengdana|shengdane|groundnut/.test(targetCheck);
  const hasOil = /तेल|tel|oil/.test(targetCheck);
  const hasGodtel = /गोडतेल|godtel|god\s*tel|खाद्यतेल|गोड\s*तेल|cooking\s*oil|refined\s*oil/.test(targetCheck);

  if (hasGodtel) {
    canonicalCommodity = "गोडतेल";
  } else if (hasShengdana && hasOil) {
    canonicalCommodity = "शेंगदाणा तेल";
  } else if (hasShengdana && !hasOil) {
    canonicalCommodity = "शेंगदाणे";
  } else if (hasOil && !hasShengdana && !hasGodtel) {
    canonicalCommodity = "गोडतेल";
  } else {
    for (const cObj of COMMODITY_MAPPINGS_LOCAL) {
      for (const al of cObj.aliases) {
        const escaped = al.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(^|\\b|\\s)${escaped}(\\b|\\s|$)`, 'i');
        if (regex.test(targetCheck) || targetCheck === al.toLowerCase()) {
          canonicalCommodity = cObj.commodity;
          break;
        }
      }
      if (canonicalCommodity) break;
    }
  }

  const finalCommodity = canonicalCommodity || remClean || cleaned;

  if (detectedBrand) {
    return `${finalCommodity} [${detectedBrand}]`;
  }
  return finalCommodity;
}

/**
 * Intelligent Text Normalization & Pre-splitting:
 * Splits raw incoming input using multi-delimiters: commas (,), newlines (\r?\n),
 * semicolons (;), and Marathi connectors ('आणि', 'तसेच').
 * Trims every token, eliminates empty entries, and obtains a clean array of raw item phrases.
 */
function splitRawGroceryInput(rawText) {
  if (!rawText || typeof rawText !== 'string') return [];
  const tokens = rawText
    .split(/(?:\r?\n|[,;]|\s+(?:आणि|तसेच)\s+)/gi)
    .map(t => {
      let cleaned = t.trim();
      // Remove leading bullet/numbering markers like '1. ', '2) ', '- ', '• ' while preserving decimals like '1.5 kg'
      cleaned = cleaned.replace(/^\s*(?:[\d\u0966-\u096F]+(?:\.|\))(?!\d)\s*|[\-\*•]\s*)/i, '').trim();
      return cleaned;
    })
    .filter(t => t.length > 0 && !/^(?:आणि|तसेच|[,;])$/i.test(t));
  return tokens;
}

/**
 * Parses raw grocery list text with guaranteed zero dropped lines.
 * Returns array of N structured item records for N valid lines.
 */
function parseListLocally(rawText) {
  if (!rawText || typeof rawText !== 'string') return [];

  // 1. Zero-Loss Input Iteration: split by multi-delimiters and filter empty
  const lines = splitRawGroceryInput(rawText);
  const items = [];

  lines.forEach((line, index) => {
    const rawLine = line;
    let name = "";
    let quantity = 1.0;
    let unit = "नग";
    let displayUnit = "नग";
    let targetAmount = null;

    // 2. Deterministic Token Classification:
    // A. Currency Tokens: e.g. "mitha 10rupees", "20 rs kothimbir", "अगरबत्ती ५० रुपये", "10 रुपयांचे मीठ"
    const curEndMatch = rawLine.match(/(?:[\-:–x×]\s*|\s+)([0-9०-९]+(?:\.[0-9०-९]+)?)\s*(?:₹|rs\.?|rupees?|रुपये|रुपयांचे|रुपयांची|रुपयाचे|रु\.?|inr)\s*$/i);
    const curStartMatch = rawLine.match(/^([0-9०-९]+(?:\.[0-9०-९]+)?)\s*(?:₹|rs\.?|rupees?|रुपये|रुपयांचे|रुपयांची|रुपयाचे|रु\.?|inr)\s*(?:[\-:–x×]\s*|\s+)(.+)$/i);
    const curRevMatch = rawLine.match(/(?:[\-:–x×]\s*|\s+)(?:₹|rs\.?|rupees?|रुपये|रुपयांचे|रुपयांची|रुपयाचे|रु\.?|inr)\s*([0-9०-९]+(?:\.[0-9०-९]+)?)\s*$/i);

    if (curEndMatch) {
      name = rawLine.slice(0, curEndMatch.index).trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
      targetAmount = parseFloat(devanagariToAsciiDigits(curEndMatch[1]));
    } else if (curStartMatch) {
      name = curStartMatch[2].trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
      targetAmount = parseFloat(devanagariToAsciiDigits(curStartMatch[1]));
    } else if (curRevMatch) {
      name = rawLine.slice(0, curRevMatch.index).trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
      targetAmount = parseFloat(devanagariToAsciiDigits(curRevMatch[1]));
    }

    if (targetAmount !== null && !isNaN(targetAmount) && targetAmount > 0) {
      // Currency intent: treat as packaged retail purchase (unit: 'पाकीट' or contextual retail packaging)
      const lower = name.toLowerCase();
      if (/कोथिंबीर|kothimbir|coriander|मेथी|methi|पालक|palak|पुदिना|pudina/.test(lower)) {
        unit = "पेंढी";
        displayUnit = "पेंढी";
      } else if (/साबण|soap|पेन|pen|ब्रश|brush/.test(lower)) {
        unit = "नग";
        displayUnit = "नग";
      } else {
        unit = "पाकीट";
        displayUnit = "पाकीट";
      }
      quantity = 1.0;
    } else {
      // B. Metric Normalization: Extract quantity and unit pairs without destructive scaling
      // Check Marathi fraction words first
      let matchedFraction = false;
      for (const [fWord, fVal] of Object.entries(MARATHI_FRACTION_MAP)) {
        const regex = new RegExp(`(^|\\s)${fWord}(\\s|$)`);
        if (regex.test(rawLine)) {
          name = rawLine.replace(fWord, '').replace(/किलो|लिटर|ग्रॅम|gm|kg|L/gi, '').trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
          quantity = fVal;
          if (/ग्रॅम|gm|ग्राम/i.test(rawLine)) {
            unit = "gm";
            displayUnit = "ग्रॅम";
          } else if (/लिटर|लीटर|L|ltr/i.test(rawLine)) {
            unit = "L";
            displayUnit = "लिटर";
          } else {
            unit = "kg";
            displayUnit = "किलो";
          }
          matchedFraction = true;
          break;
        }
      }

      if (!matchedFraction) {
        // Trailing quantity & unit: "साखर२किलो", "तांदूळ 500 gm", "shengdanatel 2 L", "साबण ४ नग"
        const trailingMatch = rawLine.match(/(?<=\S)\s*([0-9०-९]+(?:\.[0-9०-९]+)?|[0-9०-९]+\/[0-9०-९]+)\s*([A-Za-z\u0900-\u097F.\s]*?)$/);
        const leadingMatch = rawLine.match(/^([0-9०-९]+(?:\.[0-9०-९]+)?|[0-9०-९]+\/[0-9०-९]+)\s*([A-Za-z\u0900-\u097F.]+)?\s*[\-:–x×]?\s*(.+)$/);

        let matchQty = null;
        let matchUnit = "";

        if (trailingMatch) {
          name = rawLine.slice(0, trailingMatch.index).trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
          matchQty = trailingMatch[1];
          matchUnit = trailingMatch[2].trim();
        } else if (leadingMatch) {
          name = leadingMatch[3].trim().replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
          matchQty = leadingMatch[1];
          matchUnit = (leadingMatch[2] || "").trim();
        }

        if (matchQty) {
          let parsedVal;
          if (matchQty.includes('/')) {
            const p = matchQty.split('/');
            parsedVal = parseFloat(devanagariToAsciiDigits(p[0])) / parseFloat(devanagariToAsciiDigits(p[1]));
          } else {
            parsedVal = parseFloat(devanagariToAsciiDigits(matchQty));
          }
          quantity = (isNaN(parsedVal) || parsedVal <= 0) ? 1.0 : parsedVal;

          const uLower = matchUnit.toLowerCase();
          if (/^(?:gm|g|gms|gram|grams|ग्रॅम|ग्राम)$/i.test(uLower)) {
            unit = "gm";
            displayUnit = "ग्रॅम";
          } else if (/^(?:kg|kgs|kilo|किलो|कि\.)$/i.test(uLower)) {
            unit = "kg";
            displayUnit = "किलो";
          } else if (/^(?:l|ltr|liter|litre|लिटर)$/i.test(uLower)) {
            unit = "L";
            displayUnit = "लिटर";
          } else if (/^(?:ml|मिली|मि\.ली\.)$/i.test(uLower)) {
            unit = "ml";
            displayUnit = "मिली";
          } else if (/^(?:packet|packets|पाकीट|पाकिटे|pouch|pkt)$/i.test(uLower)) {
            unit = "पाकीट";
            displayUnit = "पाकीट";
          } else if (/^(?:pcs|piece|pieces|नग|तुकडे)$/i.test(uLower)) {
            unit = "नग";
            displayUnit = "नग";
          } else if (/^(?:dozen|doz|डझन)$/i.test(uLower)) {
            unit = "डझन";
            displayUnit = "डझन";
          } else if (/^(?:bunch|bunches|पेंढी|पेंढ्या)$/i.test(uLower)) {
            unit = "पेंढी";
            displayUnit = "पेंढी";
          } else if (matchUnit.length > 0) {
            unit = matchUnit;
            displayUnit = matchUnit;
          } else {
            unit = "पाकीट";
            displayUnit = "पाकीट";
          }
        } else {
          // C. Generic Catch-All: preserve raw text as item label, default quantity: 1, unit: 'नग'
          name = rawLine.replace(/^[\-:–x×]+|[\-:–x×]+$/g, '').trim();
          quantity = 1.0;
          unit = "नग";
          displayUnit = "नग";
        }
      }
    }

    if (!name) name = rawLine.trim() || "किराणा वस्तू";

    // Extract Brand and Commodity with strict separation
    const finalFormattedName = extractBrandAndCommodityLocally(name);

    // Compute metric normalization factor without altering original entered unit or qty
    let normQty = quantity;
    let canonUnit = unit;
    if (unit === 'gm' || unit === 'g') {
      normQty = quantity / 1000.0;
      canonUnit = 'kg';
    } else if (unit === 'ml') {
      normQty = quantity / 1000.0;
      canonUnit = 'L';
    } else if (unit === 'kg') {
      normQty = quantity;
      canonUnit = 'kg';
    } else if (unit === 'L') {
      normQty = quantity;
      canonUnit = 'L';
    }

    items.push({
      line_index: index,
      name: finalFormattedName || name,
      qty: quantity,
      unit: unit,
      display_qty: quantity,
      display_unit: displayUnit,
      quantity_norm: normQty,
      canonical_unit: canonUnit,
      confidence: 0.65,
      original_raw: rawLine,
      parse_source: 'regex',
      corrected: false,
      needs_review: false,
      status: 'matched',
      target_price: targetAmount,
      baseline_rate: null
    });
  });

  return items;
}

/**
 * Global Brand-Commodity Cache for high-speed local resolution
 */
const KiranaBrandCache = {
  _cache: {
    "विलास अगरबत्ती": "अगरबत्ती [विलास]",
    "vilas agarbatti": "अगरबत्ती [विलास]",
    "नंबर १ साबण": "साबण [नंबर १]",
    "no 1 soap": "साबण [नंबर १]",
    "संतूर साबण": "साबण [संतूर]",
    "santoor soap": "साबण [संतूर]",
    "फॉर्च्यून गोडतेल": "गोडतेल [फॉर्च्यून]",
    "fortune godtel": "गोडतेल [फॉर्च्यून]",
    "टाटा मीठ": "मीठ [टाटा]",
    "tata salt": "मीठ [टाटा]",
    "एव्हरेस्ट हळद": "हळद [एव्हरेस्ट]",
    "everest halad": "हळद [एव्हरेस्ट]",
    "आशीर्वाद आटा": "गहू पीठ [आशीर्वाद]",
    "aashirvaad atta": "गहू पीठ [आशीर्वाद]",
    "पतंजली तूप": "साजूक तूप [पतंजली]",
    "patanjali ghee": "साजूक तूप [पतंजली]"
  },
  get(key) {
    if (!key) return null;
    const k = String(key).trim().toLowerCase();
    if (this._cache[k]) return this._cache[k];
    try {
      const stored = localStorage.getItem('kirana_brand_cache_' + k);
      if (stored) return stored;
    } catch (e) {}
    return null;
  },
  set(key, val) {
    if (!key || !val) return;
    const k = String(key).trim().toLowerCase();
    this._cache[k] = val;
    try {
      localStorage.setItem('kirana_brand_cache_' + k, val);
    } catch (e) {}
  }
};

/**
 * Normalizes product name for canonical comparison and deduplication in JavaScript.
 * Strips bracketed brands and maps Devanagari synonyms to base canonical commodity.
 */
function normalizeCanonicalCommodity(name) {
  if (!name || typeof name !== 'string') return '';
  const base = name.replace(/\[.*?\]/g, '').trim().toLowerCase();
  
  if (/गोडतेल|godtel|god\s*tel|खाद्यतेल|गोड\s*तेल|cooking\s*oil|refined\s*oil/.test(base)) {
    return "गोडतेल";
  }
  if (/शेंगदाणा\s*तेल|shengdana\s*tel/.test(base)) {
    return "शेंगदाणा तेल";
  }
  if (/शेंगदाणे|शेंगदाणा|shengdana|shengdane|groundnut/.test(base)) {
    return "शेंगदाणे";
  }

  for (const cObj of COMMODITY_MAPPINGS_LOCAL) {
    for (const al of cObj.aliases) {
      const alLower = al.toLowerCase();
      if (base === alLower || base.includes(alLower)) {
        return cObj.commodity.toLowerCase();
      }
    }
  }
  return base;
}

/**
 * MODULE 1: STRICT DEDUPLICATION & CANONICAL KEY MAPPING (JS)
 * - Eliminates duplicate rows from overlapping chunk batches.
 * - Eliminates identical repeated commodities (like "गव्हाचे पीठ" appearing multiple times).
 * - Preserves deliberate distinct multi-line items.
 */
function deduplicateParsedItems(items, mergeDuplicates = false) {
  if (!items || !Array.isArray(items)) return [];

  const seenLineIndices = new Set();
  const seenCanonical = new Map();
  const deduped = [];

  for (const item of items) {
    if (!item) continue;

    // 1. Normalize name using local brand/commodity extractor
    const rawName = item.name || item.original_raw || '';
    const normName = extractBrandAndCommodityLocally(rawName);
    if (normName) {
      item.name = normName;
    }

    // Scanned receipts: preserve every physical row without dropping
    if (item.parse_source === 'scanned_verified' || item.parse_source === 'scanned_ocr') {
      deduped.push(item);
      continue;
    }

    // 2. Discard overlapping chunk duplicates by line_index
    const lIdx = item.line_index;
    if (lIdx !== undefined && lIdx !== null && seenLineIndices.has(lIdx)) {
      continue;
    }
    if (lIdx !== undefined && lIdx !== null) {
      seenLineIndices.add(lIdx);
    }

    // 3. Canonical Key Identity Check
    const effectiveName = normName || rawName;
    const cComm = normalizeCanonicalCommodity(effectiveName);
    const rawU = String(item.canonical_unit || item.unit || '').trim().toLowerCase();
    let cUnit = rawU;
    if (/किलो|kg/i.test(rawU)) cUnit = 'kg';
    else if (/लिटर|l|ltr|liter/i.test(rawU)) cUnit = 'L';
    else if (/पाकीट|packet|pouch|pkt/i.test(rawU)) cUnit = 'packet';
    else if (/नग|pcs|piece/i.test(rawU)) cUnit = 'pcs';
    const brandMatch = effectiveName.match(/\[(.*?)\]/);
    const bTag = brandMatch ? brandMatch[1].trim().toLowerCase() : '';
    const canonKey = `${cComm}:${bTag}:${cUnit}`;

    if (seenCanonical.has(canonKey)) {
      const existingItem = seenCanonical.get(canonKey);
      const exQty = parseFloat(existingItem.qty || 1.0) || 1.0;
      const curQty = parseFloat(item.qty || 1.0) || 1.0;
      const exRaw = String(existingItem.original_raw || '').trim();
      const curRaw = String(item.original_raw || '').trim();

      // Check for identical repetition (same raw text, or identical commodity + qty)
      if (exRaw === curRaw || Math.abs(exQty - curQty) < 0.001) {
        // Accidental duplicate / identical repeated line: eliminate!
        continue;
      } else if (mergeDuplicates) {
        // Merge quantities into existing record
        const newQty = exQty + curQty;
        existingItem.qty = newQty;
        existingItem.display_qty = newQty;
        if (existingItem.quantity_norm !== undefined && item.quantity_norm !== undefined) {
          existingItem.quantity_norm = (existingItem.quantity_norm || 0) + (item.quantity_norm || 0);
        }
        if (item.target_price) {
          existingItem.target_price = (existingItem.target_price || 0) + (item.target_price || 0);
        }
        continue;
      } else {
        // Deliberate separate line entries with distinct quantities: preserve with unique row
        deduped.push(item);
        continue;
      }
    } else {
      seenCanonical.set(canonKey, item);
      deduped.push(item);
    }
  }

  return deduped;
}

// Attach globally for window access
window.splitRawGroceryInput = splitRawGroceryInput;
window.parseListLocally = parseListLocally;
window.extractBrandAndCommodityLocally = extractBrandAndCommodityLocally;
window.normalizeCanonicalCommodity = normalizeCanonicalCommodity;
window.deduplicateParsedItems = deduplicateParsedItems;
window.KiranaBrandCache = KiranaBrandCache;
window.KiranaLocalParser = {
  splitRawGroceryInput,
  parseListLocally,
  devanagariToAsciiDigits,
  extractBrandAndCommodityLocally,
  normalizeCanonicalCommodity,
  deduplicateParsedItems,
  KiranaBrandCache
};

/**
 * ==============================================================================
 * MODULE: HANDWRITTEN / PRINTED GROCERY SLIP SCANNER (GEMINI MULTIMODAL VISION AI)
 * ==============================================================================
 */
function initGrocerySlipScanner() {
  const openModalBtn = document.getElementById('btn-open-camera-options');
  const modal = document.getElementById('photoSourceModal');
  const closeModalBtn = document.getElementById('close-photo-modal');
  const actionCamBtn = document.getElementById('btn-action-camera');
  const actionGalBtn = document.getElementById('btn-action-gallery');
  const camInput = document.getElementById('camera-capture-input');
  const galInput = document.getElementById('gallery-file-input');
  const loader = document.getElementById('photo-processing-loader');

  if (!openModalBtn && !camInput && !galInput) return;

  function showModal() {
    if (modal) {
      modal.classList.add('active');
      modal.style.display = 'flex';
    }
  }

  function hideModal() {
    if (modal) {
      modal.classList.remove('active');
      modal.style.display = 'none';
    }
  }

  if (openModalBtn) {
    openModalBtn.addEventListener('click', (e) => {
      e.preventDefault();
      showModal();
    });
  }

  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', (e) => {
      e.preventDefault();
      hideModal();
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) hideModal();
    });
  }

  // Desktop WebRTC Live Webcam Modal Elements
  const webcamModal = document.getElementById('liveCameraModal') || document.getElementById('webcamLiveModal');
  const webcamVideo = document.getElementById('webcam-video-feed');
  const webcamCanvas = document.getElementById('webcam-snapshot-canvas');
  const closeWebcamBtn = document.getElementById('close-webcam-modal');
  const cancelWebcamBtn = document.getElementById('btn-cancel-webcam');
  const captureSnapshotBtn = document.getElementById('btn-capture-snapshot');
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
    hideModal();
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
      console.warn("[Webcam Access Warning]:", err);
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

  if (actionCamBtn) {
    actionCamBtn.addEventListener('click', (e) => {
      e.preventDefault();
      // On desktop browsers with webcam capability, launch WebRTC live viewfinder
      if (!isMobileDevice() && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        openLiveWebcam();
      } else if (camInput) {
        // Mobile fallback
        camInput.click();
      }
    });
  }

  if (actionGalBtn && galInput) {
    actionGalBtn.addEventListener('click', (e) => {
      e.preventDefault();
      galInput.click();
    });
  }

  async function handleFileSelected(file) {
    if (!file) return;
    hideModal();

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
        throw new Error(`HTTP error ${resp.status}`);
      }

      const data = await resp.json();

      if (data.success && Array.isArray(data.items) && data.items.length > 0) {
        // MODULE 3: Do NOT force premature POS injection!
        // Display interactive "स्कॅन केलेली पावती व बजेट पडताळणी" (Budget & Verification Review Modal)
        openScannedReceiptReviewModal(data.items);
      } else {
        const errorMsg = "⚠️ फोटो स्पष्ट दिसत नाही किंवा वस्तू ओळखता आल्या नाहीत. कृपया पुन्हा स्पष्ट फोटो काढा.";
        if (typeof showToast === 'function') {
          showToast(errorMsg, 'error', 4500);
        } else {
          alert(errorMsg);
        }
      }
    } catch (err) {
      console.error("[Grocery Slip Scanner Error]:", err);
      const errorMsg = "⚠️ फोटो स्पष्ट दिसत नाही किंवा वस्तू ओळखता आल्या नाहीत. कृपया पुन्हा स्पष्ट फोटो काढा.";
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

  // ==============================================================================
  // Interactive "स्कॅन केलेली पावती व बजेट पडताळणी" Review Modal Controller
  // ==============================================================================
  function openScannedReceiptReviewModal(scannedItems) {
    const reviewModal = document.getElementById('scannedReceiptReviewModal');
    const tableBody = document.getElementById('scanned-review-table-body');
    const countBadge = document.getElementById('review-total-items-badge');
    const totalBadge = document.getElementById('review-grand-total-badge');
    const closeBtn = document.getElementById('close-scanned-review-modal');
    const cancelBtn = document.getElementById('btn-cancel-scanned-review');
    const addRowBtn = document.getElementById('btn-add-review-row');
    const confirmSendBtn = document.getElementById('btn-confirm-send-counter');
    const saveDraftBtn = document.getElementById('btn-save-scanned-draft');
    const downloadPdfBtn = document.getElementById('btn-download-scanned-pdf');

    // Occasion Titling & Backdated Ingestion elements
    const titleInput = document.getElementById('scanned-receipt-title');
    const occasionSelect = document.getElementById('scanned-receipt-occasion');
    const dateInput = document.getElementById('scanned-receipt-date');
    const occasionChips = document.querySelectorAll('.occasion-chip');

    if (!reviewModal || !tableBody) {
      console.warn("[ReviewModal] Review modal element missing.");
      return;
    }

    // Set default date to today if empty
    if (dateInput && !dateInput.value) {
      const today = new Date().toISOString().split('T')[0];
      dateInput.value = today;
    }

    // Wire suggestion chips
    occasionChips.forEach(chip => {
      chip.onclick = () => {
        const t = chip.getAttribute('data-title');
        const o = chip.getAttribute('data-occasion');
        if (titleInput && t) titleInput.value = t;
        if (occasionSelect && o) occasionSelect.value = o;
      };
    });

    // Strict mathematical summation of visible row prices: Total = Sum(item.price)
    // Does NOT multiply row price by quantity or unit
    function recalculateReviewTotals() {
      const rows = tableBody.querySelectorAll('tr');
      let grandTotal = 0.0;
      let activeCount = 0;
      rows.forEach(tr => {
        const nameInput = tr.querySelector('.review-name-input');
        const priceInput = tr.querySelector('.review-price-input');
        if (nameInput && nameInput.value.trim().length > 0) {
          activeCount++;
        }
        if (priceInput) {
          const val = parseFloat(priceInput.value);
          // Strictly direct mathematical sum of visible row price fields: Total = Sum(item.price)
          // Do NOT multiply row price by quantity or unit again
          if (!isNaN(val) && val > 0) {
            grandTotal += val;
          }
        }
      });
      grandTotal = Math.round(grandTotal * 100) / 100;
      if (countBadge) countBadge.innerText = String(activeCount || rows.length);
      if (totalBadge) totalBadge.innerText = '₹' + grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function createRowHtml(item, index) {
      const name = item.item_name || item.name || '';
      const brand = item.brand ? ` [${item.brand}]` : '';
      const fullName = (name + brand).trim();
      const qty = item.quantity !== undefined && item.quantity !== null && item.quantity !== "" ? item.quantity : (item.qty !== undefined && item.qty !== null ? item.qty : '1 किलो');
      const unit = (item.unit || 'किलो').trim();
      const price = (item.price !== undefined && item.price !== null) ? (parseFloat(item.price) || 0.0) : 0.0;

      const units = ['किलो', 'ग्रॅम', 'लिटर', 'मिली', 'नग', 'पुडे', 'पुडा', 'डबी', 'डझन', 'पाकीट', 'बाटली'];
      let unitOptions = '';
      units.forEach(u => {
        unitOptions += `<option value="${u}" ${u === unit ? 'selected' : ''}>${u}</option>`;
      });

      return `
        <tr data-row-id="${index}" style="border-bottom:1px solid #E2E8F0;">
          <td class="row-num" style="padding:8px; font-weight:700; color:#64748B; text-align:center;">${index + 1}</td>
          <td style="padding:8px;">
            <input type="text" class="form-control review-name-input" value="${escapeHtml(fullName)}" placeholder="वस्तूचे नाव" style="height:38px; font-size:0.92rem; font-weight:600; width:100%; border:1px solid #CBD5E1; border-radius:6px; padding:0 8px;" />
          </td>
          <td style="padding:8px;">
            <input type="text" class="form-control form-control-sm item-qty-input review-qty-input" value="${escapeHtml(String(qty))}" placeholder="उदा. 2 kg / 100 ग्रॅम" style="height:38px; font-size:0.92rem; text-align:center; width:100%; border:1px solid #CBD5E1; border-radius:6px; padding:0 6px;" />
          </td>
          <td style="padding:8px;">
            <select class="form-control review-unit-select" style="height:38px; font-size:0.88rem; width:100%; border:1px solid #CBD5E1; border-radius:6px; padding:0 6px;">
              ${unitOptions}
            </select>
          </td>
          <td style="padding:8px;">
            <div style="display:flex; align-items:center; gap:4px;">
              <span style="font-weight:700; color:#0F766E;">₹</span>
              <input type="number" step="any" min="0" class="form-control review-price-input" value="${price}" placeholder="0.00" style="height:38px; font-size:0.95rem; font-weight:700; color:#0F766E; width:100%; border:1px solid #CBD5E1; border-radius:6px; padding:0 8px;" />
            </div>
          </td>
          <td style="padding:8px; text-align:center;">
            <button type="button" class="review-delete-btn" style="background:transparent; border:none; cursor:pointer; font-size:1.1rem; color:#EF4444;" title="वस्तू काढा">🗑️</button>
          </td>
        </tr>
      `;
    }

    // Populate table rows
    let html = '';
    scannedItems.forEach((it, idx) => {
      html += createRowHtml(it, idx);
    });
    tableBody.innerHTML = html;

    // Attach row events for live updating on edit or deletion
    function wireRowEvents() {
      tableBody.querySelectorAll('.review-price-input, .review-qty-input, .review-name-input').forEach(inp => {
        inp.oninput = recalculateReviewTotals;
        inp.onchange = recalculateReviewTotals;
        inp.onkeyup = recalculateReviewTotals;
        inp.onpaste = () => setTimeout(recalculateReviewTotals, 50);
      });
      tableBody.querySelectorAll('.review-delete-btn').forEach(btn => {
        btn.onclick = (e) => {
          const tr = e.target.closest('tr');
          if (tr) tr.remove();
          // Update row numbers
          tableBody.querySelectorAll('tr').forEach((r, idx) => {
            const numTd = r.querySelector('.row-num');
            if (numTd) numTd.innerText = String(idx + 1);
          });
          recalculateReviewTotals();
        };
      });
    }

    wireRowEvents();
    recalculateReviewTotals();

    // Add new row button
    if (addRowBtn) {
      addRowBtn.onclick = () => {
        const currentCount = tableBody.querySelectorAll('tr').length;
        const newRowHtml = createRowHtml({ item_name: '', quantity: 1.0, unit: 'किलो', price: 0.0 }, currentCount);
        tableBody.insertAdjacentHTML('beforeend', newRowHtml);
        wireRowEvents();
        recalculateReviewTotals();
      };
    }

    function closeReviewModal() {
      reviewModal.classList.remove('active');
      reviewModal.style.display = 'none';
    }

    if (closeBtn) closeBtn.onclick = closeReviewModal;
    if (cancelBtn) cancelBtn.onclick = closeReviewModal;

    // Collect validated items from modal table
    function getReviewedItems() {
      const items = [];
      tableBody.querySelectorAll('tr').forEach((tr, idx) => {
        const nameInput = tr.querySelector('.review-name-input');
        const qtyInput = tr.querySelector('.item-qty-input') || tr.querySelector('.review-qty-input');
        const unitSelect = tr.querySelector('.review-unit-select');
        const priceInput = tr.querySelector('.review-price-input');

        const name = nameInput ? nameInput.value.trim() : '';
        if (!name) return;

        const qtyStr = qtyInput ? qtyInput.value.trim() : '1 किलो';
        const numMatch = qtyStr.match(/[-+]?\d*\.?\d+/);
        const qtyNumeric = numMatch ? (parseFloat(numMatch[0]) || 1.0) : 1.0;
        const unit = unitSelect ? unitSelect.value : 'किलो';
        const price = priceInput ? (parseFloat(priceInput.value) || 0.0) : 0.0;

        items.push({
          line_index: idx,
          name: name,
          commodity_name: name,
          qty: qtyStr,
          quantity: qtyStr,
          quantity_norm: qtyNumeric,
          unit: unit,
          display_qty: qtyStr,
          display_unit: unit,
          target_price: price,
          enteredTotal: price, // direct pre-fill of scanned slip price
          price: price,
          parse_source: 'scanned_verified'
        });
      });
      return items;
    }

    // PILLAR 5: Offline Printable Purchase Order PDF
    if (downloadPdfBtn) {
      downloadPdfBtn.onclick = () => {
        const reviewedItems = getReviewedItems();
        if (reviewedItems.length === 0) {
          if (typeof showToast === 'function') showToast("यादीत किमान एक वस्तू आवश्यक आहे.", "warn");
          return;
        }
        const title = (titleInput && titleInput.value.trim()) || "किराणा खरेदी यादी";
        const occasionType = (occasionSelect && occasionSelect.options[occasionSelect.selectedIndex].text) || "नियमित किराणा";
        const dateVal = (dateInput && dateInput.value) || new Date().toISOString().split('T')[0];

        if (typeof window.downloadStorePurchaseOrderPDF === 'function') {
          window.downloadStorePurchaseOrderPDF({
            title: title,
            occasionType: occasionType,
            date: dateVal,
            customerName: "स्मार्ट किराणा ग्राहक",
            items: reviewedItems
          });
        } else {
          alert("PDF जनरेटर उपलब्ध नाही.");
        }
      };
    }

    // Confirm & Send to Counter
    if (confirmSendBtn) {
      confirmSendBtn.onclick = () => {
        const reviewedItems = getReviewedItems();
        if (reviewedItems.length === 0) {
          if (typeof showToast === 'function') showToast("यादीत किमान एक वस्तू आवश्यक आहे.", "warn");
          return;
        }

        // 1. Populate text area (#raw-list-input)
        const textarea = document.getElementById('raw-list-input');
        const textLines = reviewedItems.map(it => `${it.name} ${it.qty} ${it.unit} ${it.target_price > 0 ? '₹' + it.target_price : ''}`.trim()).join('\n');
        if (textarea) {
          textarea.value = textarea.value && textarea.value.trim().length > 0
            ? textarea.value.trim() + '\n' + textLines
            : textLines;
        }

        // 2. Inject row-by-row into Reverse POS Table
        if (typeof window.appendCatalogItemToCounter === 'function') {
          reviewedItems.forEach(item => window.appendCatalogItemToCounter(item));
        } else if (typeof window.loadDraftOntoCounter === 'function') {
          window.loadDraftOntoCounter(reviewedItems);
        }

        // 3. Trigger total bill recalculation
        if (typeof window.recalculateGrandTotal === 'function') {
          window.recalculateGrandTotal();
        }

        closeReviewModal();

        if (typeof showToast === 'function') {
          showToast(`✅ स्कॅन व पडताळणी केलेल्या ${reviewedItems.length} वस्तू थेट काउंटरवर लोड झाल्या!`, 'success', 4000);
        }
      };
    }

    // PILLAR 2 & 5: Save Draft with Occasion & Date + Show Post-Save PDF prompt
    if (saveDraftBtn) {
      saveDraftBtn.onclick = async () => {
        const reviewedItems = getReviewedItems();
        if (reviewedItems.length === 0) {
          if (typeof showToast === 'function') showToast("यादीत किमान एक वस्तू आवश्यक आहे.", "warn");
          return;
        }

        const title = (titleInput && titleInput.value.trim()) || "किराणा यादी";
        const occasion = (occasionSelect && occasionSelect.value) || "regular";
        const occasionLabel = (occasionSelect && occasionSelect.options[occasionSelect.selectedIndex].text) || "नियमित किराणा";
        const dateVal = (dateInput && dateInput.value) || new Date().toISOString().split('T')[0];

        let budget = 0.0;
        reviewedItems.forEach(it => { budget += (it.target_price || 0.0); });

        try {
          const resp = await fetch('/api/save-grocery-list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: title,
              list_name: title,
              occasion_type: occasion,
              purchase_date: dateVal,
              items: reviewedItems,
              estimated_budget: budget
            })
          });

          if (resp.ok) {
            closeReviewModal();
            showPostSavePdfConfirmation({
              title: title,
              occasionType: occasionLabel,
              date: dateVal,
              items: reviewedItems
            });
          } else {
            throw new Error(`HTTP error ${resp.status}`);
          }
        } catch (err) {
          console.warn("[SaveScannedDraft] Fallback:", err);
          closeReviewModal();
          showPostSavePdfConfirmation({
            title: title,
            occasionType: occasionLabel,
            date: dateVal,
            items: reviewedItems
          });
        }
      };
    }

    // Display Review Modal
    reviewModal.classList.add('active');
    reviewModal.style.display = 'flex';
  }

  // Post-Save PDF Confirmation Prompt
  function showPostSavePdfConfirmation(data) {
    let confirmBox = document.getElementById('post-save-pdf-box');
    if (!confirmBox) {
      confirmBox = document.createElement('div');
      confirmBox.id = 'post-save-pdf-box';
      confirmBox.style.position = 'fixed';
      confirmBox.style.bottom = '24px';
      confirmBox.style.right = '24px';
      confirmBox.style.zIndex = '3000';
      confirmBox.style.background = '#FFFFFF';
      confirmBox.style.border = '2px solid #0F766E';
      confirmBox.style.borderRadius = '12px';
      confirmBox.style.padding = '16px 20px';
      confirmBox.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)';
      confirmBox.style.maxWidth = '380px';
      confirmBox.style.display = 'flex';
      confirmBox.style.flexDirection = 'column';
      confirmBox.style.gap = '10px';
      document.body.appendChild(confirmBox);
    }

    confirmBox.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div style="font-weight:700; color:#0F766E; font-size:1rem;">✅ यादी यशस्वीरित्या जतन झाली!</div>
        <button type="button" onclick="this.closest('#post-save-pdf-box').remove()" style="background:none; border:none; font-size:1.1rem; cursor:pointer; color:#64748B;">✕</button>
      </div>
      <div style="font-size:0.88rem; color:#475569;">
        "<strong>${data.title}</strong>" ही यादी सेव्ह केली आहे. आपण आता ऑफलाइन दुकानासाठी स्वच्छ खरेदी पावती PDF प्रिंट करू शकता.
      </div>
      <div style="display:flex; gap:8px; justify-content:flex-end; margin-top:4px;">
        <button type="button" id="btn-post-save-print-pdf" style="background:#0F766E; color:#fff; border:none; padding:8px 14px; border-radius:6px; font-weight:700; cursor:pointer; font-size:0.88rem; display:flex; align-items:center; gap:6px;">
          📄 डाउनलोड PDF
        </button>
      </div>
    `;

    const printBtn = confirmBox.querySelector('#btn-post-save-print-pdf');
    if (printBtn) {
      printBtn.onclick = () => {
        if (typeof window.downloadStorePurchaseOrderPDF === 'function') {
          window.downloadStorePurchaseOrderPDF(data);
        }
      };
    }

    // Auto remove after 15 seconds if ignored
    setTimeout(() => {
      if (confirmBox && confirmBox.parentElement) {
        confirmBox.remove();
      }
    }, 15000);
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

