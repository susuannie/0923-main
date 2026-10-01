"""
Local GIS Web Server (Database -> GIS API with Cloud Fallback)
Project: AIoT L3 CWA HW1 - Gate 5
Rule: Weather data comes from Database (weather.db) locally, or CWA API on Cloud (Vercel).
"""

import os
import json
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
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
        raise HTTPException(status_code=500, detail="Database file weather.db does not exist.")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_cwa_fallback_data():
    """
    當 Vercel 雲端環境無 weather.db 時，自動呼叫中央氣象署 API 
    並轉成與資料庫一模一樣的 JSON 回傳格式
    """
    api_key = os.getenv("CWA_API_KEY", "")
    if not api_key:
        return None

    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return None
        
        cwa_json = res.json()
        loc_list = cwa_json.get("records", {}).get("location", [])
        
        locations = {}
        time_slots_set = set()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for loc in loc_list:
            loc_name = loc.get("locationName")
            if not loc_name:
                continue
            
            elements = {e["elementName"]: e.get("time", []) for e in loc.get("weatherElement", [])}
            wx_times = elements.get("Wx", [])
            pop_times = elements.get("PoP", [])
            mint_times = elements.get("MinT", [])
            maxt_times = elements.get("MaxT", [])
            
            if loc_name not in locations:
                locations[loc_name] = []

            for idx in range(len(wx_times)):
                s_time = wx_times[idx].get("startTime")
                e_time = wx_times[idx].get("endTime")
                wx_val = wx_times[idx].get("parameter", {}).get("parameterName", "")
                
                pop_val = pop_times[idx].get("parameter", {}).get("parameterName", "0") if idx < len(pop_times) else "0"
                mint_val = mint_times[idx].get("parameter", {}).get("parameterName", "0") if idx < len(mint_times) else "0"
                maxt_val = maxt_times[idx].get("parameter", {}).get("parameterName", "0") if idx < len(maxt_times) else "0"

                forecast_item = {
                    "start_time": s_time,
                    "end_time": e_time,
                    "weather": wx_val,
                    "min_temp": int(mint_val) if str(mint_val).isdigit() else mint_val,
                    "max_temp": int(maxt_val) if str(maxt_val).isdigit() else maxt_val,
                    "pop": int(pop_val) if str(pop_val).isdigit() else pop_val,
                    "updated_at": now_str
                }
                locations[loc_name].append(forecast_item)
                if s_time and e_time:
                    time_slots_set.add((s_time, e_time))

        sorted_slots = sorted(list(time_slots_set), key=lambda x: x[0])
        formatted_slots = [
            {"slot_index": idx + 1, "start_time": s[0], "end_time": s[1]}
            for idx, s in enumerate(sorted_slots)
        ]

        return {
            "status": "success",
            "source": "CWA Open API (Cloud Fallback)",
            "total_locations": len(locations),
            "time_slots": formatted_slots,
            "data": locations
        }
    except Exception as e:
        print("CWA API Error:", e)
        return None

@app.get("/api/health")
def health_check():
    # 本地資料庫檢查
    if DB_FILE.exists():
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
    
    # 雲端環境（無 DB）健康檢查
    return {
        "status": "healthy",
        "database": "None (Cloud API Mode)",
        "message": "Running on Vercel cloud environment using CWA API"
    }

@app.get("/api/weather")
def get_weather_data():
    """
    Reads from SQLite weather.db if available, else falls back to CWA API.
    """
    # 1. 本地優先：嘗試讀取 weather.db
    if DB_FILE.exists():
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT location_name, start_time, end_time, weather, min_temp, max_temp, pop, updated_at
            FROM weather_forecasts
            ORDER BY location_name ASC, start_time ASC;
        """)
        rows = cur.fetchall()
        conn.close()

        if rows:
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

    # 2. 雲端備援：若無 weather.db，從中央氣象署抓取
    cloud_data = get_cwa_fallback_data()
    if cloud_data:
        return cloud_data

    raise HTTPException(status_code=500, detail="No weather data available from SQLite DB or CWA API.")

@app.get("/api/geojson")
def get_taiwan_geojson():
    geojson_path = STATIC_DIR / "data" / "taiwan_counties.json"
    if not geojson_path.exists():
        # 備用路徑檢查
        geojson_path = STATIC_DIR / "data" / "taiwan.geojson"
        if not geojson_path.exists():
            raise HTTPException(status_code=404, detail="GeoJSON file not found in static/data/")
    
    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Mount static folder
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    return FileResponse(index_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)