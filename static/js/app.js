/**
 * Taiwan Weather GIS — Core Frontend Application
 * AIoT L3 CWA HW1 — Gate 3 Local Taiwan GIS
 * 
 * Milestone Implementation:
 *  3A Taiwan Map
 *  3B One Marker
 *  3C Weather Popup
 *  3D Taiwan Locations
 *  3E Database -> GIS (SQLite weather.db)
 *  3F Taiwan GeoJSON
 *  3G Interactive Dashboard
 */

// Application State
const state = {
  currentSlotIndex: 0,
  activeMode: 'temp', // 'temp' | 'pop'
  weatherData: {},    // Map of locationName -> [forecast_slot_1, 2, 3] from SQLite
  timeSlots: [],      // Array of 3 forecast time intervals
  coordinates: {},    // Map of locationName -> {lat, lng}
  geoJsonData: null,
  selectedLocation: '臺中市',
  
  // Leaflet Layer References
  map: null,
  markersLayer: null,
  geoJsonLayer: null,
  taichungMarker: null // 3B Specific Milestone Reference
};

// Color Utility Functions
function getTempColor(temp) {
  if (temp === null || temp === undefined) return '#64748b';
  if (temp < 24) return '#3b82f6';      // Cold Blue
  if (temp < 27) return '#10b981';      // Mild Emerald
  if (temp < 30) return '#f59e0b';      // Warm Amber
  if (temp < 33) return '#ef4444';      // Hot Red
  return '#8b5cf6';                    // Extreme Violet
}

function getPoPColor(pop) {
  if (pop === null || pop === undefined) return '#64748b';
  if (pop === 0) return '#10b981';       // No rain
  if (pop <= 20) return '#06b6d4';      // Low
  if (pop <= 50) return '#3b82f6';      // Medium
  if (pop <= 80) return '#6366f1';      // High
  return '#8b5cf6';                    // Very High
}

function getWeatherIcon(weatherDesc) {
  if (!weatherDesc) return '⛅';
  if (weatherDesc.includes('晴') && !weatherDesc.includes('雨')) {
    return weatherDesc.includes('雲') ? '🌤️' : '☀️';
  }
  if (weatherDesc.includes('多雲') || weatherDesc.includes('陰')) {
    return weatherDesc.includes('雨') ? '🌧️' : '☁️';
  }
  if (weatherDesc.includes('雷')) return '⛈️';
  if (weatherDesc.includes('雨')) return '🌧️';
  return '⛅';
}

// ==========================================================================
// 3A: Taiwan Map Initialization
// ==========================================================================
function init3ATaiwanMap() {
  console.log('[3A] Initializing Taiwan Leaflet Map...');
  state.map = L.map('map', {
    center: [23.75, 120.95],
    zoom: 7.6,
    zoomSnap: 0.1,
    zoomControl: true,
    attributionControl: true
  });

  // Sleek Dark Matter Tiles (OpenStreetMap base)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 18
  }).addTo(state.map);

  state.markersLayer = L.layerGroup().addTo(state.map);
  console.log('[3A Taiwan Map] PASS');
}

// ==========================================================================
// 3B & 3C: One Marker & Weather Popup (Taichung City)
// ==========================================================================
function init3BOneMarkerAndPopup(taichungForecast) {
  console.log('[3B & 3C] Initializing One Marker (Taichung City) & Weather Popup...');
  const tcCoords = [24.1477, 120.6736];

  const popupHtml = buildWeatherPopupHtml('臺中市', taichungForecast);

  // Milestone marker
  const customIcon = L.divIcon({
    className: 'custom-station-marker',
    html: `
      <div class="marker-pill" style="background: ${getTempColor(taichungForecast.max_temp)};">
        <span>${getWeatherIcon(taichungForecast.weather)}</span>
        <span>${taichungForecast.max_temp}°C</span>
      </div>
      <div class="marker-name">臺中市 (3B)</div>
    `,
    iconSize: [80, 40],
    iconAnchor: [40, 20]
  });

  state.taichungMarker = L.marker(tcCoords, { icon: customIcon })
    .bindPopup(popupHtml, { maxWidth: 260 })
    .addTo(state.markersLayer);

  console.log('[3B One Marker & 3C Weather Popup] Initialized.');
}

function buildWeatherPopupHtml(locationName, forecast) {
  const icon = getWeatherIcon(forecast.weather);
  const popStr = forecast.pop !== null && forecast.pop !== undefined ? `${forecast.pop}%` : 'N/A';
  return `
    <div class="weather-popup">
      <div class="popup-title">${icon} ${locationName}</div>
      <div class="popup-time">${forecast.start_time.slice(5, 16)} ~ ${forecast.end_time.slice(5, 16)}</div>
      <div class="popup-row">
        <span class="popup-label">天氣狀況</span>
        <span class="popup-val">${forecast.weather}</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">最高氣溫 (MaxT)</span>
        <span class="popup-val" style="color:#f87171;">${forecast.max_temp}°C</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">最低氣溫 (MinT)</span>
        <span class="popup-val" style="color:#60a5fa;">${forecast.min_temp}°C</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">降雨機率 (PoP)</span>
        <span class="popup-val" style="color:#38bdf8;">${popStr}</span>
      </div>
      <div class="popup-row" style="margin-top:6px; font-size:0.68rem; color:#10b981;">
        <span class="popup-label">資料來源</span>
        <span class="popup-val">SQLite (weather.db)</span>
      </div>
    </div>
  `;
}

// ==========================================================================
// 3D: Taiwan Locations Markers
// ==========================================================================
function render3DTaiwanLocations() {
  console.log('[3D] Rendering all 22 Taiwan locations markers...');
  state.markersLayer.clearLayers();

  const slotIdx = state.currentSlotIndex;

  Object.entries(state.coordinates).forEach(([locName, coords]) => {
    const forecasts = state.weatherData[locName];
    if (!forecasts || !forecasts[slotIdx]) return;

    const f = forecasts[slotIdx];
    const isTaichung = locName === '臺中市';
    const metricVal = state.activeMode === 'temp' ? `${f.max_temp}°C` : `${f.pop}%`;
    const bgColor = state.activeMode === 'temp' ? getTempColor(f.max_temp) : getPoPColor(f.pop);

    const markerHtml = `
      <div class="marker-pill" style="background:${bgColor};">
        <span>${getWeatherIcon(f.weather)}</span>
        <span>${metricVal}</span>
      </div>
      <div class="marker-name">${locName}</div>
    `;

    const customIcon = L.divIcon({
      className: 'custom-station-marker',
      html: markerHtml,
      iconSize: [70, 36],
      iconAnchor: [35, 18]
    });

    const marker = L.marker([coords.lat, coords.lng], { icon: customIcon });
    marker.bindPopup(buildWeatherPopupHtml(locName, f), { maxWidth: 260 });
    
    marker.on('click', () => {
      openWeatherDrawer(locName);
    });

    marker.addTo(state.markersLayer);
    if (isTaichung) {
      state.taichungMarker = marker;
    }
  });

  console.log('[3D Taiwan Locations] 22 Location Markers Rendered.');
}

// ==========================================================================
// 3E: Database -> GIS (Fetch from SQLite via /api/weather)
// ==========================================================================
async function load3EDatabaseToGIS() {
  console.log('[3E] Loading weather data from Database (SQLite weather.db)...');
  try {
    const res = await fetch('/api/weather');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const json = await res.json();
    
    state.weatherData = json.data;
    state.timeSlots = json.time_slots;

    console.log(`[3E Database -> GIS] Successfully received ${json.total_locations} locations from ${json.source}`);
    updateTimeBanner();
    updateKpis();
    return true;
  } catch (err) {
    console.error('[3E Database -> GIS] Error fetching weather:', err);
    return false;
  }
}

// ==========================================================================
// 3F: Taiwan GeoJSON Boundary Layer & Choropleth
// ==========================================================================
async function load3FTaiwanGeoJSON() {
  console.log('[3F] Loading Taiwan GeoJSON...');
  try {
    const res = await fetch('/api/geojson');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    state.geoJsonData = await res.json();

    renderGeoJsonLayer();
    console.log('[3F Taiwan GeoJSON] Layer rendered.');
  } catch (err) {
    console.error('[3F Taiwan GeoJSON] Error loading GeoJSON:', err);
  }
}

function getFeatureColor(feature) {
  const locName = feature.properties.name || feature.properties.COUNTYNAME;
  const forecasts = state.weatherData[locName];
  if (!forecasts || !forecasts[state.currentSlotIndex]) return '#334155';

  const f = forecasts[state.currentSlotIndex];
  return state.activeMode === 'temp' ? getTempColor(f.max_temp) : getPoPColor(f.pop);
}

function renderGeoJsonLayer() {
  if (state.geoJsonLayer) {
    state.map.removeLayer(state.geoJsonLayer);
  }

  state.geoJsonLayer = L.geoJSON(state.geoJsonData, {
    style: (feature) => ({
      fillColor: getFeatureColor(feature),
      weight: 1.5,
      opacity: 0.9,
      color: 'rgba(255, 255, 255, 0.4)',
      fillOpacity: 0.45
    }),
    onEachFeature: (feature, layer) => {
      const locName = feature.properties.name || feature.properties.COUNTYNAME;
      
      layer.on({
        mouseover: (e) => {
          const l = e.target;
          l.setStyle({
            weight: 3,
            color: '#38bdf8',
            fillOpacity: 0.75
          });
          l.bringToFront();
        },
        mouseout: (e) => {
          state.geoJsonLayer.resetStyle(e.target);
        },
        click: (e) => {
          openWeatherDrawer(locName);
          state.map.flyTo(e.latlng, 8.8, { duration: 0.8 });
        }
      });
    }
  }).addTo(state.map);
}

// ==========================================================================
// 3G: Interactive Dashboard (KPIs, Slot Switch, Search & Drawer)
// ==========================================================================
function updateTimeBanner() {
  const slot = state.timeSlots[state.currentSlotIndex];
  if (!slot) return;
  const label = `預報區間：${slot.start_time} 至 ${slot.end_time}`;
  document.getElementById('currentSlotTime').textContent = label;
}

function updateKpis() {
  const slotIdx = state.currentSlotIndex;
  let maxT = -999, maxLoc = '';
  let minT = 999, minLoc = '';
  let totalPoP = 0, popCount = 0;

  Object.entries(state.weatherData).forEach(([loc, forecasts]) => {
    const f = forecasts[slotIdx];
    if (!f) return;

    if (f.max_temp > maxT) {
      maxT = f.max_temp;
      maxLoc = loc;
    }
    if (f.min_temp < minT) {
      minT = f.min_temp;
      minLoc = loc;
    }
    if (f.pop !== null && f.pop !== undefined) {
      totalPoP += f.pop;
      popCount++;
    }
  });

  document.getElementById('kpiHighVal').textContent = `${maxT.toFixed(1)}°C`;
  document.getElementById('kpiHighLoc').textContent = `${maxLoc} 最高溫`;

  document.getElementById('kpiLowVal').textContent = `${minT.toFixed(1)}°C`;
  document.getElementById('kpiLowLoc').textContent = `${minLoc} 最低溫`;

  const avgPop = popCount > 0 ? (totalPoP / popCount).toFixed(0) : '0';
  document.getElementById('kpiRainVal').textContent = `${avgPop}%`;
  document.getElementById('kpiRainDesc').textContent = avgPop > 30 ? '部分地區有雨勢' : '降雨機率低，多雲到晴';
}

function openWeatherDrawer(locationName) {
  state.selectedLocation = locationName;
  const forecasts = state.weatherData[locationName];
  if (!forecasts) return;

  const currentF = forecasts[state.currentSlotIndex] || forecasts[0];
  const drawer = document.getElementById('weatherDrawer');

  document.getElementById('drawerCityName').textContent = locationName;
  document.getElementById('drawerRegionBadge').textContent = `臺灣 • ${locationName}`;
  document.getElementById('drawerWeatherIcon').textContent = getWeatherIcon(currentF.weather);
  document.getElementById('drawerTempRange').textContent = `${currentF.min_temp}°C ~ ${currentF.max_temp}°C`;
  document.getElementById('drawerWeatherDesc').textContent = currentF.weather;
  document.getElementById('drawerPoP').textContent = currentF.pop !== null ? `${currentF.pop}%` : 'N/A';
  document.getElementById('drawerMinMax').textContent = `${currentF.min_temp}°C / ${currentF.max_temp}°C`;
  document.getElementById('drawerSlotIndex').textContent = `時段 ${state.currentSlotIndex + 1} (${currentF.start_time.slice(5, 16)})`;

  // Render 3-Slot mini cards
  const timelineContainer = document.getElementById('drawerTimeline');
  timelineContainer.innerHTML = forecasts.map((f, i) => `
    <div class="timeline-item ${i === state.currentSlotIndex ? 'active-slot' : ''}">
      <div>
        <div class="t-slot-name">時段 ${i + 1}</div>
        <div style="font-size:0.65rem; color:#94a3b8;">${f.start_time.slice(5, 16)}</div>
      </div>
      <div>${getWeatherIcon(f.weather)} ${f.weather}</div>
      <div class="t-slot-temp">${f.min_temp}°C ~ ${f.max_temp}°C</div>
      <div class="t-slot-pop">💧 ${f.pop}%</div>
    </div>
  `).join('');

  drawer.style.display = 'flex';
}

function setupEventListeners() {
  // Slot Switchers
  document.querySelectorAll('.slot-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.slot-btn').forEach((b) => b.classList.remove('active'));
      e.target.classList.add('active');
      state.currentSlotIndex = parseInt(e.target.dataset.slot, 10);
      
      updateTimeBanner();
      updateKpis();
      render3DTaiwanLocations();
      renderGeoJsonLayer();
      if (state.selectedLocation) {
        openWeatherDrawer(state.selectedLocation);
      }
    });
  });

  // Color Mode (Temp vs PoP)
  const modeTemp = document.getElementById('modeTemp');
  const modePop = document.getElementById('modePop');
  const legendTitle = document.getElementById('legendTitle');
  const legendScale = document.getElementById('legendScale');

  modeTemp.addEventListener('click', () => {
    modeTemp.classList.add('active');
    modePop.classList.remove('active');
    state.activeMode = 'temp';
    legendTitle.textContent = '氣溫色階 (°C)';
    legendScale.innerHTML = `
      <div class="scale-item"><span class="scale-color" style="background:#3b82f6;"></span> &lt; 24°C</div>
      <div class="scale-item"><span class="scale-color" style="background:#10b981;"></span> 24 ~ 27°C</div>
      <div class="scale-item"><span class="scale-color" style="background:#f59e0b;"></span> 27 ~ 30°C</div>
      <div class="scale-item"><span class="scale-color" style="background:#ef4444;"></span> 30 ~ 33°C</div>
      <div class="scale-item"><span class="scale-color" style="background:#8b5cf6;"></span> &gt; 33°C</div>
    `;
    renderGeoJsonLayer();
    render3DTaiwanLocations();
  });

  modePop.addEventListener('click', () => {
    modePop.classList.add('active');
    modeTemp.classList.remove('active');
    state.activeMode = 'pop';
    legendTitle.textContent = '降雨機率色階 (%)';
    legendScale.innerHTML = `
      <div class="scale-item"><span class="scale-color" style="background:#10b981;"></span> 0% (晴朗)</div>
      <div class="scale-item"><span class="scale-color" style="background:#06b6d4;"></span> 1 ~ 20%</div>
      <div class="scale-item"><span class="scale-color" style="background:#3b82f6;"></span> 21 ~ 50%</div>
      <div class="scale-item"><span class="scale-color" style="background:#6366f1;"></span> 51 ~ 80%</div>
      <div class="scale-item"><span class="scale-color" style="background:#8b5cf6;"></span> &gt; 80% (高降雨)</div>
    `;
    renderGeoJsonLayer();
    render3DTaiwanLocations();
  });

  // Toggles
  document.getElementById('toggleGeoJSON').addEventListener('change', (e) => {
    if (e.target.checked) {
      state.geoJsonLayer.addTo(state.map);
    } else {
      state.map.removeLayer(state.geoJsonLayer);
    }
  });

  document.getElementById('toggleMarkers').addEventListener('change', (e) => {
    if (e.target.checked) {
      state.markersLayer.addTo(state.map);
    } else {
      state.map.removeLayer(state.markersLayer);
    }
  });

  // County Search Dropdown
  const select = document.getElementById('countySelect');
  select.addEventListener('change', (e) => {
    const loc = e.target.value;
    if (loc && state.coordinates[loc]) {
      const c = state.coordinates[loc];
      state.map.flyTo([c.lat, c.lng], 9.2, { duration: 1 });
      openWeatherDrawer(loc);
    }
  });

  // Drawer Close
  document.getElementById('drawerCloseBtn').addEventListener('click', () => {
    document.getElementById('weatherDrawer').style.display = 'none';
  });
}

async function populateCountyDropdown() {
  const select = document.getElementById('countySelect');
  Object.keys(state.coordinates).sort().forEach((name) => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  });
}

// ==========================================================================
// Master Bootstrap Sequence (3A -> 3B -> 3C -> 3D -> 3E -> 3F -> 3G)
// ==========================================================================
async function main() {
  console.log('=== Starting Gate 3 Sequence ===');

  // 1. Initialize Map (3A)
  init3ATaiwanMap();

  // 2. Load Coordinates (3D Helper)
  const coordsRes = await fetch('/static/data/county_coordinates.json');
  state.coordinates = await coordsRes.json();
  populateCountyDropdown();

  // 3. Database to GIS (3E)
  const success = await load3EDatabaseToGIS();
  if (!success) {
    alert('無法從 SQLite 資料庫載入資料，請確認 Gate 2 已正確完成！');
    return;
  }

  // 4. One Marker & Weather Popup for Taichung City (3B & 3C)
  const tcForecast = state.weatherData['臺中市'] ? state.weatherData['臺中市'][0] : null;
  if (tcForecast) {
    init3BOneMarkerAndPopup(tcForecast);
  }

  // 5. Render All Taiwan Locations (3D)
  render3DTaiwanLocations();

  // 6. Render GeoJSON Boundaries (3F)
  await load3FTaiwanGeoJSON();

  // 7. Setup Interactive Controls & Default Drawer (3G)
  setupEventListeners();
  openWeatherDrawer('臺中市');

  console.log('=== Gate 3 Sequence (3A ~ 3G) Fully Operational ===');
}

window.addEventListener('DOMContentLoaded', main);
