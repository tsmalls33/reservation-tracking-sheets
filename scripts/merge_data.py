
#!/usr/bin/env python3
"""
Merge processed Airbnb + Booking CSVs into single file.
Usage: python merge_data.py input1.csv input2.csv output.csv
"""

import pandas as pd
import sys
from pathlib import Path

if len(sys.argv) < 4:
    print("Usage: python merge_data.py input1.csv input2.csv output.csv")
    sys.exit(1)

input_files = sys.argv[1:-1]
output_file = Path(sys.argv[-1])

# Read all CSVs
dfs = []
for file in input_files:
    df = pd.read_csv(file)
    print(f"Loaded {len(df)} rows from {file}")
    dfs.append(df)

# Merge + dedupe + sort
merged = pd.concat(dfs, ignore_index=True)

# Dedupe by common keys
key_cols = ['reservation_id', 'confirmation_code', 'invoice_number', 'Cdigo de confirmacin']
existing_keys = [col for col in key_cols if col in merged.columns]
if existing_keys:
    initial_rows = len(merged)
    merged = merged.drop_duplicates(subset=existing_keys)
    print(f"Deduplicated: {initial_rows} → {len(merged)} rows")

# Sort by date
date_cols = ['date', 'arrival', 'checkin_date', 'Fecha de inicio', 'Arrival']
for col in date_cols:
    if col in merged.columns:
        merged[col] = pd.to_datetime(merged[col], errors='coerce')
        merged = merged.sort_values(col).reset_index(drop=True)
        break

# Save
output_file.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(output_file, index=False)
print(f"✅ Saved {len(merged)} rows to {output_file}")
