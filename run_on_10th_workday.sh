0 9 * * * /home/ivan/Documents/e-mail_processor/run_on_10th_workday.sh >> /tmp/iskon_cron.log 2>&10 9 * * * /home/ivan/Documents/e-mail_processor/run_on_10th_workday.sh >> /tmp/iskon_cron.log 2>&1#!/bin/bash
# Script to run iskon_invoice_processor.py on the 10th working day of each month

cd /home/ivan/Documents/e-mail_processor

# Calculate if today is the 10th working day of the month
CURRENT_YEAR=$(date +%Y)
CURRENT_MONTH=$(date +%m)
CURRENT_DAY=$(date +%d)

# Count working days from day 1 to current day
WORKING_DAYS=0
for ((day=1; day<=CURRENT_DAY; day++)); do
    # Get day of week (1=Monday, 7=Sunday)
    DAY_OF_WEEK=$(date -d "$CURRENT_YEAR-$CURRENT_MONTH-$day" +%u)
    
    # Count only Monday-Friday (1-5)
    if [ $DAY_OF_WEEK -le 5 ]; then
        WORKING_DAYS=$((WORKING_DAYS + 1))
    fi
done

# Run the script if today is the 10th working day
if [ $WORKING_DAYS -eq 10 ]; then
    echo "$(date): Today is the 10th working day - running iskon_invoice_processor.py"
    .venv/bin/python iskon_invoice_processor.py >> /tmp/iskon_processor.log 2>&1
else
    echo "$(date): Not the 10th working day (working day #$WORKING_DAYS) - skipping"
fi
