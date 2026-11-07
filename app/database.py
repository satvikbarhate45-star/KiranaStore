import os
import json
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Engine configuration
db_url = settings.get_database_url()
connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine_kwargs["connect_args"] = connect_args
elif "postgres" in db_url:
    connect_args = {
        "sslmode": "require",
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
    engine_kwargs["connect_args"] = connect_args
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_timeout"] = 15

engine = create_engine(db_url, **engine_kwargs)

# Enable foreign keys and WAL mode for SQLite
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

def run_sqlite_migrations(eng):
    """
    Automatic Schema Migrations for Pillars 1 & 2:
    Adds title, occasion_type, and purchase_date to receipts and grocery list tables.
    """
    try:
        insp = inspect(eng)
        tables = insp.get_table_names()
        
        if "grocery_trips" in tables:
            cols = [c["name"] for c in insp.get_columns("grocery_trips")]
            with eng.connect() as conn:
                if "title" not in cols:
                    conn.execute(text("ALTER TABLE grocery_trips ADD COLUMN title VARCHAR(255) DEFAULT 'नियमित किराणा'"))
                if "occasion_type" not in cols:
                    conn.execute(text("ALTER TABLE grocery_trips ADD COLUMN occasion_type VARCHAR(64) DEFAULT 'regular'"))
                if "purchase_date" not in cols:
                    conn.execute(text("ALTER TABLE grocery_trips ADD COLUMN purchase_date TIMESTAMP"))
                conn.commit()

        if "saved_grocery_lists" in tables:
            cols = [c["name"] for c in insp.get_columns("saved_grocery_lists")]
            with eng.connect() as conn:
                if "title" not in cols:
                    conn.execute(text("ALTER TABLE saved_grocery_lists ADD COLUMN title VARCHAR(255) DEFAULT 'माझी किराणा यादी'"))
                if "occasion_type" not in cols:
                    conn.execute(text("ALTER TABLE saved_grocery_lists ADD COLUMN occasion_type VARCHAR(64) DEFAULT 'regular'"))
                if "purchase_date" not in cols:
                    conn.execute(text("ALTER TABLE saved_grocery_lists ADD COLUMN purchase_date TIMESTAMP"))
                conn.commit()

        if "trip_items" in tables:
            cols = [c["name"] for c in insp.get_columns("trip_items")]
            with eng.connect() as conn:
                if "quantity_str" not in cols:
                    conn.execute(text("ALTER TABLE trip_items ADD COLUMN quantity_str VARCHAR(64)"))
                if "line_total_amount" not in cols:
                    conn.execute(text("ALTER TABLE trip_items ADD COLUMN line_total_amount FLOAT DEFAULT 0.0"))
                if "normalized_quantity" not in cols:
                    conn.execute(text("ALTER TABLE trip_items ADD COLUMN normalized_quantity FLOAT DEFAULT 1.0"))
                if "unit_base_rate" not in cols:
                    conn.execute(text("ALTER TABLE trip_items ADD COLUMN unit_base_rate FLOAT DEFAULT 0.0"))
                
                # Internal Migration: Synchronize & re-parse all existing records into discrete fields
                conn.execute(text("""
                    UPDATE trip_items 
                    SET line_total_amount = entered_total 
                    WHERE (line_total_amount IS NULL OR line_total_amount = 0.0) AND entered_total IS NOT NULL AND entered_total > 0
                """))
                conn.execute(text("""
                    UPDATE trip_items 
                    SET normalized_quantity = quantity_norm 
                    WHERE (normalized_quantity IS NULL OR normalized_quantity = 0.0) AND quantity_norm IS NOT NULL AND quantity_norm > 0
                """))
                conn.execute(text("""
                    UPDATE trip_items 
                    SET unit_base_rate = derived_rate 
                    WHERE (unit_base_rate IS NULL OR unit_base_rate = 0.0) AND derived_rate IS NOT NULL AND derived_rate > 0
                """))
                conn.execute(text("""
                    UPDATE trip_items 
                    SET unit_base_rate = ROUND(line_total_amount / normalized_quantity, 4)
                    WHERE (unit_base_rate IS NULL OR unit_base_rate = 0.0) 
                      AND normalized_quantity IS NOT NULL 
                      AND normalized_quantity > 0 
                      AND line_total_amount IS NOT NULL
                """))
                conn.commit()
    except Exception as e:
        print("[Database Migrations Warning]:", e)

# Run migrations on startup for SQLite
if db_url.startswith("sqlite"):
    run_sqlite_migrations(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_historical_sanitization(db: Session = None):
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True
    try:
        from app.services.history_service import sanitize_historical_database
        res = sanitize_historical_database(db)
        print(f"[Historical Sanitization Success]: {res}")
        return res
    except Exception as e:
        print("[Historical Sanitization Startup Warning]:", e)
        return None
    finally:
        if close_after:
            db.close()
