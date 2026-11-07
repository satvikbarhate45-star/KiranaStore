import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class ProductCatalog(Base):
    __tablename__ = "product_catalog"

    sku_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    canonical_name = Column(String(255), unique=True, nullable=False, index=True)
    marathi_name = Column(String(255), unique=True, nullable=False, index=True)
    aliases = Column(JSON, nullable=False, default=list)  # list of strings: ["सक्कर", "sakhar", "sugar"]
    canonical_unit = Column(String(32), nullable=False)   # 'kg', 'L', 'pcs', 'dozen'
    category = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    trip_items = relationship("TripItem", back_populates="product")
    candidates = relationship("AliasCandidate", back_populates="product")


class GroceryTrip(Base):
    __tablename__ = "grocery_trips"

    trip_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    buyer_id = Column(Integer, nullable=False, default=1, index=True)
    title = Column(String(255), nullable=True, default="नियमित किराणा")
    occasion_type = Column(String(64), nullable=False, default="regular")  # 'regular', 'festive', 'guest_event', 'other'
    purchase_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    merchant_vpa = Column(String(255), nullable=True, default="store@upi")
    merchant_name = Column(String(255), nullable=True, default="किराणा पावती")
    trip_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    settled_total = Column(Float, nullable=False)
    basket_variance = Column(Float, nullable=True)
    basket_status = Column(String(64), nullable=True)  # 'संतुलित बजेट' / 'असंतुलित खर्च'
    status = Column(String(32), default="settled", nullable=False)  # 'draft', 'audited', 'settled', 'abandoned'
    upi_ref = Column(String(128), nullable=True)

    items = relationship("TripItem", back_populates="trip", cascade="all, delete-orphan")


class TripItem(Base):
    __tablename__ = "trip_items"

    item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("grocery_trips.trip_id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id = Column(Integer, ForeignKey("product_catalog.sku_id"), nullable=False, index=True)

    # Core Separated Financial & Measurement Attributes (Strict Non-Null Numeric)
    line_total_amount = Column(Float, nullable=False, default=0.0)
    normalized_quantity = Column(Float, nullable=False, default=1.0)
    unit_base_rate = Column(Float, nullable=False, default=0.0)

    # Parallel attributes maintained for 100% backward compatibility
    quantity_norm = Column(Float, nullable=False, default=1.0)
    quantity_str = Column(String(64), nullable=True)
    unit = Column(String(32), nullable=False)  # 'kg', 'L', 'pcs', 'dozen'
    entered_total = Column(Float, nullable=False, default=0.0)
    derived_rate = Column(Float, nullable=False, default=0.0)

    baseline_rate = Column(Float, nullable=True)
    variance_pct = Column(Float, nullable=True)
    badge = Column(String(64), nullable=True, default="संतुलित")  # 'संतुलित', 'भाववाढ', 'स्वस्त', 'नवीन नोंद'
    raw_input = Column(String(255), nullable=True)
    parse_source = Column(String(32), default="regex", nullable=False)  # 'gemini', 'regex', 'manual'
    ai_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    trip = relationship("GroceryTrip", back_populates="items")
    product = relationship("ProductCatalog", back_populates="trip_items")

    def __init__(self, **kwargs):
        # Synchronize line_total, line_total_amount, and entered_total
        total = kwargs.get("line_total")
        if total is None:
            total = kwargs.get("line_total_amount")
        if total is None:
            total = kwargs.get("entered_total")
        if total is not None:
            kwargs["line_total_amount"] = float(total)
            kwargs["entered_total"] = float(total)

        # Synchronize base_quantity, normalized_quantity and quantity_norm
        qty = kwargs.get("base_quantity")
        if qty is None:
            qty = kwargs.get("normalized_quantity")
        if qty is None:
            qty = kwargs.get("quantity_norm")
        if qty is not None:
            kwargs["normalized_quantity"] = float(qty)
            kwargs["quantity_norm"] = float(qty)

        # Synchronize display_unit and unit
        u = kwargs.get("display_unit") or kwargs.get("unit") or "किलो"
        kwargs["unit"] = str(u)

        # Synchronize unit_base_rate, base_rate, and derived_rate
        rate = kwargs.get("unit_base_rate")
        if rate is None:
            rate = kwargs.get("base_rate")
        if rate is None:
            rate = kwargs.get("derived_rate")
        if rate is None and total is not None and qty is not None and float(qty) > 0:
            rate = round(float(total) / float(qty), 4)
        if rate is not None:
            kwargs["unit_base_rate"] = float(rate)
            kwargs["derived_rate"] = float(rate)

        super().__init__(**kwargs)

    @property
    def line_total(self) -> float:
        return self.line_total_amount if self.line_total_amount is not None else self.entered_total

    @line_total.setter
    def line_total(self, val: float):
        f_val = float(val or 0.0)
        self.line_total_amount = f_val
        self.entered_total = f_val

    @property
    def base_quantity(self) -> float:
        return self.normalized_quantity if self.normalized_quantity is not None else self.quantity_norm

    @base_quantity.setter
    def base_quantity(self, val: float):
        f_val = float(val or 1.0)
        self.normalized_quantity = f_val
        self.quantity_norm = f_val

    @property
    def display_unit(self) -> str:
        return self.unit

    @display_unit.setter
    def display_unit(self, val: str):
        self.unit = str(val or "किलो")


class VolatilityConfig(Base):
    __tablename__ = "volatility_config"

    id = Column(Integer, primary_key=True, default=1)
    balanced_abs = Column(Float, default=5.0, nullable=False)
    surge_gt = Column(Float, default=6.0, nullable=False)
    dip_lt = Column(Float, default=-2.0, nullable=False)
    median_window = Column(Integer, default=5, nullable=False)


class AIPartseAudit(Base):
    __tablename__ = "ai_parse_audit"

    audit_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    model = Column(String(128), nullable=False)
    prompt_version = Column(String(64), nullable=False)
    latency_ms = Column(Integer, nullable=False)
    outcome = Column(String(32), nullable=False)  # 'ok', 'degraded', 'rejected'
    degrade_reason = Column(String(128), nullable=True)
    lines_in = Column(Integer, nullable=False)
    items_out = Column(Integer, nullable=False)
    validator_fails = Column(JSON, default=dict, nullable=False)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class AliasCandidate(Base):
    __tablename__ = "alias_candidates"

    candidate_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    raw_text = Column(String(255), nullable=False)
    suggested_sku = Column(Integer, ForeignKey("product_catalog.sku_id"), nullable=True)
    times_seen = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default="pending", nullable=False)  # 'pending', 'approved', 'rejected'
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    product = relationship("ProductCatalog", back_populates="candidates")


class SupportLog(Base):
    __tablename__ = "support_logs"

    inquiry_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_number = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    mobile = Column(String(32), nullable=False)
    category = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(32), default="open", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class DraftGroceryList(Base):
    """
    MODULE 2: Persistent Offline/Online Draft Storage.
    Stores verified lists so users can prepare at home and restore at the shop counter.
    """
    __tablename__ = "draft_grocery_lists"

    draft_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=False)
    buyer_id = Column(Integer, nullable=False, default=1, index=True)
    title = Column(String(255), default="किराणा यादी ड्राफ्ट", nullable=False)
    raw_text = Column(Text, nullable=True)
    items_json = Column(JSON, nullable=False, default=list)
    total_items = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)


class CachedCommodityPrice(Base):
    """
    MODULE 3: Zero-KYC APMC and Government Benchmark Rate Cache with 12-hour TTL.
    """
    __tablename__ = "cached_commodity_prices"

    cache_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    commodity_name = Column(String(128), unique=True, index=True, nullable=False)
    canonical_unit = Column(String(32), default="kg", nullable=False)
    retail_modal_rate = Column(Float, nullable=False)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    source = Column(String(64), default="apmc_local", nullable=False)  # 'apmc_local' | 'gemini_search_grounding'
    market_location = Column(String(128), default="Maharashtra Modal Retail", nullable=False)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class KiranaTripAnalytics(Base):
    """
    MODULE 4: Closed-Loop 3-Way Comparative Price Variance and Settlement Audit.
    Stores Govt expected vs Shopkeeper counter vs UPI settled amounts and line-item variances.
    """
    __tablename__ = "kirana_trip_analytics"

    analytics_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    buyer_id = Column(Integer, default=1, nullable=False, index=True)
    govt_total_amount = Column(Float, nullable=False)
    shopkeeper_total_amount = Column(Float, nullable=False)
    upi_settled_amount = Column(Float, nullable=False)
    total_variance_amount = Column(Float, nullable=False)  # shopkeeper_total - govt_total
    variance_percentage = Column(Float, nullable=False)
    items_breakdown = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True, nullable=False)


class SavedGroceryList(Base):
    """
    MODULE 5: Persistent Saved Grocery Lists ("सेव्ह केलेल्या याद्या").
    Stores confirmed grocery lists with estimated budget and line items payload.
    """
    __tablename__ = "saved_grocery_lists"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    list_name = Column(String(255), nullable=False, default="माझी किराणा यादी")
    title = Column(String(255), nullable=True, default="माझी किराणा यादी")
    occasion_type = Column(String(64), nullable=False, default="regular")  # 'regular', 'festive', 'guest_event', 'other'
    purchase_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    total_items = Column(Integer, nullable=False, default=0)
    estimated_budget = Column(Float, nullable=True, default=0.0)
    items_payload = Column(JSON, nullable=False, default=list)


# Canonical Enterprise Model Aliases (Pillar 1 & 2)
Receipt = GroceryTrip
ReceiptItem = TripItem
GroceryList = SavedGroceryList


