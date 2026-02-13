# Data Management

How the application manages temporary and permanent data files.

## Directory Structure

```
reservation-tracking-sheets/
├── data/
│   └── temp/              # Temporary files (auto-deleted)
├── config/               # Permanent configuration files
├── invoices/             # Generated invoice metadata
└── credentials/          # Service account credentials
```

## Data Folders

### `data/temp/` - Temporary Processing Files

**Purpose**: Stores intermediate CSV files during processing

**Contents**:
- `*_airbnb_processed.csv` - Processed Airbnb exports
- `*_booking_processed.csv` - Processed Booking.com exports
- `*_merged.csv` - Merged files when multiple CSVs provided

**Lifecycle**: 
- Created during `upload` command
- **Automatically deleted** after upload completes (success or failure)
- Not tracked in git (ignored in `.gitignore`)

**Why deleted**:
- No value in keeping processed CSVs
- Original CSVs are the source of truth
- Saves disk space
- Prevents confusion with outdated data

### Removed Folders

Previously used `data/raw/` and `data/processed/` folders have been removed. All processing now uses `data/temp/` with automatic cleanup.

## Upload Workflow

```
1. User runs: reservations upload airbnb.csv booking.csv -a downtown-loft

2. Create temp folder:
   data/temp/

3. Process files:
   data/temp/airbnb_airbnb_processed.csv
   data/temp/booking_booking_processed.csv

4. Merge (if multiple):
   data/temp/downtown-loft_2026_merged.csv

5. Upload to Google Sheets:
   ✅ Data uploaded successfully

6. Cleanup (automatic):
   🧹 data/temp/ deleted
   ✅ No files left behind
```

## Permanent Data

### `config/` - Configuration Files

**Never deleted**. Contains:
- `{apartment}_{year}.json` - Apartment/year configurations
- `{apartment}_{year}_test.json` - Test configurations
- `invoices.json` - Invoice template configuration

### `invoices/` - Invoice Metadata

**Never deleted**. Contains:
- `{apartment}/DL_0001.json` - Invoice metadata
- `{apartment}/DL_0002.json` - Next invoice metadata
- etc.

These track invoice numbers and contain links to generated Google Sheets.

### `credentials/` - Google Service Account

**Never deleted**. Contains:
- `service_account.json` - Google API credentials

## Cleanup Behavior

### Automatic Cleanup

The upload command **always** cleans up `data/temp/` after running:

```python
finally:
    # Always clean up temp files, even if there was an error
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        info("🧹 Cleaned up temporary files")
```

This happens:
- ✅ After successful upload
- ✅ After failed upload
- ✅ After keyboard interrupt (Ctrl+C)
- ✅ After any error

### Manual Cleanup

If needed:

```bash
# Remove temp folder
rm -rf data/temp/

# Recreated automatically on next upload
```

## Storage Recommendations

### Keep Original CSVs Outside Project

Store downloaded CSVs separately:

```
~/Downloads/
├── airbnb_export_jan_2026.csv
├── booking_export_jan_2026.csv
└── airbnb_export_feb_2026.csv
```

Reference them:

```bash
reservations upload ~/Downloads/airbnb_export_jan_2026.csv -a downtown-loft
```

### Archive Old CSVs (Optional)

For record-keeping:

```
~/Documents/reservations-archive/
├── 2026/
│   ├── 01-january/
│   │   ├── airbnb_export.csv
│   │   └── booking_export.csv
│   ├── 02-february/
│   │   ├── airbnb_export.csv
│   │   └── booking_export.csv
```

## Disk Space

With automatic cleanup:
- **Before**: ~50-200 KB per upload (processed + merged files)
- **After**: 0 KB (all temp files deleted)
- **Savings**: 100% of temporary file space

## Benefits

1. **No Clutter**: Project stays clean
2. **No Confusion**: No outdated processed files
3. **Disk Space**: Automatic cleanup saves space
4. **Reliable**: Works even if upload fails
5. **Simple**: No manual cleanup needed

## Troubleshooting

### Temp Folder Not Deleted

If cleanup fails (rare):

```
⚠️  Warning: Could not clean temp folder: [error]
```

Manually delete:

```bash
rm -rf data/temp/
```

### Need to Debug Processed Files

To inspect processed files before deletion:

```bash
# Process files manually
python scripts/process_airbnb.py input.csv output.csv

# Files won't be auto-deleted
```

### Checking Disk Usage

```bash
# Check project size
du -sh ~/dev/reservation-tracking-sheets

# Check if temp exists
ls -la data/temp/ 2>/dev/null || echo "No temp folder (clean!)"
```

## Git Ignore

All data directories are gitignored:

```gitignore
# .gitignore
data/
credentials/
invoices/
```

This ensures:
- No sensitive data in repository
- No large CSV files committed
- Clean repository history
