#!/usr/bin/env python3
"""
Check if today is the 10th working day of the current month.
Exits with code 0 if true, code 1 if false.
"""

import sys
from datetime import date, timedelta


def is_weekday(d: date) -> bool:
    """Check if date is a weekday (Monday=0 to Friday=4)."""
    return d.weekday() < 5


def count_working_days_until(target_date: date) -> int:
    """Count working days from start of month until target date (inclusive)."""
    year = target_date.year
    month = target_date.month
    
    working_days = 0
    current = date(year, month, 1)
    
    while current <= target_date:
        if is_weekday(current):
            working_days += 1
        current += timedelta(days=1)
    
    return working_days


def main():
    today = date.today()
    working_day_count = count_working_days_until(today)
    
    print(f"Today is {today.strftime('%Y-%m-%d')}")
    print(f"Working day #{working_day_count} of the month")
    
    if working_day_count == 10:
        print("✓ This is the 10th working day!")
        sys.exit(0)
    else:
        print("✗ Not the 10th working day")
        sys.exit(1)


if __name__ == "__main__":
    main()
