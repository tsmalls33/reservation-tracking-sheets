#!/usr/bin/env python3
"""
Reservations CLI - Process and upload Airbnb/Booking data to Google Sheets

Supports multiple CSV files from Airbnb and Booking.com, automatically
detects platforms, processes data, and uploads to configured Google Sheets
with dynamic column mapping.
"""

import warnings
import os

# Suppress all warnings at startup
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

from cli import cli


if __name__ == '__main__':
    cli()
