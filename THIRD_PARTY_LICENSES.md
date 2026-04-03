# Third-Party License Verification

Before accepting AI-suggested code or new dependencies, verify the licenses of all third-party libraries used by the project.

## Project workflow
1. Review dependency changes in `requirements.txt` and `requirements-dev.txt`.
2. Run the checker:
   ```powershell
   .\.venv\Scripts\python.exe .\tools\check_licenses.py --fail-on-unknown
   ```
3. Manually review any package flagged as `REVIEW` before shipping.

## Current dependency set to monitor

| Package | Expected license family |
|---|---|
| `requests` | Apache-2.0 |
| `geopy` | MIT |
| `fastapi` | MIT |
| `uvicorn` | BSD/MIT-compatible |
| `jinja2` | BSD-3-Clause |
| `cryptography` | Apache-2.0 / BSD |
| `pytest` | MIT |
| `flake8` | MIT |

> This file is a compliance aid and not legal advice.
