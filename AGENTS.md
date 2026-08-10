# AGENTS.md — E-mail Processor

## Project Overview
Small Python utility that fetches telecom invoices (Iskon, Tomato) from Gmail, extracts attachments and barcodes, and uploads them to Google Drive. Runs automatically on the 10th working day of each month via GitHub Actions.

## Real Entrypoints
- **`iskon.py`** — Processes Iskon invoices (PDF/PNG attachments from `e-racun@iskon.hr`).
- **`tomato.py`** — Processes Tomato invoices (inline barcode images + PDFs from `moj.racun@tomato.com.hr`).
- **`check_10th_workday.py`** — Exits `0` if today is the 10th working day, `1` otherwise. Used by CI and cron.
- **`main.py`** — Stub/placeholder. Do not use as an entrypoint.

## Environment & Dependencies
- **Python**: `>=3.12` per `pyproject.toml` and `.python-version`.
- **Package manager**: `uv` (primary — `uv.lock` present). `requirements.txt` exists as fallback.
- **System deps required** (not installable via pip): `poppler-utils`, `libzbar0`.
  - Ubuntu/Debian: `sudo apt-get install poppler-utils libzbar0`
  - macOS: `brew install poppler zbar`

## Running Locally
```bash
# With uv (preferred)
uv run iskon.py
uv run tomato.py

# With pip/venv
pip install -r requirements.txt
python3 iskon.py
python3 tomato.py
```

## Known Code Issues (Agent Should Be Aware)
- **`tomato.py` hardcoded OAuth filename bug**: Line 51 references `'client_secret_544079871095-...googleusercontent.com'` **without `.json` extension**. `iskon.py` line 46 has the correct filename **with** `.json`. This is a real bug that will break Tomato auth on fresh runs.
- **`run_on_10th_workday.sh` is corrupted**: First line contains a malformed crontab entry merged into the shebang. It also references the old script name `iskon_invoice_processor.py` (does not exist anymore).
- **`main.py` is a stub**: Only prints a hello message. Do not treat it as the app entrypoint.

## Authentication & Secrets
- **OAuth scopes** (hardcoded in both scripts): Gmail readonly, Gmail send, Drive file.
- **Sensitive files** (gitignored, never commit):
  - `token.json` — generated after first interactive OAuth flow
  - `client_secret_544079871095-7eo15ghsvks1u43urcft84afblheu732.apps.googleusercontent.com.json` — downloaded from Google Cloud Console
- If `token.json` is deleted or scopes change, the next run will open a browser for interactive OAuth.

## GitHub Actions CI
- Workflow: `.github/workflows/process-invoices.yml`
- **Trigger**: Weekdays at 9:00 AM UTC (`cron: '0 9 * * 1-5'`) + manual `workflow_dispatch`.
- **Logic**: Checks 10th working day via `check_10th_workday.py`; if true, runs both processors.
- **CI Python version**: Uses 3.11 (note: project requires 3.12+ — this is a mismatch).
- **CI secrets required**: `GOOGLE_CLIENT_SECRET`, `GOOGLE_TOKEN_JSON`.
- **Tomato step** has `continue-on-error: true`, so CI won't fail if Tomato processing fails.

## Drive & Deduplication
- Drive folders are hardcoded: `"Iskon"` and `"Tomato"`.
- `tomato.py` checks for existing files by filename before uploading (skips duplicates). `iskon.py` does **not** deduplicate — it will upload duplicates.

## Working Day Logic
- `check_10th_workday.py` counts Monday–Friday only. **Does not account for public holidays**.

## Useful Commands
```bash
# Check if today is the 10th working day
python3 check_10th_workday.py

# Run individual processors
uv run iskon.py
uv run tomato.py
```
