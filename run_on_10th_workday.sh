#!/bin/bash
# Script to run invoice processors on the 10th working day of each month
# Delegates to check_10th_workday.py for working-day calculation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="/tmp/invoice_processor.log"

# Check if today is the 10th working day
if python3 check_10th_workday.py >> "$LOG_FILE" 2>&1; then
    echo "$(date): Today is the 10th working day — running processors" | tee -a "$LOG_FILE"
    uv run iskon.py >> "$LOG_FILE" 2>&1
    uv run tomato.py >> "$LOG_FILE" 2>&1
else
    echo "$(date): Not the 10th working day — skipping" | tee -a "$LOG_FILE"
fi
