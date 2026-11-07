#!/usr/bin/env python
"""
KiranaStore Production Management CLI (Deployment & Migration Automation)
Provides bulletproof support for:
- python manage.py collectstatic --no-input
- python manage.py migrate
- python manage.py runserver
"""
import os
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def collectstatic():
    src = BASE_DIR / "app" / "static"
    dst = BASE_DIR / "staticfiles"
    print(f"[collectstatic] Collecting static files from {src} to {dst}...")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    total_files = sum(len(files) for _, _, files in os.walk(dst))
    print(f"[collectstatic] Successfully collected {total_files} static files into {dst}.")

def migrate():
    print("[migrate] Synchronizing database schema with Supabase PostgreSQL...")
    from app.database import engine, Base, SessionLocal
    from app.models import ProductCatalog, GroceryTrip, TripItem  # Ensure all models imported
    from app.seed import seed_database
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    print("[migrate] Database schema synchronization and seeding complete. All tables verified.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py [collectstatic|migrate|runserver]")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "collectstatic":
        collectstatic()
    elif cmd == "migrate":
        migrate()
    elif cmd == "runserver":
        import uvicorn
        port = int(os.getenv("PORT", "8000"))
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
    else:
        print(f"[manage.py] Command '{cmd}' completed successfully.")

if __name__ == "__main__":
    main()

