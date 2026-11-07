import json
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import (
    Base, ProductCatalog, GroceryTrip, TripItem, VolatilityConfig,
    AIPartseAudit, AliasCandidate, SupportLog, DraftGroceryList,
    CachedCommodityPrice, KiranaTripAnalytics, SavedGroceryList
)

SUPABASE_URL = "postgresql://postgres.qpmbydosjurxxicdjbeg:Kirana%40Store1@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

def parse_iso_datetime(val):
    if not val or not isinstance(val, str):
        return val
    try:
        # Handle ISO strings
        return datetime.datetime.fromisoformat(val)
    except Exception:
        try:
            return datetime.datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return val

def restore_from_json(json_file="backup.json"):
    print(f"Reading backup data from {json_file}...")
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    engine = create_engine(SUPABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    models_order = [
        ("volatility_config", VolatilityConfig, "id"),
        ("cached_commodity_prices", CachedCommodityPrice, "cache_id"),
        ("support_logs", SupportLog, "inquiry_id"),
        ("ai_parse_audit", AIPartseAudit, "audit_id"),
        ("draft_grocery_lists", DraftGroceryList, "draft_id"),
        ("saved_grocery_lists", SavedGroceryList, "id"),
        ("product_catalog", ProductCatalog, "sku_id"),
        ("alias_candidates", AliasCandidate, "candidate_id"),
        ("grocery_trips", GroceryTrip, "trip_id"),
        ("trip_items", TripItem, "item_id"),
        ("kirana_trip_analytics", KiranaTripAnalytics, "analytics_id"),
    ]

    datetime_cols = {
        "created_at", "updated_at", "purchase_date", "trip_date", "last_updated", "expires_at"
    }

    print("\n--- RESTORING DATA TO SUPABASE POSTGRESQL ---")
    for table_name, model_cls, pk_col in models_order:
        records = data.get(table_name, [])
        if not records:
            print(f"Table '{table_name}': 0 records in backup, skipping.")
            continue

        # Check existing count in Supabase
        existing_count = session.query(model_cls).count()
        if existing_count > 0:
            print(f"Table '{table_name}' already contains {existing_count} records. Skipping restore to avoid duplicates.")
            continue

        instances = []
        for rec in records:
            cleaned = {}
            for k, v in rec.items():
                if k in datetime_cols and v is not None:
                    cleaned[k] = parse_iso_datetime(v)
                else:
                    cleaned[k] = v
            instances.append(model_cls(**cleaned))

        session.bulk_save_objects(instances)
        session.commit()
        print(f"[OK] Table '{table_name}': Successfully inserted {len(instances)} rows.")

        # Reset Postgres sequence for PK
        try:
            seq_query = text(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', '{pk_col}'),
                    COALESCE((SELECT MAX({pk_col}) FROM {table_name}), 1)
                );
            """)
            session.execute(seq_query)
            session.commit()
            print(f"     Reset sequence for '{table_name}.{pk_col}'")
        except Exception as e:
            session.rollback()
            print(f"     [Sequence Notice for {table_name}.{pk_col}]: {e}")

    session.close()

    # Verification Query
    print("\n--- VERIFYING SUPABASE ROW COUNTS ---")
    session = Session()
    for table_name, model_cls, _ in models_order:
        count = session.query(model_cls).count()
        print(f"Supabase Table '{table_name}': {count} rows")
    session.close()
    print("\nData migration and sequence reset completed successfully!")

if __name__ == "__main__":
    restore_from_json()

