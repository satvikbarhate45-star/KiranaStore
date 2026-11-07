import sys
import uvicorn
from app.config import settings

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("============================================================")
    print(f"  Smart Kirana Enterprise ({settings.APP_NAME_MR}) v{settings.VERSION}")
    print(f"  Server starting at: http://{settings.HOST}:{settings.PORT}")
    print("  Engine: Local Deterministic Parser (Zero External Calls)")
    print("============================================================")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
