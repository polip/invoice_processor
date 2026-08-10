#!/usr/bin/env python3
"""
Unified entrypoint for invoice processors.

Usage:
    python main.py iskon
    python main.py tomato
    python main.py all
"""

import argparse
import logging
import sys

import iskon
import tomato
from google_services import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process telecom invoices from Gmail and upload to Google Drive."
    )
    parser.add_argument(
        "provider",
        choices=["iskon", "tomato", "all"],
        help="Which provider to process (or 'all' for both)",
    )
    args = parser.parse_args()

    setup_logging()

    if args.provider in ("iskon", "all"):
        logger.info("=== Running Iskon processor ===")
        try:
            iskon.main()
        except Exception:
            logger.exception("Iskon processor failed")
            if args.provider == "iskon":
                sys.exit(1)

    if args.provider in ("tomato", "all"):
        logger.info("=== Running Tomato processor ===")
        try:
            tomato.main()
        except Exception:
            logger.exception("Tomato processor failed")
            if args.provider == "tomato":
                sys.exit(1)

    logger.info("=== Processing complete ===")


if __name__ == "__main__":
    main()
