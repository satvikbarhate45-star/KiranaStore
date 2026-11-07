import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import (
    Base, ProductCatalog, GroceryTrip, TripItem, VolatilityConfig,
    AIPartseAudit, AliasCandidate, SupportLog, DraftGroceryList,
    CachedCommodityPrice, KiranaTripAnalytics, SavedGroceryList
)

def serialize_val(val):
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    return val

def model_to_dict(obj):
    res = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        res[col.name] = serialize_val(val)
    return res

def dump_all_sqlite(sqlite_path="sqlite:///kirana.db", output_file="backup.json"):
    engine = create_engine(sqlite_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    models_order = [
        ("volatility_config", VolatilityConfig),
        ("cached_commodity_prices", CachedCommodityPrice),
        ("support_logs", SupportLog),
        ("ai_parse_audit", AIPartseAudit),
        ("draft_grocery_lists", DraftGroceryList),
        ("saved_grocery_lists", SavedGroceryList),
        ("product_catalog", ProductCatalog),
        ("alias_candidates", AliasCandidate),
        ("grocery_trips", GroceryTrip),
        ("trip_items", TripItem),
        ("kirana_trip_analytics", KiranaTripAnalytics),
    ]

    backup_data = {}
    total_records = 0

    print("--- DUMPING SQLITE DATA ---")
    for table_name, model in models_order:
        rows = session.query(model).all()
        table_records = [model_to_dict(r) for r in rows]
        backup_data[table_name] = table_records
        count = len(table_records)
        total_records += count
        print(f"Table '{table_name}': {count} records exported")

    session.close()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)

    print(f"\nSuccessfully wrote {total_records} total records to {output_file}")
    return total_records

if __name__ == "__main__":
    dump_all_sqlite()

