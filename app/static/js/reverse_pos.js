/**
 * KiranaStore Enterprise Reverse POS Billing Engine (SSOT)
 * Single Source of Truth for counter reverse billing math:
 * - Counter merchant inputs only 'एकूण रक्कम ₹' (line_total)
 * - System dynamically derives unit_base_rate = line_total / normalized_quantity
 * - Rate is strictly formatted as ₹{rate}/किलो, ₹{rate}/ली, or ₹{rate}/unit
 * - Eliminates independent or ad-hoc client-side divisions
 */

const ReversePOS = {
  DEV_DIGITS: {
    '०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'
  },

  toAsciiDigits: function(text) {
    if (!text) return "";
    let clean = String(text);
    for (const [d, a] of Object.entries(this.DEV_DIGITS)) {
      clean = clean.split(d).join(a);
    }
    return clean;
  },

  /**
   * Normalizes physical quantity without truncation.
   * e.g., 250 gm -> 0.25 kg, 500 ml -> 0.5 L
   */
  normalizeQuantity: function(quantityVal, unitStr) {
    let cleanUnit = (unitStr || '').trim().toLowerCase();
    let q = parseFloat(quantityVal);
    if (isNaN(q) || q <= 0) {
      q = 1.0;
    }

    // Mass: grams -> kilograms
    if (cleanUnit === 'gm' || cleanUnit === 'g' || cleanUnit === 'ग्रॅम' || cleanUnit === 'ग्राम') {
      return {
        normalizedQuantity: parseFloat((q / 1000.0).toFixed(4)),
        baseUnit: 'किलो',
        displayUnit: q < 1000 ? 'ग्रॅम' : 'किलो',
        rawQuantity: q
      };
    }

    // Volume: milliliters -> liters
    if (cleanUnit === 'ml' || cleanUnit === 'मिली') {
      return {
        normalizedQuantity: parseFloat((q / 1000.0).toFixed(4)),
        baseUnit: 'ली',
        displayUnit: q < 1000 ? 'मिली' : 'ली',
        rawQuantity: q
      };
    }

    // Standard metric units
    if (cleanUnit === 'kg' || cleanUnit === 'किलो' || cleanUnit === 'kilo') {
      return {
        normalizedQuantity: q,
        baseUnit: 'किलो',
        displayUnit: 'किलो',
        rawQuantity: q
      };
    }

    if (cleanUnit === 'l' || cleanUnit === 'लिटर' || cleanUnit === 'ली' || cleanUnit === 'ltr') {
      return {
        normalizedQuantity: q,
        baseUnit: 'ली',
        displayUnit: 'ली',
        rawQuantity: q
      };
    }

    // Discrete countable units
    return {
      normalizedQuantity: q,
      baseUnit: unitStr || 'नग',
      displayUnit: unitStr || 'नग',
      rawQuantity: q
    };
  },

  /**
   * Reverse calculates unit rate from entered gross total.
   * Formula: unit_base_rate = line_total / normalized_quantity
   */
  calculateUnitRate: function(lineTotal, quantityVal, unitStr) {
    const total = parseFloat(lineTotal) || 0.0;
    const { normalizedQuantity, baseUnit, displayUnit, rawQuantity } = this.normalizeQuantity(quantityVal, unitStr);

    if (total <= 0 || normalizedQuantity <= 0) {
      return {
        lineTotal: 0.0,
        normalizedQuantity: normalizedQuantity,
        unitBaseRate: 0.0,
        baseUnit: baseUnit,
        displayUnit: displayUnit,
        formattedRate: '—'
      };
    }

    const rate = Math.round((total / normalizedQuantity) * 100) / 100;
    const formatted = `₹${rate.toFixed(2)}/${baseUnit}`;

    return {
      lineTotal: total,
      normalizedQuantity: normalizedQuantity,
      unitBaseRate: rate,
      baseUnit: baseUnit,
      displayUnit: displayUnit,
      formattedRate: formatted
    };
  }
};

window.ReversePOS = ReversePOS;

