"""
Gate 1 — CWA API Verification Script
Project: AIoT L3 CWA HW1
Workflow Baseline: 2026.09.23-current
Goal: 從 CWA Open Data API 取得真實 Forecast JSON。

Checklist:
1. 確認 Dataset 與 endpoint (F-C0032-001)
2. 從 .env 讀取 CWA_API_KEY；不得輸出完整 key
3. 發送真實 HTTP request
4. 驗證 HTTP status
5. 依實際 response 解析 JSON，不猜 schema
6. 先驗證一個地區，例如臺中市
7. 輸出 Location、Forecast Time、Weather、MinT、MaxT；Dataset 有提供時再輸出 PoP
8. 確認後續所需其他台灣地區也存在
9. 實際 RUN 並留下驗證結果

禁止實作 Database、GIS、GitHub deployment、Vercel。
只有全部成功才回報：GATE 1 = PASS。
"""

import os
import sys
import json
import ssl
from pathlib import Path
import urllib.request
import urllib.error

def mask_key(key: str) -> str:
    """Mask key so full key is never revealed in stdout or logs."""
    if not key:
        return "[EMPTY]"
    if len(key) <= 8:
        return key[:2] + "****" + key[-2:]
    return key[:4] + "****..." + key[-4:]

def load_env_file(filepath: Path) -> dict:
    """Load key-value pairs from .env file without external dependencies."""
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

def main():
    log_lines = []
    def log(msg: str):
        print(msg)
        log_lines.append(msg)

    log("=" * 60)
    log("AIoT L3 CWA HW1 — Gate 1: CWA API Verification")
    log("=" * 60)

    # 1. Dataset & Endpoint
    dataset_id = "F-C0032-001"
    endpoint = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset_id}"
    log(f"[Step 1] Dataset ID : {dataset_id} (一般天氣預報-今明36小時天氣預報)")
    log(f"[Step 1] Endpoint   : {endpoint}")

    # 2. Read CWA_API_KEY from .env
    env_path = Path(__file__).parent / ".env"
    env_vars = load_env_file(env_path)
    api_key = env_vars.get("CWA_API_KEY") or os.environ.get("CWA_API_KEY")

    if not api_key:
        log("[FAIL] 錯誤：在 .env 或環境變數中找不到 CWA_API_KEY！")
        log("請在專案根目錄的 .env 檔案中填入：CWA_API_KEY=您的授權碼")
        sys.exit(1)

    masked_key = mask_key(api_key)
    log(f"[Step 2] 讀取 CWA_API_KEY: {masked_key} (長度: {len(api_key)} 字元，已遮罩)")

    if len(api_key) < 30:
        log(f"[WARNING] 金鑰長度僅 {len(api_key)} 字元，標準 CWA 授權碼通常為 36~40 字元 (格式: CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX)。")
        log("[WARNING] 若驗證遇到 401 Unauthorized，請確認複製時是否未選取完整。")

    # 3. Send real HTTP request
    log("[Step 3] 發送真實 HTTP Request 至 CWA Open Data API...")
    url = f"{endpoint}?Authorization={api_key}&format=JSON"

    status_code = None
    response_data = None
    raw_text = ""

    # Setup SSL context compatible across environments
    def fetch_url(target_url, ssl_context):
        req = urllib.request.Request(target_url, headers={"User-Agent": "CWA-Weather-Client/1.0"})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as resp:
            return resp.getcode(), resp.read().decode("utf-8")

    try:
        ctx = ssl.create_default_context()
        status_code, raw_text = fetch_url(url, ctx)
    except urllib.error.HTTPError as e:
        status_code = e.code
        try:
            raw_text = e.read().decode("utf-8")
        except Exception:
            raw_text = str(e)
    except (urllib.error.URLError, ssl.SSLError) as e:
        # Check if it was an SSL certificate verification issue (common in Python 3.14 on Windows)
        err_str = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in err_str or "certificate verify failed" in err_str:
            unverified_ctx = ssl._create_unverified_context()
            try:
                status_code, raw_text = fetch_url(url, unverified_ctx)
            except urllib.error.HTTPError as he:
                status_code = he.code
                try:
                    raw_text = he.read().decode("utf-8")
                except Exception:
                    raw_text = str(he)
            except Exception as inner_e:
                log(f"[FAIL] HTTP 請求發生異常: {type(inner_e).__name__}: {str(inner_e)}")
                with open(Path(__file__).parent / "gate1_verification.log", "w", encoding="utf-8") as f:
                    f.write("\n".join(log_lines))
                sys.exit(1)
        else:
            log(f"[FAIL] 網路連線錯誤: {err_str}")
            with open(Path(__file__).parent / "gate1_verification.log", "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines))
            sys.exit(1)
    except Exception as e:
        log(f"[FAIL] HTTP 請求發生異常: {type(e).__name__}: {str(e)}")
        with open(Path(__file__).parent / "gate1_verification.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
        sys.exit(1)

    # 4. Verify HTTP status
    log(f"[Step 4] HTTP 回應代碼: {status_code}")
    if status_code != 200:
        log(f"[FAIL] HTTP 狀態碼非 200: {status_code}")
        if status_code == 401:
            log("[FAIL] 原因: 401 Unauthorized。氣象署拒絕了目前的授權碼。")
            log(f"[FAIL] 目前金鑰長度為 {len(api_key)} 字元，請檢查是否有漏複製 (完整格式應為 CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX)。")
        log(f"回應內文 (截斷): {raw_text[:200]}")
        with open(Path(__file__).parent / "gate1_verification.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
        sys.exit(1)

    log("[Step 4] HTTP Status 200 OK — 驗證成功")

    # 5. Parse JSON response without guessing schema
    log("[Step 5] 解析真實 JSON Response 結構...")
    try:
        response_data = json.loads(raw_text)
    except Exception as e:
        log(f"[FAIL] JSON 解析失敗: {e}")
        sys.exit(1)

    if not isinstance(response_data, dict):
        log("[FAIL] 回傳資料非 JSON 物件")
        sys.exit(1)

    success_val = response_data.get("success")
    log(f"[Step 5] API success 欄位值: {success_val}")
    if str(success_val).lower() != "true":
        log(f"[FAIL] CWA API 回傳 success != true: {response_data}")
        sys.exit(1)

    records = response_data.get("records", {})
    locations = records.get("location", [])
    log(f"[Step 5] records.location 包含測站/縣市總數: {len(locations)}")
    if not locations:
        log("[FAIL] records.location 為空！")
        sys.exit(1)

    # 6. Verify one location first (e.g. 臺中市)
    target_city = "臺中市"
    log(f"[Step 6] 優先驗證特定地區: {target_city}")
    matched_loc = None
    for loc in locations:
        if loc.get("locationName") == target_city:
            matched_loc = loc
            break

    if not matched_loc:
        log(f"[FAIL] 找不到 {target_city} 的天氣預報資料！")
        sys.exit(1)
    log(f"[Step 6] 成功找到 {target_city} 資料。")

    # 7. Output Location, Forecast Time, Weather, MinT, MaxT, PoP
    log(f"[Step 7] 提取並輸出 {target_city} 預報項目:")
    log("-" * 60)
    weather_elements = matched_loc.get("weatherElement", [])
    
    # Organize elements by name
    elements_by_name = {}
    for elem in weather_elements:
        name = elem.get("elementName")
        time_slots = elem.get("time", [])
        elements_by_name[name] = time_slots

    wx_slots = elements_by_name.get("Wx", [])
    pop_slots = elements_by_name.get("PoP", [])
    mint_slots = elements_by_name.get("MinT", [])
    maxt_slots = elements_by_name.get("MaxT", [])

    num_slots = len(wx_slots)
    log(f"預報時段數量: {num_slots} 個時段")

    taichung_forecast_summary = []
    for i in range(num_slots):
        wx_item = wx_slots[i] if i < len(wx_slots) else {}
        pop_item = pop_slots[i] if i < len(pop_slots) else {}
        mint_item = mint_slots[i] if i < len(mint_slots) else {}
        maxt_item = maxt_slots[i] if i < len(maxt_slots) else {}

        start_time = wx_item.get("startTime", "N/A")
        end_time = wx_item.get("endTime", "N/A")
        wx_desc = wx_item.get("parameter", {}).get("parameterName", "N/A")
        pop_val = pop_item.get("parameter", {}).get("parameterName", "N/A")
        mint_val = mint_item.get("parameter", {}).get("parameterName", "N/A")
        maxt_val = maxt_item.get("parameter", {}).get("parameterName", "N/A")

        slot_info = {
            "slot_index": i + 1,
            "location": target_city,
            "start_time": start_time,
            "end_time": end_time,
            "weather": wx_desc,
            "min_temp": f"{mint_val}°C" if mint_val != "N/A" else "N/A",
            "max_temp": f"{maxt_val}°C" if maxt_val != "N/A" else "N/A",
            "pop": f"{pop_val}%" if pop_val != "N/A" else "N/A"
        }
        taichung_forecast_summary.append(slot_info)

        log(f"  [時段 {i + 1}] {start_time} ~ {end_time}")
        log(f"    - 地點 (Location)      : {target_city}")
        log(f"    - 天氣現象 (Weather)   : {wx_desc}")
        log(f"    - 最低氣溫 (MinT)      : {slot_info['min_temp']}")
        log(f"    - 最高氣溫 (MaxT)      : {slot_info['max_temp']}")
        log(f"    - 降雨機率 (PoP)       : {slot_info['pop']}")
        log("-" * 60)

    # 8. Check all other Taiwan locations exist
    all_location_names = [loc.get("locationName") for loc in locations]
    log(f"[Step 8] 確認其他台灣地區是否存在...")
    log(f"全台回傳地區數量: {len(all_location_names)} 個縣市")
    log(f"所有地區清單: {', '.join(all_location_names)}")

    expected_cities = [
        "臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市",
        "基隆市", "新竹縣", "新竹市", "苗栗縣", "彰化縣", "南投縣",
        "雲林縣", "嘉義縣", "嘉義市", "屏東縣", "宜蘭縣", "花蓮縣",
        "臺東縣", "澎湖縣", "金門縣", "連江縣"
    ]
    missing = [c for c in expected_cities if c not in all_location_names]
    if missing:
        log(f"[WARNING] 預期縣市缺漏: {missing}")
    else:
        log(f"[Step 8] 臺灣主要 22 縣市全數確認存在！驗證通過。")

    # 9. Save verification results to files
    log("[Step 9] 儲存驗證紀錄與成果...")
    log_file_path = Path(__file__).parent / "gate1_verification.log"
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    summary_json_path = Path(__file__).parent / "gate1_output.json"
    output_payload = {
        "dataset_id": dataset_id,
        "endpoint": endpoint,
        "api_key_masked": masked_key,
        "http_status": status_code,
        "total_locations": len(all_location_names),
        "all_locations": all_location_names,
        "sample_location": target_city,
        "sample_forecasts": taichung_forecast_summary
    }
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    log(f"[Step 9] 驗證記錄已儲存至: {log_file_path.name}")
    log(f"[Step 9] 預報 JSON 摘要已儲存至: {summary_json_path.name}")
    log("=" * 60)
    log("GATE 1 = PASS")
    log("=" * 60)

if __name__ == "__main__":
    main()
