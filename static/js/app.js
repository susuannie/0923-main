// 1. 氣溫對應色碼函數 (規格書 Section 15)
function getColorByTemp(temp) {
  if (temp < 10) return "#2b6cb0";
  if (temp < 15) return "#3182ce";
  if (temp < 20) return "#38a169";
  if (temp < 25) return "#ecc94b";
  if (temp < 30) return "#ed8936";
  if (temp < 35) return "#e53e3e";
  return "#9b2c2c";
}

// 2. Windy 初始化參數 (規格書 Section 12)
const options = {
  key: "YOUR_WINDY_API_KEY",
  lat: 23.7,
  lon: 121.0,
  zoom: 7,
  overlay: "wind",
  verbose: true
};

// 3. 啟動 Windy 並疊加 CWA 氣溫圖層 (規格書 Section 12 & 14)
if (typeof windyInit === 'function') {
  windyInit(options, windyAPI => {
    const { map, store } = windyAPI;

    // 預設開啟風速背景圖層
    store.set("overlay", "wind");

    // 建立 CWA 測站 LayerGroup
    const cwaLayer = L.layerGroup().addTo(map);

    // 從 FastAPI 後端讀取 CWA 資料
    async function fetchCwaTemperature() {
      try {
        const response = await fetch('/api/temperature/latest');
        if (!response.ok) throw new Error('Network error');
        const data = await response.json();

        cwaLayer.clearLayers();

        // 更新頂部資訊列時間
        if (data.updated_at) {
          const statusElem = document.getElementById('cwa-status');
          if (statusElem) {
            statusElem.innerText = '最後更新: ' + data.updated_at;
          }
        }

        // 繪製每個 CWA 觀測站的色塊與 Popup
        const stations = data.stations || [];
        stations.forEach(station => {
          if (station.lat && station.lon && station.temperature_c !== null && station.temperature_c !== undefined) {
            const marker = L.circleMarker([station.lat, station.lon], {
              radius: 7,
              fillColor: getColorByTemp(station.temperature_c),
              fillOpacity: 0.85,
              color: "#ffffff",
              weight: 1
            });

            // 單行安全版 Popup 內容 (防止換行貼上跑掉)
            const popupContent = 'marker.bindPopup(popupContent)'
            marker.addTo(cwaLayer);
          }
        });
      } catch (error) {
        console.error("無法載入 CWA 氣溫資料:", error);
      }
    }

    // 首次載入與每 5 分鐘自動刷新 (規格書 Section 16)
    fetchCwaTemperature();
    setInterval(fetchCwaTemperature, 300000);
  });
} else {
  console.error("Windy API (libBoot.js) 未成功載入。");
}