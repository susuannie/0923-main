"""
Gate 2 — Database (SQLite ETL & Verification)
Project: AIoT L3 CWA HW1
Workflow Baseline: 2026.09.23-current
Prerequisite: Gate 1 PASS.

Goal:
將真實 CWA response 做 ETL 並存入 SQLite。
建立 schema、資料驗證與 duplicate strategy，以 SQL SELECT 驗證指定地區及多地區資料。
禁止開始 GIS。
完成才回報：GATE 2 = PASS。
"""

import os
import sys
import json
import sqlite3
import ssl
from pathlib import Path
import urllib.request
import urllib.error

DB_FILE = Path(__file__).parent / "weather.db"
LOG_FILE = Path(__file__).parent / "gate2_verification.log"

def mask_key(key: str) -> str:
    if not key:
        return "[EMPTY]"
    if len(key) <= 8:
        return key[:2] + "****" + key[-2:]
    return key[:4] + "****..." + key[-4:]

def load_env_file(filepath: Path) -> dict:
    env_vars = {}
    if not filepath.exists():
        return env_vars
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars

def fetch_real_cwa_data(log) -> dict:
    dataset_id = "F-C0032-001"
    endpoint = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset_id}"
    env_vars = load_env_file(Path(__file__).parent / ".env")
    api_key = env_vars.get("CWA_API_KEY") or os.environ.get("CWA_API_KEY")

    if not api_key:
        log("[FAIL] 找不到 CWA_API_KEY，請確認 .env")
        sys.exit(1)

    log(f"[Extract] 連線氣象署 API (金鑰: {mask_key(api_key)})...")
    url = f"{endpoint}?Authorization={api_key}&format=JSON"

    def do_fetch(ssl_ctx):
        req = urllib.request.Request(url, headers={"User-Agent": "CWA-Weather-Client/1.0"})
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            return resp.getcode(), resp.read().decode("utf-8")

    try:
        status, text = do_fetch(ssl.create_default_context())
    except (urllib.error.URLError, ssl.SSLError) as e:
        status, text = do_fetch(ssl._create_unverified_context())

    if status != 200:
        log(f"[FAIL] HTTP 請求失敗: {status}")
        sys.exit(1)

    data = json.loads(text)
    if str(data.get("success")).lower() != "true":
        log(f"[FAIL] API 回傳 success 非 true: {data}")
        sys.exit(1)

    locations = data.get("records", {}).get("location", [])
    log(f"[Extract] 成功擷取 {len(locations)} 個縣市真實氣象資料")
    return locations

def init_db(db_path: Path, log):
    log(f"[Schema] 初始化 SQLite 資料庫: {db_path.name}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 建立主資料表與約束
    cur.execute("""
    CREATE TABLE IF NOT EXISTS weather_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        weather TEXT NOT NULL,
        min_temp REAL NOT NULL,
        max_temp REAL NOT NULL,
        pop INTEGER,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(location_name, start_time)
    );
    """)

    # 建立查詢索引以提升效能
    cur.execute("CREATE INDEX IF NOT EXISTS idx_forecast_location ON weather_forecasts(location_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_forecast_time ON weather_forecasts(start_time, end_time);")

    conn.commit()
    conn.close()
    log("[Schema] 資料表 weather_forecasts 及 UNIQUE(location_name, start_time) 建立完成")

def transform_and_validate(raw_locations: list, log) -> list:
    log("[Transform & Validate] 轉換氣象資料與驗證欄位合法性...")
    valid_records = []
    validation_errors = 0

    for loc in raw_locations:
        loc_name = loc.get("locationName", "").strip()
        if not loc_name:
            continue

        elements = {}
        for elem in loc.get("weatherElement", []):
            elements[elem.get("elementName")] = elem.get("time", [])

        wx_slots = elements.get("Wx", [])
        pop_slots = elements.get("PoP", [])
        mint_slots = elements.get("MinT", [])
        maxt_slots = elements.get("MaxT", [])

        num_slots = len(wx_slots)
        for i in range(num_slots):
            wx_item = wx_slots[i] if i < len(wx_slots) else {}
            pop_item = pop_slots[i] if i < len(pop_slots) else {}
            mint_item = mint_slots[i] if i < len(mint_slots) else {}
            maxt_item = maxt_slots[i] if i < len(maxt_slots) else {}

            start_t = wx_item.get("startTime", "").strip()
            end_t = wx_item.get("endTime", "").strip()
            weather = wx_item.get("parameter", {}).get("parameterName", "").strip()
            
            raw_min_t = mint_item.get("parameter", {}).get("parameterName")
            raw_max_t = maxt_item.get("parameter", {}).get("parameterName")
            raw_pop = pop_item.get("parameter", {}).get("parameterName")

            # 型別轉換
            try:
                min_t = float(raw_min_t) if raw_min_t is not None else None
                max_t = float(raw_max_t) if raw_max_t is not None else None
            except (ValueError, TypeError):
                min_t, max_t = None, None

            try:
                pop = int(raw_pop) if raw_pop is not None and raw_pop != "" else None
            except (ValueError, TypeError):
                pop = None

            # 資料驗證 (Data Validation)
            is_valid = True
            err_msg = []

            if not loc_name or not start_t or not end_t or not weather:
                is_valid = False
                err_msg.append("缺少必要鍵值")
            if min_t is None or max_t is None:
                is_valid = False
                err_msg.append("氣溫數值無效")
            elif min_t > max_t:
                is_valid = False
                err_msg.append(f"MinT ({min_t}) > MaxT ({max_t}) 邏輯錯誤")
            elif not (-15.0 <= min_t <= 50.0 and -15.0 <= max_t <= 50.0):
                is_valid = False
                err_msg.append(f"氣溫超出合理臺灣氣候範圍: {min_t}~{max_t}")

            if pop is not None and not (0 <= pop <= 100):
                is_valid = False
                err_msg.append(f"降雨機率不在 0~100 區間: {pop}")

            if is_valid:
                valid_records.append({
                    "location_name": loc_name,
                    "start_time": start_t,
                    "end_time": end_t,
                    "weather": weather,
                    "min_temp": min_t,
                    "max_temp": max_t,
                    "pop": pop
                })
            else:
                validation_errors += 1
                log(f"[WARNING] 略過異常資料 [{loc_name}]: {', '.join(err_msg)}")

    log(f"[Transform & Validate] 完成：成功轉換 {len(valid_records)} 筆，略過異常 {validation_errors} 筆")
    return valid_records

def load_to_sqlite(db_path: Path, records: list, log) -> int:
    """Load records with UPSERT duplicate strategy."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    upsert_sql = """
    INSERT INTO weather_forecasts (
        location_name, start_time, end_time, weather, min_temp, max_temp, pop, updated_at
    ) VALUES (
        :location_name, :start_time, :end_time, :weather, :min_temp, :max_temp, :pop, CURRENT_TIMESTAMP
    )
    ON CONFLICT(location_name, start_time) DO UPDATE SET
        end_time = excluded.end_time,
        weather = excluded.weather,
        min_temp = excluded.min_temp,
        max_temp = excluded.max_temp,
        pop = excluded.pop,
        updated_at = CURRENT_TIMESTAMP;
    """

    cur.executemany(upsert_sql, records)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM weather_forecasts;")
    total_count = cur.fetchone()[0]
    conn.close()
    return total_count

def run_sql_verifications(db_path: Path, log):
    log("\n" + "=" * 60)
    log("[Verification] 執行 SQL SELECT 驗證")
    log("=" * 60)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. 指定地區驗證（臺中市）
    log("\n[SQL Test 1] 指定地區查詢：臺中市 (Taichung City)")
    log("-" * 60)
    cur.execute("""
    SELECT location_name, start_time, end_time, weather, min_temp, max_temp, pop, updated_at
    FROM weather_forecasts
    WHERE location_name = '臺中市'
    ORDER BY start_time ASC;
    """)
    rows = cur.fetchall()
    log(f"臺中市預報筆數: {len(rows)}")
    for r in rows:
        log(f"  時間: {r[1]} ~ {r[2]} | 天氣: {r[3]:<6} | 氣溫: {r[4]}°C ~ {r[5]}°C | 降雨率: {r[6]}% | 更新: {r[7]}")

    if not rows:
        log("[FAIL] SQL 查無臺中市資料！")
        sys.exit(1)

    # 2. 多地區統計驗證（全台 22 縣市）
    log("\n[SQL Test 2] 全台多地區統計查詢：GROUP BY location_name")
    log("-" * 60)
    cur.execute("""
    SELECT 
        location_name, 
        COUNT(*) as slot_count, 
        MIN(min_temp) as lowest_t, 
        MAX(max_temp) as highest_t,
        AVG(pop) as avg_pop
    FROM weather_forecasts
    GROUP BY location_name
    ORDER BY location_name ASC;
    """)
    stats_rows = cur.fetchall()
    log(f"全台納入統計之縣市總數: {len(stats_rows)}")
    log(f"{'縣市':<6} | {'時段數':<6} | {'預報最低溫':<10} | {'預報最高溫':<10} | {'平均降雨機率':<10}")
    log("-" * 60)
    for sr in stats_rows:
        avg_p = f"{sr[4]:.1f}%" if sr[4] is not None else "N/A"
        log(f"{sr[0]:<6} | {sr[1]:<6} | {sr[2]:>6.1f}°C    | {sr[3]:>6.1f}°C    | {avg_p:>10}")

    if len(stats_rows) != 22:
        log(f"[FAIL] 縣市數量不符預期 22: 實際 {len(stats_rows)}")
        sys.exit(1)

    # 3. 欄位結構檢查
    log("\n[SQL Test 3] 資料表 Schema PRAGMA 驗證")
    cur.execute("PRAGMA table_info(weather_forecasts);")
    cols = cur.fetchall()
    col_names = [c[1] for c in cols]
    log(f"欄位清單: {', '.join(col_names)}")

    expected_cols = ["id", "location_name", "start_time", "end_time", "weather", "min_temp", "max_temp", "pop", "updated_at"]
    for ec in expected_cols:
        if ec not in col_names:
            log(f"[FAIL] 缺少欄位: {ec}")
            sys.exit(1)
    log("[SQL Test 3] Schema 欄位全部正確驗證！")

    conn.close()

def main():
    log_lines = []
    def log(msg: str):
        print(msg)
        log_lines.append(msg)

    log("=" * 60)
    log("AIoT L3 CWA HW1 — Gate 2: Database (SQLite ETL & Verification)")
    log("=" * 60)

    # Step 1: Initialize Database & Schema
    init_db(DB_FILE, log)

    # Step 2: Extract real CWA response
    raw_locations = fetch_real_cwa_data(log)

    # Step 3: Transform & Validate
    valid_records = transform_and_validate(raw_locations, log)

    # Step 4: Load into SQLite (First Run)
    log(f"[Load Run 1] 寫入 {len(valid_records)} 筆資料至 SQLite...")
    total_1 = load_to_sqlite(DB_FILE, valid_records, log)
    log(f"[Load Run 1] 第一次寫入完成，資料庫總筆數: {total_1}")
    if total_1 != len(valid_records):
        log(f"[FAIL] 寫入後總筆數 ({total_1}) 與有效筆數 ({len(valid_records)}) 不符！")
        sys.exit(1)

    # Step 5: Duplicate Strategy Test (Second Run)
    log("\n[Duplicate Strategy Test] 執行第二次重複寫入測試...")
    total_2 = load_to_sqlite(DB_FILE, valid_records, log)
    log(f"[Duplicate Strategy Test] 第二次寫入完成，資料庫總筆數: {total_2}")
    if total_2 != total_1:
        log(f"[FAIL] Duplicate Strategy 失敗！總筆數由 {total_1} 變為 {total_2}，資料發生重複！")
        sys.exit(1)
    log("[Duplicate Strategy Test] 總筆數維持不變 (UPSERT 成功防重複)，驗證 PASS！")

    # Step 6: SQL SELECT verifications
    run_sql_verifications(DB_FILE, log)

    # Save log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    log(f"\n[Log] 驗證記錄已儲存至: {LOG_FILE.name}")
    log(f"[DB] 資料庫檔案大小: {DB_FILE.stat().st_size} bytes")

    log("\n" + "=" * 60)
    log("GATE 2 = PASS")
    log("=" * 60)

if __name__ == "__main__":
    main()
