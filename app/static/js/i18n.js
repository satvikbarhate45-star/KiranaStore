/**
 * Smart Kirana Enterprise - Marathi i18n & Currency Formatting Tokens
 */

const MR_I18N = {
  appName: "स्मार्ट किराणा",
  version: "v1.1",
  currency: "₹",
  
  // Status Pills
  balanced: "संतुलित",
  surge: "भाववाढ",
  dip: "स्वस्त",
  newEntry: "नवीन नोंद",

  // Basket Status
  balancedBudget: "संतुलित बजेट",
  unbalancedSpend: "असंतुलित खर्च",

  // Units
  units: {
    kg: "किलो",
    L: "लिटर",
    pcs: "नग",
    dozen: "डझन"
  },

  // Messages
  onlineMode: "ऑनलाइन",
  offlineMode: "ऑफलाइन मोड",
  verifyingList: "यादी तपासली जात आहे...",
  fallbackNotice: "स्मार्ट सुधारणा उपलब्ध नाही, साधा पार्सर वापरला आहे.",
  enterAmount: "कृपया योग्य रक्कम टाका",
  zeroAmountError: "रक्कम शून्य असू शकत नाही",
  confirmDelete: "ही खरेदी इतिहासामधून कायमची हटवायची आहे का?"
};

// Formats a numeric value into Indian currency format: ₹1,23,456.50
function formatINR(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return "₹0.00";
  }
  return "₹" + Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

// Formats quantity: 1.5 किलो, 0.5 किलो
function formatQty(qty, unit) {
  const displayUnit = MR_I18N.units[unit] || unit || "युनिट";
  return `${Number(qty)} ${displayUnit}`;
}
