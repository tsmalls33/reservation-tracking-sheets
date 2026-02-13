# Installation Guide

After pulling the refactored code, you need to reinstall the package in development mode.

## Quick Fix

```bash
cd ~/dev/reservation-tracking-sheets
git checkout chore/clean-up-code
git pull
pip install -e .
```

## What This Does

The `-e` flag installs the package in "editable" mode, which:
- Creates links to your source code instead of copying it
- Allows you to make changes without reinstalling
- Makes the `cli` package importable from anywhere

## Verify Installation

```bash
reservations --help
```

You should see:

```
Usage: reservations [OPTIONS] COMMAND [ARGS]...

  Reservation Tracking System - Automate Airbnb/Booking data to Google
  Sheets.

  This tool processes reservation CSVs from Airbnb and Booking.com, then
  uploads them to Google Sheets with dynamic column mapping based on your
  configuration.

  ...
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'cli'"

This means the package isn't installed. Run:

```bash
cd ~/dev/reservation-tracking-sheets
pip install -e .
```

### "command not found: reservations"

The package isn't installed at all. Run:

```bash
cd ~/dev/reservation-tracking-sheets
pip install -e .
```

Make sure you're using the correct Python environment (if you use virtual environments).

### Check Installation

Verify the package is installed:

```bash
pip show reservations
```

Should show:
```
Name: reservations
Version: 2.0.0
Location: /Users/thomas/dev/reservation-tracking-sheets
...
```

## Development Workflow

With editable install (`-e`):
1. Make changes to any file in `cli/` or `main.py`
2. Changes take effect immediately
3. No need to reinstall
4. Just run `reservations` command as normal

## Uninstalling

If needed:

```bash
pip uninstall reservations
```
