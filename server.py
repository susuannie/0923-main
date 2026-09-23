"""
Local GIS Web Server (Database -> GIS API)
Project: AIoT L3 CWA HW1 - Gate 3
Rule: Weather data MUST come from Database (weather.db).
"""

import os
import json
import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).parent.resolve()
DB_FILE = BASE_DIR / "weather.db"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Taiwan Weather GIS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    if not DB_FILE.exists():
        raise HTTPException(status_code=500, detail="Database file weather.db does not exist. Run Gate 2 first.")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/health")
def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM weather_forecasts;")
        count = cur.fetchone()["count"]
        cur.execute("SELECT MAX(updated_at) as last_update FROM weather_forecasts;")
        last_update = cur.fetchone()["last_update"]
        conn.close()
        return {
            "status": "healthy",
            "database": "weather.db",
            "total_records": count,
            "last_update": last_update
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/api/weather")
def get_weather_data():
    """
    Reads exclusively from SQLite weather.db to power GIS visualization.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT location_name, start_time, end_time, weather, min_temp, max_temp, pop, updated_at
        FROM weather_forecasts
        ORDER BY location_name ASC, start_time ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No weather data found in database.")

    # Group by location and extract unique time slots
    locations = {}
    time_slots_set = set()

    for r in rows:
        loc = r["location_name"]
        if loc not in locations:
            locations[loc] = []
        
        forecast_item = {
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "weather": r["weather"],
            "min_temp": r["min_temp"],
            "max_temp": r["max_temp"],
            "pop": r["pop"],
            "updated_at": r["updated_at"]
        }
        locations[loc].append(forecast_item)
        time_slots_set.add((r["start_time"], r["end_time"]))

    sorted_slots = sorted(list(time_slots_set), key=lambda x: x[0])
    formatted_slots = [
        {"slot_index": idx + 1, "start_time": s[0], "end_time": s[1]}
        for idx, s in enumerate(sorted_slots)
    ]

    return {
        "status": "success",
        "source": "SQLite (weather.db)",
        "total_locations": len(locations),
        "time_slots": formatted_slots,
        "data": locations
    }

@app.get("/api/geojson")
def get_taiwan_geojson():
    geojson_path = STATIC_DIR / "data" / "taiwan_counties.json"
    if not geojson_path.exists():
        raise HTTPException(status_code=404, detail="taiwan_counties.json not found")
    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    return FileResponse(index_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
