/**
 * Gate 1 — CWA API Verification Script (Node.js)
 * Project: AIoT L3 CWA HW1
 * Workflow Baseline: 2026.09.23-current
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function maskKey(key) {
  if (!key) return '[EMPTY]';
  if (key.length <= 8) return key.slice(0, 2) + '****' + key.slice(-2);
  return key.slice(0, 4) + '****...' + key.slice(-4);
}

function loadEnv(filePath) {
  const env = {};
  if (!fs.existsSync(filePath)) return env;
  const content = fs.readFileSync(filePath, 'utf-8');
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx !== -1) {
      const k = trimmed.slice(0, eqIdx).trim();
      const v = trimmed.slice(eqIdx + 1).trim().replace(/^['"]|['"]$/g, '');
      env[k] = v;
    }
  }
  return env;
}

async function run() {
  const logLines = [];
  function log(msg) {
    console.log(msg);
    logLines.push(msg);
  }

  log('='.repeat(60));
  log('AIoT L3 CWA HW1 — Gate 1: CWA API Verification (Node.js)');
  log('='.repeat(60));

  // 1. Dataset & Endpoint
  const datasetId = 'F-C0032-001';
  const endpoint = `https://opendata.cwa.gov.tw/api/v1/rest/datastore/${datasetId}`;
  log(`[Step 1] Dataset ID : ${datasetId} (一般天氣預報-今明36小時天氣預報)`);
  log(`[Step 1] Endpoint   : ${endpoint}`);

  // 2. Read CWA_API_KEY from .env
  const env = loadEnv(path.join(__dirname, '.env'));
  const apiKey = env.CWA_API_KEY || process.env.CWA_API_KEY;

  if (!apiKey) {
    log('[FAIL] 錯誤：在 .env 中找不到 CWA_API_KEY！');
    process.exit(1);
  }

  const maskedKey = maskKey(apiKey);
  log(`[Step 2] 讀取 CWA_API_KEY: ${maskedKey} (長度: ${apiKey.length} 字元，已遮罩)`);
  if (apiKey.length < 30) {
    log(`[WARNING] 金鑰長度僅 ${apiKey.length} 字元，完整 CWA 授權碼通常為 36~40 字元。`);
  }

  // 3. Send real HTTP request
  log('[Step 3] 發送真實 HTTP Request 至 CWA Open Data API...');
  const url = `${endpoint}?Authorization=${encodeURIComponent(apiKey)}&format=JSON`;

  let response;
  try {
    response = await fetch(url);
  } catch (err) {
    log(`[FAIL] 網路連線錯誤: ${err.message}`);
    process.exit(1);
  }

  // 4. Verify HTTP status
  log(`[Step 4] HTTP 回應代碼: ${response.status} ${response.statusText}`);
  if (response.status !== 200) {
    log(`[FAIL] HTTP 狀態碼非 200: ${response.status}`);
    if (response.status === 401) {
      log('[FAIL] 401 Unauthorized: 授權碼無效或不完整，請確認是否漏複製。');
    }
    const txt = await response.text();
    log(`回應內文 (截斷): ${txt.slice(0, 200)}`);
    process.exit(1);
  }

  // 5. Parse JSON response
  log('[Step 5] 解析真實 JSON Response 結構...');
  const data = await response.json();
  if (String(data.success).toLowerCase() !== 'true') {
    log(`[FAIL] API success 欄位非 true: ${JSON.stringify(data)}`);
    process.exit(1);
  }

  const locations = data.records?.location || [];
  log(`[Step 5] records.location 包含測站/縣市總數: ${locations.length}`);

  // 6. Verify one location (臺中市)
  const targetCity = '臺中市';
  log(`[Step 6] 優先驗證特定地區: ${targetCity}`);
  const matched = locations.find((l) => l.locationName === targetCity);
  if (!matched) {
    log(`[FAIL] 找不到 ${targetCity} 預報資料！`);
    process.exit(1);
  }

  // 7. Output standard fields
  log(`[Step 7] 提取並輸出 ${targetCity} 預報項目:`);
  log('-'.repeat(60));
  const elements = {};
  for (const elem of matched.weatherElement || []) {
    elements[elem.elementName] = elem.time || [];
  }

  const wxSlots = elements.Wx || [];
  const popSlots = elements.PoP || [];
  const minTSlots = elements.MinT || [];
  const maxTSlots = elements.MaxT || [];

  const summary = [];
  for (let i = 0; i < wxSlots.length; i++) {
    const wx = wxSlots[i] || {};
    const pop = popSlots[i] || {};
    const minT = minTSlots[i] || {};
    const maxT = maxTSlots[i] || {};

    const startTime = wx.startTime || 'N/A';
    const endTime = wx.endTime || 'N/A';
    const wxDesc = wx.parameter?.parameterName || 'N/A';
    const popVal = pop.parameter?.parameterName ? `${pop.parameter.parameterName}%` : 'N/A';
    const minTVal = minT.parameter?.parameterName ? `${minT.parameter.parameterName}°C` : 'N/A';
    const maxTVal = maxT.parameter?.parameterName ? `${maxT.parameter.parameterName}°C` : 'N/A';

    summary.push({
      slot_index: i + 1,
      location: targetCity,
      start_time: startTime,
      end_time: endTime,
      weather: wxDesc,
      min_temp: minTVal,
      max_temp: maxTVal,
      pop: popVal,
    });

    log(`  [時段 ${i + 1}] ${startTime} ~ ${endTime}`);
    log(`    - 地點 (Location)      : ${targetCity}`);
    log(`    - 天氣現象 (Weather)   : ${wxDesc}`);
    log(`    - 最低氣溫 (MinT)      : ${minTVal}`);
    log(`    - 最高氣溫 (MaxT)      : ${maxTVal}`);
    log(`    - 降雨機率 (PoP)       : ${popVal}`);
    log('-'.repeat(60));
  }

  // 8. Check all Taiwan locations
  const allNames = locations.map((l) => l.locationName);
  log(`[Step 8] 確認其他台灣地區是否存在...`);
  log(`全台回傳地區數量: ${allNames.length} 個縣市`);
  log(`所有地區清單: ${allNames.join(', ')}`);

  // 9. Save output
  log('[Step 9] 儲存驗證紀錄與成果...');
  fs.writeFileSync(path.join(__dirname, 'gate1_verification.log'), logLines.join('\n') + '\n', 'utf-8');
  fs.writeFileSync(
    path.join(__dirname, 'gate1_output.json'),
    JSON.stringify(
      {
        dataset_id: datasetId,
        endpoint,
        api_key_masked: maskedKey,
        http_status: response.status,
        total_locations: allNames.length,
        all_locations: allNames,
        sample_location: targetCity,
        sample_forecasts: summary,
      },
      null,
      2
    ),
    'utf-8'
  );

  log('='.repeat(60));
  log('GATE 1 = PASS');
  log('='.repeat(60));
}

run();
