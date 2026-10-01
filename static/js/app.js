// ==========================================
// Gate 3: Taiwan GIS Dashboard (Leaflet + OpenStreetMap)
// ==========================================

// 全局狀態物件 (包含 3B 要求的 state.taichungMarker)
const state = {
  taichungMarker: null,
  weatherData: []
};

// 3A. Taiwan Map: 初始化 Leaflet 地圖
const map = L.map('map').setView([23.7, 121.0], 7);

// 3A. OpenStreetMap 圖層
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors',
  maxZoom: 19
}).addTo(map);

// 3B. One Marker: 臺中市標記 (指定 state.taichungMarker 變數)
state.taichungMarker = L.marker([24.1477, 120.6736]).addTo(map);

// 3C. Weather Popup: 氣象彈窗生成函數
function buildWeatherPopupHtml(station) {
  return `
        <div style="font-size: 13px; line-height: 1.6; color: #333;">
            <strong style="font-size: 15px; color: #1a202c;">${station.station_name || station.location_name || '氣象測站'}</strong><br/>
            🌡️ 氣溫：<b>${station.temperature_c ?? station.max_temp ?? '-'} °C</b><br/>
            🌧️ 降雨機率：${station.pop ?? '-'} %<br/>
            🌤️ 天氣現象：${station.weather || '-'}<br/>
            🕒 時間：${station.observed_at || station.updated_at || '-'}
        </div>
    `;
}

// 綁定 3B 標記的 3C 彈窗
state.taichungMarker.bindPopup(buildWeatherPopupHtml({ station_name: '臺中市基準點', temperature_c: 25 }));

// 溫度色階
function getColorByTemp(temp) {
  if (temp < 10) return "#2b6cb0";
  if (temp < 15) return "#3182ce";
  if (temp < 20) return "#38a169";
  if (temp < 25) return "#ecc94b";
  if (temp < 30) return "#ed8936";
  if (temp < 35) return "#e53e3e";
  return "#9b2c2c";
}

const weatherLayer = L.layerGroup().addTo(map);

// 3D. Taiwan Locations: 渲染全台多點資料
function render3DTaiwanLocations(stations) {
  weatherLayer.clearLayers();
  stations.forEach(station => {
    const lat = station.lat;
    const lon = station.lon;
    const temp = station.temperature_c ?? station.max_temp;

    if (lat && lon) {
      const marker = L.circleMarker([lat, lon], {
        radius: 8,
        fillColor: getColorByTemp(temp ?? 25),
        fillOpacity: 0.85,
        color: "#ffffff",
        weight: 1.5
      });

      marker.bindPopup(buildWeatherPopupHtml(station));
      marker.addTo(weatherLayer);
    }
  });
}

// 3G. Interactive Dashboard: 更新面板與 KPI
function updateKpis(data) {
  const statusElem = document.getElementById('cwa-status');
  if (statusElem && data.updated_at) {
    statusElem.innerText = '最後更新: ' + data.updated_at;
  }
}

// 3E. Database -> GIS: 讀取 API 氣象資料 (包含 /api/weather 路徑)
async function loadWeatherData() {
  try {
    let response = await fetch('/api/weather');
    if (!response.ok) {
      response = await fetch('/api/temperature/latest');
    }
    if (!response.ok) return;

    const data = await response.json();
    state.weatherData = data.stations || [];

    render3DTaiwanLocations(state.weatherData);
    updateKpis(data);
  } catch (error) {
    console.error("氣象資料載入失敗:", error);
  }
}

// 3F. Taiwan GeoJSON: 載入縣市邊界圖層
async function renderGeoJsonLayer() {
  try {
    let response = await fetch('/static/data/taiwan.geojson');
    if (!response.ok) {
      response = await fetch('/static/data/taiwan_counties.json');
    }
    if (!response.ok) return;

    const geojson = await response.json();
    L.geoJSON(geojson, {
      style: {
        color: "#4a5568",
        weight: 1,
        fillColor: "#3182ce",
        fillOpacity: 0.05
      }
    }).addTo(map);
  } catch (e) {
    console.log("GeoJSON 載入說明:", e);
  }
}

// 初始化執行
renderGeoJsonLayer();
loadWeatherData();