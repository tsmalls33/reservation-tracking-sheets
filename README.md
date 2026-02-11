
# Reservation Tracking Sheets Automation

Automate processing and uploading of Airbnb and Booking.com reservation data to Google Sheets.

## 🚀 Quick Start

    # Process and upload in one command
    reservations oneshot your-booking-file.xls -a mediona -y 2025 --test -H

## 📋 Prerequisites

- Python 3.9+
- Google Cloud service account with Sheets API enabled
- Required Python packages: pandas, gspread, google-auth, xlrd, openpyxl, click

## 🛠️ Installation

    pip install -r requirements.txt
    chmod +x main.py

## 📂 Project Structure

    reservation-tracking-sheets/
    ├── config/
    │   ├── mediona_2025.json          # Production config
    │   └── mediona_2025_test.json     # Test config
    ├── credentials/
    │   └── service_account.json       # Google service account key
    ├── scripts/
    │   ├── process_airbnb.py          # Clean Airbnb exports
    │   ├── process_booking.py         # Clean Booking.com exports
    │   ├── merge_data.py              # Merge multiple sources
    │   └── upload_to_sheets.py        # Upload to Google Sheets
    ├── data/
    │   ├── raw/                       # Downloaded CSVs
    │   ├── processed/                 # Cleaned outputs
    │   └── temp/                      # Temporary files
    └── main.py                        # CLI entry point

## 🎯 Commands

### oneshot - All-in-One Processing & Upload

Process files and upload to Google Sheets in one command.

    reservations oneshot FILE [FILE...] -a APARTMENT -y YEAR [OPTIONS]

Arguments: FILE - One or more CSV/XLS/XLSX files to process

Options: -a, --apartment (required), -y, --year (default: 2026), --test (Use test config), -H, --hard-replace (Clear ALL tabs)

Examples:

    reservations oneshot booking.xls -a mediona -y 2025 --test -H
    reservations oneshot airbnb.csv booking.xlsx -a mediona -y 2025
    reservations oneshot data.csv -a mediona -y 2025 -H

### process - Process Only (No Upload)

    reservations process PLATFORM FILE [-o OUTPUT]

Arguments: PLATFORM (airbnb or booking), FILE (Path to raw export)

Options: -o, --output (Output path)

Examples:

    reservations process booking my-export.xls
    reservations process airbnb reservations.csv -o custom-output.csv

### upload - Upload Only (Pre-processed CSV)

    reservations upload FILE -a APARTMENT -y YEAR [OPTIONS]

Arguments: FILE (Path to processed CSV)

Options: -a, --apartment (required), -y, --year, --test, -H, --hard-replace

Examples:

    reservations upload processed.csv -a mediona -y 2025 --test

## 📊 Supported File Formats

✅ CSV (.csv) | ✅ Excel 97-2003 (.xls) | ✅ Excel 2007+ (.xlsx)

## 🏷️ Platform Detection

Automatically detects platform based on filename or content.

Airbnb: Filename/content contains airbnb, confirmación, hm

Booking.com: Filename/content contains booking, reservation, invoice

## 🔧 Configuration Files

JSON files define spreadsheet ID, tabs, ranges, and column mappings.

Example config/mediona_2025_test.json:

    {
      "spreadsheet_id": "your-spreadsheet-id",
      "tabs": {
        "january_reservations": {
          "tab_name": "January",
          "start_range": "F11",
          "columns": ["Actividad", "Pagado", "Entrada", "Salida", "Noches", "Precio", "Check In/Out", "Comision"]
        }
      }
    }

## 📝 Output Format

Columns: Actividad (Guest name + count), Entrada (Check-in YYYY-MM-DD), Salida (Check-out YYYY-MM-DD), Noches (Nights), Precio (Price, no currency), Check In/Out (Cleaning fee), Comision (Commission), VAT (Empty)

## 🎨 Features

Smart Processing: Auto-detects platform, handles multiple column formats, strips currency symbols, filters cancelled reservations, converts dates

Smart Upload: Auto-detects months, only clears affected tabs (unless -H), preserves formatting, detailed progress logs

## 🔐 Google Sheets Setup

1. Create Google Cloud project
2. Enable Google Sheets API
3. Create service account & download JSON key
4. Save as credentials/service_account.json
5. Share spreadsheet with service account email (editor access)

## 🐛 Troubleshooting

Config not found: Check naming {apartment}__{year}.json or {apartment}__{year}_test.json in config/

Worksheet not found: Verify tab names in config match Sheet (ignoring whitespace)

Column not found: Check error message for available columns

Emojis not displaying:

    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8

## 📖 Examples

Typical workflow:

    # Download export from Booking.com, then run:
    reservations oneshot ~/Downloads/booking_export.xls -a mediona -y 2025 --test -H
    # Output: ✓ Processing → ✓ Filtering → ✓ Uploading → ✓ Complete!

Multiple sources:

    reservations oneshot airbnb.csv booking.xls -a mediona -y 2025

## 📄 License

MIT

## 👤 Author

Thomas - Software Engineer in Barcelona
