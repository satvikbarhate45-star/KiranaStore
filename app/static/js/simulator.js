/**
 * KiranaStore Enterprise Budget Simulator Engine (SSOT)
 * Single Source of Truth for frontend simulation math:
 * - Projected Item Cost = requested_quantity * unit_base_rate
 * - Total Simulated Budget = sum(projected_item_costs)
 * - Display badge "मागील दर: ₹{unit_base_rate}/किलो" (or per base unit)
 */

const BudgetSimulator = {
  /**
   * Computes clean projection for a single line item
   */
  calculateLineProjection: function(quantity, unitBaseRate) {
    const q = parseFloat(quantity) || 0.0;
    const rate = parseFloat(unitBaseRate) || 0.0;
    if (q <= 0 || rate <= 0) {
      return {
        projectedCost: null,
        rangeLow: null,
        rangeHigh: null
      };
    }
    const cost = Math.round(q * rate * 100) / 100;
    const low = Math.round(cost * 0.95 * 100) / 100;
    const high = Math.round(cost * 1.07 * 100) / 100;
    return {
      projectedCost: cost,
      rangeLow: low,
      rangeHigh: high
    };
  },

  /**
   * Asynchronously calls the simulator endpoint
   */
  simulate: async function(itemsPayload, buyerId = 1) {
    const resp = await fetch('/api/v1/analyzer/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: itemsPayload,
        buyer_id: buyerId
      })
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "सिम्युलेशन अयशस्वी झाले.");
    }
    return await resp.json();
  },

  /**
   * Formats baseline rate badge text
   */
  formatBaselineBadge: function(unitBaseRate, displayUnit = 'किलो') {
    if (!unitBaseRate || unitBaseRate <= 0) return '— नवीन वस्तू';
    const cleanRate = parseFloat(unitBaseRate).toFixed(2);
    return `मागील दर: ₹${cleanRate}/${displayUnit}`;
  }
};

window.BudgetSimulator = BudgetSimulator;

