# AGENTS.md — E-mail Processor

## Project Overview
Small Python utility that fetches telecom invoices (Iskon, Tomato) from Gmail, extracts attachments and barcodes, and uploads them to Google Drive. Runs automatically on the 10th working day of each month via GitHub Actions.

## Real Entrypoints
- **`main.py`** — Unified CLI entrypoint. Supports `python main.py iskon`, `python main.py tomato`, and `python main.py all`.
- **`iskon.py`** — Processes Iskon invoices (PDF/PNG attachments from `e-racun@iskon.hr`).
- **`tomato.py`** — Processes Tomato invoices (inline barcode images + PDFs from `moj.racun@tomato.com.hr`).
- **`check_10th_workday.py`** — Exits `0` if today is the 10th working day, `1` otherwise. Used by CI and cron.

## Shared Module
- **`google_services.py`** — Contains all common logic:
  - OAuth authentication (`authenticate`)
  - Gmail search with pagination (`search_emails`)
  - Attachment extraction (`get_attachments`)
  - Drive folder management (`get_or_create_drive_folder`)
  - Drive deduplication (`file_exists_in_drive`)
  - Drive upload (`upload_to_drive`)
  - Email notifications (`send_notification`)
  - Logging setup (`setup_logging`)

## Environment & Dependencies
- **Python**: `>=3.12` per `pyproject.toml` and `.python-version`.
- **Package manager**: `uv` (primary — `uv.lock` present). `requirements.txt` exists as fallback.
- **System deps required** (not installable via pip): `poppler-utils`, `libzbar0`.
  - Ubuntu/Debian: `sudo apt-get install poppler-utils libzbar0`
  - macOS: `brew install poppler zbar`

## Running Locally
```bash
# With uv (preferred)
uv run main.py all
uv run main.py iskon
uv run main.py tomato

# With pip/venv
pip install -r requirements.txt
python3 main.py all
```

## Known Code Issues (Agent Should Be Aware)
- **`check_10th_workday.py` does not account for public holidays**: It counts Monday–Friday only.
- **No automated token secret update in CI**: If `token.json` refreshes in GitHub Actions, the new token is lost when the job ends. Manual secret update is required, or switch to a Service Account for fully headless operation.

## Authentication & Secrets
- **OAuth scopes** (defined once in `google_services.py`): Gmail readonly, Gmail send, Drive file.
- **Sensitive files** (gitignored, never commit):
  - `token.json` — generated after first interactive OAuth flow
  - `client_secret_544079871095-7eo15ghsvks1u43urcft84afblheu732.apps.googleusercontent.com.json` — downloaded from Google Cloud Console
- If `token.json` is deleted or scopes change, the next run will open a browser for interactive OAuth.

## GitHub Actions CI
- Workflow: `.github/workflows/process-invoices.yml`
- **Trigger**: Weekdays at 9:00 AM UTC (`cron: '0 9 * * 1-5'`) + manual `workflow_dispatch`.
- **Logic**: Checks 10th working day via `check_10th_workday.py`; if true, runs both processors.
- **CI Python version**: Uses 3.12 (matches project requirement).
- **CI secrets required**: `GOOGLE_CLIENT_SECRET`, `GOOGLE_TOKEN_JSON`.
- Both processor steps now fail the workflow on error (no `continue-on-error`).

## Drive & Deduplication
- Drive folders are hardcoded: `"Iskon"` and `"Tomato"`.
- Both `iskon.py` and `tomato.py` now check for existing files by filename before uploading (skips duplicates). The deduplication logic lives in `google_services.py`.

## Working Day Logic
- `check_10th_workday.py` counts Monday–Friday only. **Does not account for public holidays**.

## Useful Commands
```bash
# Check if today is the 10th working day
python3 check_10th_workday.py

# Run unified entrypoint
uv run main.py all

# Run individual processors
uv run iskon.py
uv run tomato.py
```
