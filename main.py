import os
import json
import random
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="SneakPeak API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load mock sneaker dataset once
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'sneakers.json')
with open(DATA_PATH, 'r') as f:
    SNEAKERS = json.load(f)
SNEAKERS_BY_ID = {s['id']: s for s in SNEAKERS}

# Models for designs and alerts (validated then stored via helper)
class DesignPayload(BaseModel):
    user_id: Optional[str] = None
    sneaker_id: str
    name: str
    layers: dict = {}
    preview_url: Optional[str] = None
    is_public: bool = False

class AlertPayload(BaseModel):
    user_id: Optional[str] = None
    sneaker_id: str
    type: str  # 'price_drop' | 'restock'
    threshold_price: Optional[float] = None
    email: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "SneakPeak Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "❌ Unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# --------- Sneakers endpoints (mock data with integration-ready filters) ---------
@app.get("/api/sneakers")
def list_sneakers(
    q: Optional[str] = Query(None, description="Search query"),
    brand: Optional[str] = None,
    model: Optional[str] = None,
    minPrice: Optional[float] = None,
    maxPrice: Optional[float] = None,
    releaseFrom: Optional[str] = None,
    releaseTo: Optional[str] = None,
    sort: Optional[str] = Query(None, description="trending|price_asc|price_desc|release_desc|release_asc"),
    limit: int = 50,
):
    items = SNEAKERS.copy()

    if q:
        ql = q.lower()
        items = [s for s in items if ql in s['name'].lower() or ql in s['model'].lower() or ql in s['brand'].lower()]
    if brand:
        items = [s for s in items if s['brand'].lower() == brand.lower()]
    if model:
        items = [s for s in items if model.lower() in s['model'].lower()]
    if minPrice is not None:
        items = [s for s in items if s.get('stockx', {}).get('lowestAsk', s.get('retailPrice', 0)) >= minPrice]
    if maxPrice is not None:
        items = [s for s in items if s.get('stockx', {}).get('lowestAsk', s.get('retailPrice', 0)) <= maxPrice]
    if releaseFrom:
        items = [s for s in items if s.get('releaseDate') and s['releaseDate'] >= releaseFrom]
    if releaseTo:
        items = [s for s in items if s.get('releaseDate') and s['releaseDate'] <= releaseTo]

    if sort == 'trending':
        items.sort(key=lambda s: s.get('trendingScore', 0), reverse=True)
    elif sort == 'price_asc':
        items.sort(key=lambda s: s.get('stockx', {}).get('lowestAsk', s.get('retailPrice', 0)))
    elif sort == 'price_desc':
        items.sort(key=lambda s: s.get('stockx', {}).get('lowestAsk', s.get('retailPrice', 0)), reverse=True)
    elif sort == 'release_desc':
        items.sort(key=lambda s: s.get('releaseDate', ''), reverse=True)
    elif sort == 'release_asc':
        items.sort(key=lambda s: s.get('releaseDate', ''))

    return {"count": len(items), "items": items[:limit]}

@app.get("/api/sneakers/{sneaker_id}")
def get_sneaker(sneaker_id: str):
    s = SNEAKERS_BY_ID.get(sneaker_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sneaker not found")
    return s

@app.get("/api/trending")
def trending():
    items = sorted(SNEAKERS, key=lambda s: s.get('trendingScore', 0), reverse=True)[:8]
    terms = ["Jordan 1", "Air Force 1", "Yeezy 350", "Dunk Low", "New Balance 550", "AJ4", "Panda Dunks", "Travis Scott"]
    return {"items": items, "terms": terms}

@app.get("/api/stockx/{sneaker_id}/live")
def live_stockx(sneaker_id: str):
    s = SNEAKERS_BY_ID.get(sneaker_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sneaker not found")
    base = s.get('stockx', {})
    # Simulate small real-time fluctuations
    def jitter(val, pct=0.03):
        return round(val * (1 + random.uniform(-pct, pct))) if isinstance(val, (int, float)) else val
    live = {
        "lastSale": jitter(base.get('lastSale', s.get('retailPrice', 0)), 0.05),
        "lowestAsk": jitter(base.get('lowestAsk', s.get('retailPrice', 0)), 0.05),
        "highestBid": jitter(base.get('highestBid', s.get('retailPrice', 0)), 0.05),
        "volatility": round(max(0.01, base.get('volatility', 0.05) + random.uniform(-0.01, 0.01)), 3),
        "salesLast72h": max(0, base.get('salesLast72h', 0) + random.randint(-5, 5)),
        "asOf": datetime.utcnow().isoformat() + 'Z'
    }
    return live

# --------- Persistence endpoints using MongoDB helpers ---------
@app.post("/api/designs")
def create_design(payload: DesignPayload):
    try:
        from database import create_document
        design_id = create_document('design', payload.model_dump())
        return {"id": design_id, "ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/designs")
def list_designs(user_id: Optional[str] = None):
    try:
        from database import get_documents
        q = {"user_id": user_id} if user_id else {}
        docs = get_documents('design', q)
        # Convert ObjectId to string if present
        for d in docs:
            if "_id" in d:
                d["id"] = str(d.pop("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts")
def create_alert(payload: AlertPayload):
    try:
        from database import create_document
        alert_id = create_document('alert', payload.model_dump())
        return {"id": alert_id, "ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
