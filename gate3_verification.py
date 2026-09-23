"""
Gate 3 — Local Taiwan GIS Verification Script
Project: AIoT L3 CWA HW1
Workflow Baseline: 2026.09.23-current
Prerequisite: Gate 2 PASS.

Milestones to verify:
3A Taiwan Map
3B One Marker (Taichung City)
3C Weather Popup
3D Taiwan Locations (22 locations)
3E Database -> GIS (Weather MUST come from SQLite weather.db)
3F Taiwan GeoJSON (taiwan_counties.json)
3G Interactive Dashboard (KPIs, Slot Switching, County Drawer)

Rule: Complete only Gate 3. Do not push to GitHub or deploy to Vercel yet.
"""

import sys
import json
import sqlite3
import time
import subprocess
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.resolve()
DB_FILE = BASE_DIR / "weather.db"
STATIC_DIR = BASE_DIR / "static"
LOG_FILE = BASE_DIR / "gate3_verification.log"

def main():
    log_lines = []
    def log(msg: str):
        print(msg)
        log_lines.append(msg)

    log("=" * 60)
    log("AIoT L3 CWA HW1 — Gate 3: Local Taiwan GIS Verification")
    log("=" * 60)

    # 1. Prerequisite & Database Check (3E Foundation)
    log("\n[Check 1] 檢驗 Gate 2 資料庫前置條件 (weather.db)...")
    if not DB_FILE.exists():
        log("[FAIL] weather.db 不存在！")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM weather_forecasts;")
    count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT location_name) FROM weather_forecasts;")
    loc_count = cur.fetchone()[0]
    conn.close()

    log(f"SQLite 預報總筆數: {count} 筆，涵蓋縣市數: {loc_count} 個")
    if count < 66 or loc_count < 22:
        log("[FAIL] 資料庫筆數不足，請先重新執行 Gate 2！")
        sys.exit(1)
    log("[Check 1] 資料庫前置條件檢核 PASS")

    # 2. Check Geographical Assets (3D & 3F Foundation)
    log("\n[Check 2] 檢驗地理資料資源 (3D 座標與 3F GeoJSON)...")
    coords_path = STATIC_DIR / "data" / "county_coordinates.json"
    geojson_path = STATIC_DIR / "data" / "taiwan_counties.json"

    if not coords_path.exists():
        log("[FAIL] county_coordinates.json 遺失！")
        sys.exit(1)
    with open(coords_path, "r", encoding="utf-8") as f:
        coords_data = json.load(f)
    log(f"已定義座標之縣市數: {len(coords_data)} 個")
    if len(coords_data) != 22:
        log("[FAIL] 座標檔案未涵蓋全台 22 縣市！")
        sys.exit(1)

    if not geojson_path.exists():
        log("[FAIL] taiwan_counties.json 遺失！")
        sys.exit(1)
    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    features = geojson_data.get("features", [])
    log(f"臺灣縣市 GeoJSON 多邊形數量: {len(features)} 個")
    if len(features) != 22:
        log("[FAIL] GeoJSON 特徵數量未涵蓋 22 縣市！")
        sys.exit(1)
    log("[Check 2] 地理資料資源檢核 PASS")

    # 3. Check Frontend Structure & Milestone Code Coverage
    log("\n[Check 3] 檢驗前端檔案與 3A ~ 3G 代碼實作覆蓋率...")
    app_js_path = STATIC_DIR / "js" / "app.js"
    index_html_path = STATIC_DIR / "index.html"
    style_css_path = STATIC_DIR / "css" / "style.css"

    for p in [app_js_path, index_html_path, style_css_path]:
        if not p.exists():
            log(f"[FAIL] 檔案遺失: {p.name}")
            sys.exit(1)
        log(f"檔案存在: {p.relative_to(BASE_DIR)} ({p.stat().st_size} bytes)")

    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js_code = f.read()

    milestones = {
        "3A Taiwan Map": "L.map('map'",
        "3B One Marker": "state.taichungMarker",
        "3C Weather Popup": "buildWeatherPopupHtml",
        "3D Taiwan Locations": "render3DTaiwanLocations",
        "3E Database -> GIS": "/api/weather",
        "3F Taiwan GeoJSON": "renderGeoJsonLayer",
        "3G Interactive Dashboard": "updateKpis"
    }

    for milestone, code_sig in milestones.items():
        if code_sig in app_js_code:
            log(f"  - [{milestone}] 核心實作確認存在 ({code_sig})")
        else:
            log(f"[FAIL] 缺少里程碑實作: {milestone}")
            sys.exit(1)
    log("[Check 3] 前端代碼結構檢核 PASS")

    # 4. Start Local Server & Verify Live Endpoints
    log("\n[Check 4] 啟動本機伺服器並實測 API 與圖台端點...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to bind
    time.sleep(2.5)

    try:
        # A. Health endpoint
        health_url = "http://127.0.0.1:8000/api/health"
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.getcode() != 200:
                log(f"[FAIL] /api/health 回應非 200: {res.getcode()}")
                sys.exit(1)
            health_json = json.loads(res.read().decode("utf-8"))
            log(f"  - [API Health] 狀態: {health_json.get('status')} | 資料庫: {health_json.get('database')} | 筆數: {health_json.get('total_records')}")

        # B. Weather API endpoint (Database -> GIS)
        weather_url = "http://127.0.0.1:8000/api/weather"
        with urllib.request.urlopen(urllib.request.Request(weather_url), timeout=5) as res:
            if res.getcode() != 200:
                log(f"[FAIL] /api/weather 回應非 200: {res.getcode()}")
                sys.exit(1)
            weather_json = json.loads(res.read().decode("utf-8"))
            log(f"  - [API Weather] 資料源: {weather_json.get('source')} | 縣市數: {weather_json.get('total_locations')} | 時段數: {len(weather_json.get('time_slots', []))}")
            if weather_json.get("source") != "SQLite (weather.db)":
                log("[FAIL] 資料來源非 SQLite！")
                sys.exit(1)
            
            # Check Taichung City forecast
            tc_data = weather_json.get("data", {}).get("臺中市")
            if not tc_data or len(tc_data) != 3:
                log("[FAIL] 查無臺中市 3 個時段預報！")
                sys.exit(1)
            log(f"  - [Taichung Data] 臺中市時段 1 氣溫: {tc_data[0]['min_temp']}°C ~ {tc_data[0]['max_temp']}°C，天氣: {tc_data[0]['weather']}")

        # C. GeoJSON endpoint
        geojson_url = "http://127.0.0.1:8000/api/geojson"
        with urllib.request.urlopen(urllib.request.Request(geojson_url), timeout=5) as res:
            if res.getcode() != 200:
                log(f"[FAIL] /api/geojson 回應非 200: {res.getcode()}")
                sys.exit(1)
            gj_resp = json.loads(res.read().decode("utf-8"))
            log(f"  - [API GeoJSON] 行政區特徵數量: {len(gj_resp.get('features', []))} 筆")

        # D. Static frontend index.html
        index_url = "http://127.0.0.1:8000/"
        with urllib.request.urlopen(urllib.request.Request(index_url), timeout=5) as res:
            if res.getcode() != 200:
                log(f"[FAIL] 首頁回應非 200: {res.getcode()}")
                sys.exit(1)
            html_text = res.read().decode("utf-8")
            if "Taiwan Weather GIS" not in html_text or "leaflet" not in html_text.lower():
                log("[FAIL] 首頁 HTML 缺少關鍵圖台標籤！")
                sys.exit(1)
            log("  - [Frontend Home] 成功回傳 GIS 圖台 HTML (200 OK)")

        log("[Check 4] 本機伺服器與端點實測全部 PASS")

    finally:
        # Terminate server process cleanly
        server_process.terminate()
        server_process.wait()

    # Save log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    log(f"\n[Log] 驗證記錄已儲存至: {LOG_FILE.name}")

    log("\n" + "=" * 60)
    log("3A Taiwan Map           : PASS")
    log("3B One Marker           : PASS")
    log("3C Weather Popup        : PASS")
    log("3D Taiwan Locations     : PASS")
    log("3E Database -> GIS      : PASS")
    log("3F Taiwan GeoJSON       : PASS")
    log("3G Interactive Dashboard: PASS")
    log("=" * 60)
    log("GATE 3 = PASS")
    log("=" * 60)

if __name__ == "__main__":
    main()
