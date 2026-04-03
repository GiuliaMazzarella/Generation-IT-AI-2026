# Privacy & Data Handling

This app processes the **city name** entered by the user to retrieve weather data from external services.

## What is sent to third parties
- `Nominatim` (via `geopy`) receives the city name for geocoding.
- `Open-Meteo` receives latitude/longitude to return weather and forecast data.

## Consent
- **Web UI**: searches stay disabled until the user explicitly accepts the privacy notice.
- **CLI**: the app asks for consent before the first network request unless `WEATHER_USER_CONSENT=1` is already set.

## Data minimization
- Persistent cache is **disabled by default**.
- To enable local disk cache explicitly, set `WEATHER_ENABLE_PERSISTENT_CACHE=1`.
- Cache files are ignored by Git (`.weather_cache.pkl`, `.geocode_cache.pkl`).

## Sensitive information protection
- Store admin secrets in the environment using `WEATHER_ADMIN_TOKEN`.
- For encrypted local secret storage, also set `WEATHER_ENCRYPTION_KEY`; the app will use `.admin_token.enc` instead of plain text.

## Operational note
This repository is intended for local development/demo use. If deployed publicly, place it behind HTTPS and manage secrets with a proper secret manager.
