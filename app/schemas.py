from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

# Ingestion & Parsing Schemas
class ParseListRequest(BaseModel):
    session_id: Optional[str] = None
    raw_text: Optional[str] = ""
    raw_items: Optional[List[str]] = None
    client_catalog_version: Optional[str] = "2026-10-20.1"
    mode: Optional[str] = "auto"  # 'auto' or 'local_only'

class PipelineMetadata(BaseModel):
    source: str  # 'gemini' | 'regex' | 'manual'
    model: str
    prompt_version: str
    latency_ms: int
    degraded: bool
    degrade_reason: Optional[str] = None
    ai_fallback: bool = False
    ai_active: bool = False

class ParsedItem(BaseModel):
    line_index: int
    sku_id: Optional[int] = None
    name: str
    qty: Any
    unit: str  # 'gm', 'kg', 'L', 'ml', 'pcs', 'dozen', 'packet'
    display_qty: Optional[Any] = None
    display_unit: Optional[str] = "किलो"
    quantity_norm: Optional[float] = None
    canonical_unit: Optional[str] = "kg"
    confidence: float
    original_raw: str
    parse_source: str  # 'gemini' | 'regex' | 'manual'
    corrected: bool = False
    needs_review: bool = False
    status: str = "matched"  # 'matched' | 'unmatched' | 'provisional'
    baseline_rate: Optional[float] = None
    target_price: Optional[float] = None
    estimated_price: Optional[float] = None

class UnresolvedLine(BaseModel):
    line_index: int
    original_raw: str
    reason: str
    suggestions: List[str] = []

class ParseListResponse(BaseModel):
    session_id: str
    pipeline: PipelineMetadata
    items: List[ParsedItem]
    unresolved: List[UnresolvedLine] = []
    merged_duplicates: List[str] = []
    fallback_notice_mr: Optional[str] = None
    ai_fallback: bool = False
    ai_active: bool = False

# Trip Schemas
class TripItemCreate(BaseModel):
    sku_id: Optional[int] = None
    name: Optional[str] = None
    commodity_name: Optional[str] = None
    quantity_norm: Optional[float] = 1.0
    normalized_quantity: Optional[float] = None
    quantity: Optional[Union[str, float, int]] = None
    quantity_str: Optional[str] = None
    qty: Optional[Union[str, float, int]] = None
    unit: Optional[str] = "किलो"
    display_unit: Optional[str] = "किलो"
    line_total_amount: Optional[float] = None
    entered_total: Optional[float] = 0.0
    unit_base_rate: Optional[float] = None
    derived_rate: Optional[float] = 0.0
    price: Optional[float] = None
    target_price: Optional[float] = None
    baseline_rate: Optional[float] = None
    variance_pct: Optional[float] = None
    badge: Optional[str] = "संतुलित"
    raw_input: Optional[str] = None
    parse_source: Optional[str] = "regex"
    ai_confidence: Optional[float] = None

class TripCreate(BaseModel):
    session_id: Optional[str] = None
    merchant_vpa: Optional[str] = "store@upi"
    merchant_name: Optional[str] = "किराणा व्यावसायिक"
    settled_total: Optional[float] = 0.0
    title: Optional[str] = "नियमित किराणा"
    occasion_type: Optional[str] = "regular"  # 'regular', 'festive', 'guest_event', 'other'
    purchase_date: Optional[str] = None
    basket_variance: Optional[float] = None
    basket_status: Optional[str] = "संतुलित बजेट"
    status: Optional[str] = "settled"
    upi_ref: Optional[str] = None
    items: List[TripItemCreate] = []

class HistoricalBillItem(BaseModel):
    name: Optional[str] = None
    item_name: Optional[str] = None
    commodity_name: Optional[str] = None
    quantity: Optional[Union[str, float, int]] = "1 किलो"
    qty: Optional[Union[str, float, int]] = None
    unit: Optional[str] = "किलो"
    display_unit: Optional[str] = "किलो"
    price: Optional[float] = 0.0
    line_total_amount: Optional[float] = None
    entered_total: Optional[float] = 0.0
    normalized_quantity: Optional[float] = None
    unit_base_rate: Optional[float] = None
    derived_rate: Optional[float] = 0.0
    target_price: Optional[float] = 0.0

class SaveHistoricalBillRequest(BaseModel):
    title: Optional[str] = "मागील किराणा पावती"
    occasion_type: Optional[str] = "regular"
    purchase_date: Optional[str] = None
    merchant_name: Optional[str] = "किराणा पावती"
    merchant_vpa: Optional[str] = "store@upi"
    settled_total: Optional[float] = None
    items: List[HistoricalBillItem] = []

class TripItemResponse(BaseModel):
    item_id: int
    sku_id: int
    name: str
    quantity_norm: float
    normalized_quantity: Optional[float] = None
    quantity_str: Optional[str] = None
    unit: str
    display_unit: str
    line_total_amount: Optional[float] = None
    entered_total: float
    unit_base_rate: Optional[float] = None
    derived_rate: float
    baseline_rate: Optional[float] = None
    variance_pct: Optional[float] = None
    badge: str
    raw_input: Optional[str] = None
    parse_source: str
    ai_confidence: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class HistoryItemUpdateRequest(BaseModel):
    session_id: Optional[str] = None
    item_id: int
    quantity: str
    total_price: Optional[float] = None
    line_total_amount: Optional[float] = None
    unit_price: Optional[float] = None
    unit_base_rate: Optional[float] = None

class HistoryItemUpdateResponse(BaseModel):
    success: bool
    message: str
    item_id: int
    trip_id: Optional[int] = None
    session_id: Optional[str] = None
    quantity: str
    quantity_norm: float
    normalized_quantity: Optional[float] = None
    unit: str
    total_price: float
    line_total_amount: Optional[float] = None
    unit_price: float
    unit_base_rate: Optional[float] = None
    trip_settled_total: float

class TripResponse(BaseModel):
    trip_id: int
    session_id: str
    buyer_id: int
    merchant_vpa: str
    merchant_name: str
    title: Optional[str] = "नियमित किराणा"
    occasion_type: Optional[str] = "regular"
    purchase_date: Optional[str] = None
    trip_date: str
    settled_total: float
    basket_variance: Optional[float] = None
    basket_status: Optional[str] = None
    status: str
    upi_ref: Optional[str] = None
    items_count: int = 0
    items: Optional[List[TripItemResponse]] = None

    model_config = ConfigDict(from_attributes=True)

# Aliases for canonical enterprise endpoints
ReceiptCreate = TripCreate
ReceiptResponse = TripResponse

# Catalog Schemas
class AcceptAliasRequest(BaseModel):
    raw_text: str
    sku_id: int

# Contact & Support Schemas
class ContactCreate(BaseModel):
    name: str = Field(..., min_length=2)
    mobile: str = Field(..., min_length=10, max_length=15)
    category: str
    message: str = Field(..., min_length=5)

class ContactResponse(BaseModel):
    success: bool
    ticket_number: str
    message_mr: str

# Simulator Schemas
class SimulationItemInput(BaseModel):
    sku_id: int
    quantity: float
    manual_price: Optional[float] = None

class SimulatorRequest(BaseModel):
    items: List[SimulationItemInput]

SimulationRequest = SimulatorRequest

class SimulatedItemResult(BaseModel):
    sku_id: int
    marathi_name: str
    quantity: float
    unit: str
    display_unit: str
    baseline_unit_rate: Optional[float] = None
    estimated_total: Optional[float] = None
    confidence_range_low: Optional[float] = None
    confidence_range_high: Optional[float] = None
    has_history: bool = True
    manual_price_required: bool = False
    manual_price: Optional[float] = None

class SimulatorResponse(BaseModel):
    total_estimated: float
    total_range_low: float
    total_range_high: float
    items: List[SimulatedItemResult]
    has_missing_history: bool = False
    missing_items_count: int = 0
    notice_mr: Optional[str] = None

SimulationResponse = SimulatorResponse


# MODULE 2: Draft Grocery List Schemas
class DraftListCreate(BaseModel):
    session_id: Optional[str] = None
    title: Optional[str] = "किराणा यादी ड्राफ्ट"
    raw_text: Optional[str] = None
    items: List[Dict[str, Any]]

class DraftListResponse(BaseModel):
    draft_id: int
    session_id: str
    buyer_id: int
    title: str
    raw_text: Optional[str] = None
    total_items: int
    items: List[Dict[str, Any]]
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


# MODULE 3: Government & APMC Market Price Schemas
class MarketRateItem(BaseModel):
    commodity_name: str
    canonical_unit: str
    retail_modal_rate: float
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    source: str
    market_location: str
    last_updated: str
    is_live_grounded: bool = False

class MarketRatesResponse(BaseModel):
    state: str = "Maharashtra"
    source: str
    rates: List[MarketRateItem]


# MODULE 4: Closed-Loop 3-Way Comparative Variance & Audit Schemas
class ItemVarianceAudit(BaseModel):
    item_index: int
    name: str
    quantity: float
    unit: str
    govt_rate: float
    govt_amount: float
    shopkeeper_rate: float
    shopkeeper_amount: float
    fair_retail_rate: Optional[float] = None
    fair_retail_amount: Optional[float] = None
    margin_indicator: Optional[str] = None  # 'वाजवी दर (Fair Retail Price)' | 'अपेक्षित दरापेक्षा जास्त' | 'सवलत / उत्तम ऑफर (Good Deal)'
    margin_status: Optional[str] = None  # 'fair' | 'expensive' | 'deal'
    variance_amount: float
    variance_percentage: float
    remark: str  # 'महाग' | 'वाजवी दर' | 'बचत'

class Audit3WayRequest(BaseModel):
    session_id: Optional[str] = None
    items: List[Dict[str, Any]]
    shopkeeper_total: Optional[float] = None
    upi_settled_amount: Optional[float] = None

class Audit3WayResponse(BaseModel):
    session_id: str
    govt_total_amount: float
    fair_retail_total_amount: Optional[float] = None
    shopkeeper_total_amount: float
    upi_settled_amount: float
    total_variance_amount: float
    variance_percentage: float
    badge_label: str
    is_inflated: bool
    savings_amount: float
    items_breakdown: List[ItemVarianceAudit]

class TripAnalyticsCreate(BaseModel):
    session_id: str
    govt_total_amount: float
    shopkeeper_total_amount: float
    upi_settled_amount: float
    items_breakdown: Optional[List[Dict[str, Any]]] = None

class TripAnalyticsResponse(BaseModel):
    analytics_id: int
    session_id: str
    govt_total_amount: float
    shopkeeper_total_amount: float
    upi_settled_amount: float
    total_variance_amount: float
    variance_percentage: float
    items_breakdown: List[Dict[str, Any]]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


# MODULE 5: Persistent Saved Grocery Lists Schemas
class SavedListCreate(BaseModel):
    list_name: str = "माझी किराणा यादी"
    total_items: Optional[int] = 0
    estimated_budget: Optional[float] = 0.0
    items: List[Dict[str, Any]] = []

class SavedListResponse(BaseModel):
    id: int
    list_name: str
    created_at: str
    total_items: int
    estimated_budget: float
    items: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


# MODULE 6: Festival Surge Predictor & Bulk Stocking Advice Schemas
class FestivalSurgeAdvice(BaseModel):
    festival_name: str
    days_until: int
    is_active_window: bool
    affected_commodities: List[str]
    advice_card_mr: str
    estimated_savings_min: float
    estimated_savings_max: float
    surge_details: List[Dict[str, Any]]


# MODULE 2: Retail Margin Pricing Engine Schemas
class RetailMarginAnalysis(BaseModel):
    commodity_name: str
    mandi_base_rate: float
    fair_retail_baseline: float
    billed_rate: float
    variance: float
    margin_indicator: str
    badge_color: str
    status: str


# DYNAMIC COMMODITY 3-WAY AUDIT PREDICTION SCHEMAS
class CommodityAuditPredictionResponse(BaseModel):
    commodity_name: str
    canonical_unit: str
    quantity: float
    is_historical: bool
    historical_sessions_count: int = 0
    notice_mr: Optional[str] = None
    govt_rate: float
    govt_total_amount: float
    fair_retail_rate: float
    fair_retail_total_amount: float
    shopkeeper_rate: float
    shopkeeper_total_amount: float
    upi_settled_rate: float
    upi_settled_total_amount: float
    total_variance_amount: float
    variance_percentage: float
    margin_indicator: str
    margin_status: str
    badge_label: str
    is_inflated: bool
    savings_amount: float
    grounding_source: str
    historical_records: List[Dict[str, Any]] = []



