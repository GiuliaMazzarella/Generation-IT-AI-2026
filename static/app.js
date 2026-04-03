// Global error handlers: surface JS runtime errors to the status element for debugging
window.addEventListener('error', function (ev) {
  try {
    const st = document.getElementById('status');
    if (st) {
      st.classList.remove('hidden');
      st.textContent = 'Errore JS: ' + (ev.message || (ev.error && ev.error.message) || 'unknown');
    }
  } catch (e) {
    console.error('error handler failed', e);
  }
  console.error('Window error', ev.error || ev.message, ev);
});

window.addEventListener('unhandledrejection', function (ev) {
  try {
    const st = document.getElementById('status');
    if (st) {
      st.classList.remove('hidden');
      st.textContent = 'Unhandled Rejection: ' + ((ev.reason && ev.reason.message) || ev.reason || 'unknown');
    }
  } catch (e) {
    console.error('rejection handler failed', e);
  }
  console.error('Unhandled rejection', ev.reason);
});

// Debounce utility
function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function fmtAge(seconds) {
  if (seconds == null) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
}

// Format ISO timestamp to a human-friendly, locale-aware string
function formatDateTime(iso) {
  if (!iso) return 'N/D';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) {
      const alt = iso.replace(' ', 'T') + (iso.endsWith('Z') ? '' : 'Z');
      const d2 = new Date(alt);
      if (!isNaN(d2.getTime()))
        return d2.toLocaleString(navigator.language, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
      return iso;
    }
    return d.toLocaleString(navigator.language, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch (e) {
    return iso;
  }
}

// Format ISO timestamp explicitly in UTC
function formatUTC(iso) {
  if (!iso) return 'N/D';
  try {
    let s = iso;
    if (!s.endsWith('Z') && !/([\+\-]\d{2}:?\d{2})$/.test(s)) s = s + 'Z';
    const d = new Date(s);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('it-IT', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
      timeZoneName: 'short',
    });
  } catch (e) {
    return iso;
  }
}

// Elements
const cityInput = document.getElementById('city');
const themeToggle = document.getElementById('themeToggle');
const cityChips = document.getElementById('cityChips');
const cardsGrid = document.getElementById('cardsGrid');
const cityCardTpl = document.getElementById('cityCardTpl');
const searchBtn = document.getElementById('searchBtn');
const statusEl = document.getElementById('status');
const onlineBanner = document.getElementById('onlineBanner');
const privacyNotice = document.getElementById('privacyNotice');
const privacyStatus = document.getElementById('privacyStatus');
const consentAcceptBtn = document.getElementById('consentAccept');
const consentRejectBtn = document.getElementById('consentReject');
const tabSingle = document.getElementById('tabSingle');
const tabMulti = document.getElementById('tabMulti');
const tabForecast = document.getElementById('tabForecast');
const singleResult = document.getElementById('singleResult');
const s_temp = document.getElementById('s_temp');
const s_condition = document.getElementById('s_condition');
const s_location = document.getElementById('s_location');
const s_metaBadge = document.getElementById('s_metaBadge');
const s_age = document.getElementById('s_age');
const s_wind = document.getElementById('s_wind');
const s_tempDetail = document.getElementById('s_tempDetail');
const s_time = document.getElementById('s_time');
const s_details = document.getElementById('s_details');
const s_sea = document.getElementById('s_sea');
const s_sea_detail = document.getElementById('s_sea_detail');
const forecastResult = document.getElementById('forecastResult');
const forecastLocation = document.getElementById('f_location');
const forecastDaysContainer = document.getElementById('f_days');
const searchInputWrapper = document.querySelector('.search-input-wrapper');
const forecastDaysSelect = document.getElementById('forecastDays');

let mode = 'single'; // 'single' or 'multi'

function getStoredPrivacyConsent() {
  try {
    return localStorage.getItem('weather_privacy_consent') || '';
  } catch (e) {
    return '';
  }
}

function hasPrivacyConsent() {
  return getStoredPrivacyConsent() === 'accepted';
}

function updateSearchAvailability() {
  const online = navigator.onLine;
  onlineBanner.classList.toggle('hidden', online);
  searchBtn.disabled = !online || !hasPrivacyConsent();
}

function updatePrivacyUI() {
  const consented = hasPrivacyConsent();
  if (privacyNotice) privacyNotice.classList.toggle('hidden', consented);
  if (privacyStatus) {
    privacyStatus.textContent = consented
      ? 'Consenso privacy registrato per questo browser.'
      : 'Per cercare il meteo devi prima accettare l’informativa privacy.';
  }
  updateSearchAvailability();
}

function setPrivacyConsent(state) {
  try {
    localStorage.setItem('weather_privacy_consent', state);
  } catch (e) {
    console.warn('Unable to persist privacy consent', e);
  }
  updatePrivacyUI();
}

function setOnline() {
  updateSearchAvailability();
}
setOnline();
window.addEventListener('online', setOnline);
window.addEventListener('offline', setOnline);

function applyTheme(name) {
  if (name === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  else document.documentElement.removeAttribute('data-theme');
  themeToggle.textContent = name === 'dark' ? '☀️' : '🌙';
}

// Helper to consistently show/hide elements
function showElement(el) {
  if (!el) return;
  el.classList.remove('hidden');
  el.style.display = '';
}
function hideElement(el) {
  if (!el) return;
  el.classList.add('hidden');
  el.style.display = 'none';
}

function setForecastDaysSelectVisible(visible) {
  if (!forecastDaysSelect) return;
  if (visible) {
    forecastDaysSelect.classList.remove('hidden');
    forecastDaysSelect.style.display = '';
  } else {
    forecastDaysSelect.classList.add('hidden');
    forecastDaysSelect.style.display = 'none';
  }
}

function setSearchLayoutForMode(isForecastMode) {
  if (!searchInputWrapper) return;
  searchInputWrapper.classList.toggle('forecast-layout', !!isForecastMode);
}

function isCityNotFoundError(status, detail) {
  if (status === 404) return true;
  if (!detail || typeof detail !== 'string') return false;
  const normalized = detail.toLowerCase();
  return normalized.includes('city not found')
    || normalized.includes('città non trovata')
    || normalized.includes('not found')
    || normalized.includes('geocodingnotfound')
    || normalized.includes('invalid city')
    || normalized.includes('invalid city name');
}

function friendlyCityErrorMessage(city) {
  const value = (city || '').trim() || 'quello che hai scritto';
  return `Ops 😄 "${value}" sembra una città inventata. Scrivimi una città vera e ti mostro subito il meteo.`;
}

function friendlyWeatherUnavailableMessage(city) {
  const value = (city || '').trim() || 'questa città';
  return `Ci scusiamo per l'inconveniente 🛶 Sappiamo che "${value}" esiste, ma purtroppo non abbiamo la barca giusta per arrivarci. Riprova tra poco!`;
}

function mapWeatherCode(code) {
  const m = {
    0: { label: 'Sereno', icon: '☀️' },
    1: { label: 'Poco nuvoloso', icon: '🌤️' },
    2: { label: 'Parz. nuvoloso', icon: '⛅' },
    3: { label: 'Nuvoloso', icon: '☁️' },
    45: { label: 'Nebbia', icon: '🌫️' },
    48: { label: 'Deposito ghiaccio', icon: '🌫️' },
    51: { label: 'Pioviggine leggera', icon: '🌦️' },
    53: { label: 'Pioviggine', icon: '🌦️' },
    55: { label: 'Pioviggine intensa', icon: '🌧️' },
    61: { label: 'Pioggia', icon: '🌧️' },
    63: { label: 'Pioggia moderata', icon: '🌧️' },
    65: { label: 'Pioggia intensa', icon: '🌧️' },
    71: { label: 'Neve debole', icon: '🌨️' },
    73: { label: 'Neve', icon: '❄️' },
    75: { label: 'Neve intensa', icon: '❄️' },
    95: { label: 'Temporale', icon: '⛈️' },
    96: { label: 'Temporale con grandine', icon: '⛈️' },
  };
  return Object.prototype.hasOwnProperty.call(m, code) ? m[code] : { label: String(code), icon: '❓' };
}

function loadSavedTheme() {
  try {
    const saved = localStorage.getItem('weather_theme');
    if (saved) applyTheme(saved);
    else {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      applyTheme(prefersDark ? 'dark' : 'light');
    }
  } catch (e) {
    applyTheme('light');
  }
}

themeToggle.addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const next = cur === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem('weather_theme', next); } catch (e) { /* ignore */ }
});

function clearResultUI() {
  cardsGrid.innerHTML = '';
  cityChips.innerHTML = '';
}

function clearSingleResultData() {
  s_temp.textContent = '--°C';
  s_condition.textContent = '--';
  s_location.textContent = '';
  s_wind.textContent = '-- km/h';
  s_tempDetail.textContent = '--°C';
  s_time.textContent = '--';
  s_age.textContent = '';
  s_metaBadge.classList.add('hidden');
  s_details.classList.add('hidden');
  if (s_sea) s_sea.textContent = '';
  if (s_sea_detail) s_sea_detail.classList.add('hidden');
}

function clearForecastResultData() {
  if (forecastDaysContainer) forecastDaysContainer.innerHTML = '';
  if (forecastLocation) forecastLocation.textContent = 'Previsioni';
  hideElement(forecastResult);
}

function clearAllResultsForTabSwitch() {
  clearResultUI();
  clearSingleResultData();
  clearForecastResultData();
  cityInput.value = '';
  statusEl.classList.add('hidden');
  statusEl.textContent = '';
}

function makeChip(name) {
  const span = document.createElement('span');
  span.className = 'chip';
  span.textContent = name;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.title = 'Rimuovi città';
  btn.textContent = '×';
  btn.addEventListener('click', () => {
    span.remove();
    const cards = cardsGrid.querySelectorAll('.card');
    for (const c of cards) {
      if (c.getAttribute('data-city') === name) { c.remove(); break; }
    }
  });
  span.appendChild(btn);
  return span;
}

async function fetchForCity(name) {
  const card = cityCardTpl.content.cloneNode(true);
  const el = card.querySelector('.card');
  el.setAttribute('data-city', name);
  cardsGrid.appendChild(el);

  const temp = el.querySelector('.temp');
  const cond = el.querySelector('.condition');
  const loc = el.querySelector('.location');
  const wind = el.querySelector('.wind');
  const tempD = el.querySelector('.tempDetail');
  const time = el.querySelector('.time');
  const metaB = el.querySelector('.metaBadge');

  temp.textContent = '--°C';
  cond.textContent = '--';
  loc.textContent = name;

  try {
    const resp = await fetch(`/api/weather?city=${encodeURIComponent(name)}`);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const detail = err && typeof err.detail === 'string' ? err.detail : '';
      if (isCityNotFoundError(resp.status, detail)) {
        cond.textContent = 'Città non trovata';
      } else {
        cond.textContent = 'Errore';
      }
      return;
    }

    const body = await resp.json();
    const data = body.data || {};
    const cw = data.current_weather || {};

    try {
      const cardIcon = el.querySelector('.weather-icon');
      if (cardIcon) {
        const code = cw.weathercode != null ? cw.weathercode : null;
        const map = code != null ? mapWeatherCode(code) : null;
        cardIcon.textContent = map ? map.icon : '❓';
      }
    } catch (e) { /* non-fatal */ }

    const sea = data.sea || (cw && cw.sea) || null;

    const mappedCondition = cw.condition || (cw.weathercode != null ? mapWeatherCode(cw.weathercode).label : '--');

    temp.textContent = (cw.temperature != null) ? `${cw.temperature}°C` : 'N/D';
    cond.textContent = mappedCondition || '--';
    wind.textContent = (cw.windspeed != null) ? `${cw.windspeed} km/h` : 'N/D';
    tempD.textContent = (cw.temperature != null) ? `${cw.temperature}°C` : 'N/D';

    const localIso = cw.time_local || cw.time;
    let localDisplay = null;
    if (localIso) localDisplay = formatDateTime(localIso);
    else if (cw.time_local_formatted) localDisplay = cw.time_local_formatted;
    time.textContent = localDisplay || 'N/D';

    const seaEl = el.querySelector('.sea');
    if (sea && seaEl) {
      const parts = [];
      if (sea.wave_height != null) parts.push(`${sea.wave_height} m`);
      if (sea.wave_period != null) parts.push(`${sea.wave_period} s`);
      if (sea.wave_direction != null) parts.push(`${sea.wave_direction}°`);
      seaEl.textContent = parts.join(' • ');
      seaEl.parentElement && seaEl.parentElement.classList.remove('hidden');
    } else if (seaEl) {
      seaEl.textContent = '';
      seaEl.parentElement && seaEl.parentElement.classList.add('hidden');
    }

    const meta = data._meta || {};
    const age = el.querySelector('.age');
    age.textContent = `aggiornato: ${fmtAge(meta.age_seconds)}`;

    metaB.classList.remove('hidden');
    if (meta.source === 'stale') metaB.classList.add('stale');
    else if (meta.source === 'live') metaB.classList.add('live');
    else metaB.classList.add('cached');
    metaB.textContent = meta.source || 'cached';

    el.querySelector('.details').classList.remove('hidden');
  } catch (e) {
    console.error('fetchForCity error', e);
    if (!cond.textContent || cond.textContent === '--' || cond.textContent === '') cond.textContent = 'Errore';
    statusEl.classList.remove('hidden');
    statusEl.textContent = `Errore nel recuperare i dati per ${name}`;
  }
}

async function fetchSingleCity(name) {
  if (!name || !name.trim()) return;
  statusEl.classList.remove('hidden');
  statusEl.textContent = 'Caricamento...';
  singleResult.classList.add('hidden');

  try {
    const resp = await fetch(`/api/weather?city=${encodeURIComponent(name)}`);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const detail = err && typeof err.detail === 'string' ? err.detail : '';
      statusEl.classList.remove('hidden');
      if (isCityNotFoundError(resp.status, detail)) {
        statusEl.textContent = friendlyCityErrorMessage(name);
      } else {
        statusEl.textContent = friendlyWeatherUnavailableMessage(name);
      }
      return;
    }

    const body = await resp.json();
    const data = body.data || {};
    const cw = data.current_weather || {};

    const mappedCondition = cw.condition || (cw.weathercode != null ? mapWeatherCode(cw.weathercode).label : '--');

    s_temp.textContent = (cw.temperature != null) ? `${cw.temperature}°C` : '--°C';
    s_condition.textContent = mappedCondition || '--';
    s_location.textContent = name;
    s_wind.textContent = (cw.windspeed != null) ? `${cw.windspeed} km/h` : '-- km/h';
    s_tempDetail.textContent = (cw.temperature != null) ? `${cw.temperature}°C` : '--°C';

    const s_local_iso = cw.time_local || cw.time;
    let s_local = null;
    if (s_local_iso) s_local = formatDateTime(s_local_iso);
    else if (cw.time_local_formatted) s_local = cw.time_local_formatted;
    s_time.textContent = s_local || '--';

    const s_sea_el = document.getElementById('s_sea');
    const s_sea = data.sea || (cw && cw.sea) || null;
    if (s_sea && s_sea_el) {
      const p = [];
      if (s_sea.wave_height != null) p.push(`${s_sea.wave_height} m`);
      if (s_sea.wave_period != null) p.push(`${s_sea.wave_period} s`);
      if (s_sea.wave_direction != null) p.push(`${s_sea.wave_direction}°`);
      s_sea_el.textContent = p.join(' • ');
      s_sea_el.parentElement && s_sea_el.parentElement.classList.remove('hidden');
    } else if (s_sea_el) {
      s_sea_el.textContent = '';
      s_sea_el.parentElement && s_sea_el.parentElement.classList.add('hidden');
    }

    const meta = data._meta || {};
    s_age.textContent = `aggiornato: ${fmtAge(meta.age_seconds)}`;
    s_metaBadge.classList.remove('hidden');
    s_metaBadge.textContent = meta.source || 'cached';
    s_details.classList.remove('hidden');
    showElement(singleResult);
    statusEl.classList.add('hidden');
    statusEl.textContent = '';

    const s_icon = document.getElementById('s_icon');
    if (s_icon) {
      const sc = cw.weathercode != null ? cw.weathercode : null;
      const sm = sc != null ? mapWeatherCode(sc) : null;
      s_icon.textContent = sm ? sm.icon : '❓';
    }
  } catch (e) {
    console.error('fetchSingleCity error', e);
    statusEl.classList.remove('hidden');
    statusEl.textContent = friendlyWeatherUnavailableMessage(name);
  }
}

async function fetchForecast(name, days = 7) {
  if (!name || !name.trim()) return;
  statusEl.classList.remove('hidden');
  statusEl.textContent = 'Caricamento previsioni...';

  try {
    const selDays = (forecastDaysSelect && forecastDaysSelect.value) ? Number(forecastDaysSelect.value) : days;
    const resp = await fetch(`/api/forecast?city=${encodeURIComponent(name)}&days=${encodeURIComponent(selDays)}`);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const detail = err && typeof err.detail === 'string' ? err.detail : '';
      statusEl.classList.remove('hidden');
      if (isCityNotFoundError(resp.status, detail)) {
        statusEl.textContent = friendlyCityErrorMessage(name);
      } else {
        statusEl.textContent = friendlyWeatherUnavailableMessage(name);
      }
      return;
    }

    const body = await resp.json();
    const data = body.data || {};
    const daily = data.daily || {};
    const dates = daily.time || [];
    const tmax = daily.temperature_2m_max || [];
    const tmin = daily.temperature_2m_min || [];
    const wcode = daily.weathercode || [];

    const container = document.getElementById('f_days');
    container.innerHTML = '';
    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    table.innerHTML = `<thead><tr><th style="text-align:left;padding:8px;border-bottom:1px solid rgba(0,0,0,0.08)">Data</th><th style="text-align:left;padding:8px;border-bottom:1px solid rgba(0,0,0,0.08)">Massima</th><th style="text-align:left;padding:8px;border-bottom:1px solid rgba(0,0,0,0.08)">Minima</th><th style="text-align:left;padding:8px;border-bottom:1px solid rgba(0,0,0,0.08)">Cond.</th></tr></thead>`;
    const tbody = document.createElement('tbody');
    const n = Math.min(dates.length, selDays);

    for (let i = 0; i < n; i++) {
      const tr = document.createElement('tr');
      const mapped = mapWeatherCode(wcode[i]);
      tr.innerHTML = `
        <td style="padding:8px;border-bottom:1px solid rgba(0,0,0,0.04)">${new Date(dates[i]).toLocaleDateString()}</td>
        <td style="padding:8px;border-bottom:1px solid rgba(0,0,0,0.04)">${tmax[i] ?? '--'}°C</td>
        <td style="padding:8px;border-bottom:1px solid rgba(0,0,0,0.04)">${tmin[i] ?? '--'}°C</td>
        <td style="padding:8px;border-bottom:1px solid rgba(0,0,0,0.04)"><span class='weather-icon' style='font-size:18px;margin-right:6px'>${mapped.icon}</span>${mapped.label}</td>
      `;
      tbody.appendChild(tr);
    }

    table.appendChild(tbody);
    container.appendChild(table);
    document.getElementById('f_location').textContent = `Previsioni per ${name} (prossimi ${n} giorni)`;
    showElement(document.getElementById('forecastResult'));
    statusEl.classList.add('hidden');
    statusEl.textContent = '';
  } catch (e) {
    console.error('fetchForecast error', e);
    statusEl.textContent = 'Impossibile recuperare le previsioni.';
  }
}

// Input filter for single mode: allow only letters, spaces, apostrophe and hyphen
let singleFilterEnabled = false;
function enableSingleInputFilter() {
  if (singleFilterEnabled) return;
  singleFilterEnabled = true;
  cityInput.addEventListener('input', singleInputFilter);
}
function disableSingleInputFilter() {
  if (!singleFilterEnabled) return;
  singleFilterEnabled = false;
  cityInput.removeEventListener('input', singleInputFilter);
}

function singleInputFilter(e) {
  const v = e.target.value;
  // Allow only letters (all languages), spaces, apostrophe and hyphen
  const cleaned = v.replace(/[^\p{L}\s'\-]+/gu, '');
  if (cleaned !== v) {
    const pos = (e.target.selectionStart || 0) - (v.length - cleaned.length);
    e.target.value = cleaned;
    try {
      e.target.setSelectionRange(pos, pos);
    } catch (err) { /* ignore */ }
  }
}

function parseCities(input) {
  if (!input || !input.trim()) return [];
  const raw = input.trim();
  if (/[;,\n]/.test(raw)) {
    return raw.split(/[;,\n]+/).map(s => s.trim()).filter(Boolean);
  }

  const results = [];
  const quoteRe = /"([^"]+)"|'([^']+)'/g;
  let m; let remaining = raw;
  while ((m = quoteRe.exec(raw)) !== null) {
    const phrase = m[1] || m[2];
    if (phrase) {
      results.push(phrase.trim());
      remaining = remaining.replace(m[0], ' ');
    }
  }

  const tokens = remaining.trim().split(/\s+/).map(s => s.trim()).filter(Boolean);
  for (const t of tokens) results.push(t);
  return results.map(s => s.trim()).filter(Boolean);
}

document.getElementById('clearInput').addEventListener('click', () => {
  cityInput.value = '';
  clearResultUI();
  statusEl.classList.add('hidden');
});

if (consentAcceptBtn) {
  consentAcceptBtn.addEventListener('click', () => {
    setPrivacyConsent('accepted');
    statusEl.classList.add('hidden');
    statusEl.textContent = '';
  });
}

if (consentRejectBtn) {
  consentRejectBtn.addEventListener('click', () => {
    setPrivacyConsent('rejected');
    statusEl.classList.remove('hidden');
    statusEl.textContent = 'Consenso non concesso: la ricerca meteo resta disabilitata.';
  });
}

searchBtn.addEventListener('click', async () => {
  if (!hasPrivacyConsent()) {
    statusEl.textContent = 'Accetta prima l’informativa privacy per inviare la città ai servizi meteo esterni.';
    statusEl.classList.remove('hidden');
    if (privacyNotice) privacyNotice.classList.remove('hidden');
    return;
  }

  if (mode === 'single') {
    const city = cityInput.value.trim();
    if (!city) {
      statusEl.textContent = 'Inserisci una città.';
      statusEl.classList.remove('hidden');
      return;
    }
    statusEl.classList.add('hidden');
    clearResultUI();
    fetchSingleCity(city);
    return;
  }

  if (mode === 'forecast') {
    const city = cityInput.value.trim();
    if (!city) {
      statusEl.textContent = 'Inserisci una città.';
      statusEl.classList.remove('hidden');
      return;
    }
    clearResultUI();
    const selDays = (forecastDaysSelect && forecastDaysSelect.value) ? Number(forecastDaysSelect.value) : 7;
    fetchForecast(city, selDays);
    return;
  }

  const cities = parseCities(cityInput.value);
  clearResultUI();
  if (cities.length === 0) {
    statusEl.textContent = 'Nessuna città trovata.';
    statusEl.classList.remove('hidden');
    return;
  }

  const MAX_MULTI = 3;
  if (cities.length > MAX_MULTI) {
    statusEl.textContent = `Hai inserito ${cities.length} città; verranno mostrate solo le prime ${MAX_MULTI}.`;
    statusEl.classList.remove('hidden');
  } else {
    statusEl.classList.add('hidden');
  }

  const toUse = cities.slice(0, MAX_MULTI);
  searchBtn.disabled = true;
  try {
    for (let i = 0; i < toUse.length; i++) {
      const city = toUse[i];
      statusEl.classList.remove('hidden');
      statusEl.textContent = `Caricamento confronto: città ${i + 1}/${toUse.length} (${city})...`;

      const chip = makeChip(city);
      cityChips.appendChild(chip);
      await fetchForCity(city);
      // Space requests to avoid geocoding burst/rate-limit in compare mode.
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }

    statusEl.classList.add('hidden');
    statusEl.textContent = '';
  } finally {
    searchBtn.disabled = !navigator.onLine;
  }
});

cityInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') { e.preventDefault(); searchBtn.click(); } });
cityInput.addEventListener('keydown', (e) => { if ((mode === 'single' || mode === 'forecast') && (e.key === ',' || e.key === ';')) { e.preventDefault(); } });
cityInput.addEventListener('paste', (e) => {
  if (mode === 'single' || mode === 'forecast') {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text') || '';
    const cleaned = text.replace(/[;,\n]/g, ' ');
    const start = cityInput.selectionStart || 0;
    const end = cityInput.selectionEnd || 0;
    const v = cityInput.value;
    cityInput.value = v.slice(0, start) + cleaned + v.slice(end);
  }
});

function switchToSingleMode() {
  mode = 'single';
  clearAllResultsForTabSwitch();
  tabSingle.classList.add('active'); tabMulti.classList.remove('active'); tabForecast.classList.remove('active');
  // hide grid and forecast; show single result only after a successful search
  hideElement(singleResult);
  hideElement(cardsGrid);
  const forecastArea = document.getElementById('forecastResult'); if (forecastArea) hideElement(forecastArea);
  setForecastDaysSelectVisible(false);
  setSearchLayoutForMode(false);
  enableSingleInputFilter();
  const hint = document.getElementById('inputHint'); if (hint) hint.style.display = 'none';
  cityInput.placeholder = 'Inserisci una città';
}

function switchToMultiMode() {
  mode = 'multi';
  clearAllResultsForTabSwitch();
  tabSingle.classList.remove('active'); tabMulti.classList.add('active'); tabForecast.classList.remove('active');
  // show cards grid, hide single and forecast
  hideElement(singleResult);
  showElement(cardsGrid);
  const forecastArea = document.getElementById('forecastResult'); if (forecastArea) hideElement(forecastArea);
  setForecastDaysSelectVisible(false);
  setSearchLayoutForMode(false);
  disableSingleInputFilter();
  const hint = document.getElementById('inputHint'); if (hint) hint.style.display = 'block';
  cityInput.placeholder = 'Inserisci città (es: Milano, Roma)';
}

function switchToForecastMode() {
  mode = 'forecast';
  clearAllResultsForTabSwitch();
  tabSingle.classList.remove('active'); tabMulti.classList.remove('active'); tabForecast.classList.add('active');
  // keep result panels hidden; forecast appears only after a search
  hideElement(singleResult);
  hideElement(cardsGrid);
  const forecastArea = document.getElementById('forecastResult'); if (forecastArea) hideElement(forecastArea);
  setForecastDaysSelectVisible(true);
  setSearchLayoutForMode(true);
  enableSingleInputFilter();
  const hint = document.getElementById('inputHint'); if (hint) hint.style.display = 'none';
  cityInput.placeholder = 'Inserisci una città per le previsioni';
}

tabSingle.addEventListener('click', switchToSingleMode);
tabMulti.addEventListener('click', switchToMultiMode);
tabForecast.addEventListener('click', switchToForecastMode);

// Initialize UI
switchToSingleMode();
const hintInit = document.getElementById('inputHint'); if (hintInit) hintInit.style.display = 'none';
loadSavedTheme();
updatePrivacyUI();
