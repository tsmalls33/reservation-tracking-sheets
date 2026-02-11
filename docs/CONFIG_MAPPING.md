# Dynamic Column Mapping Documentation

This document explains how the dynamic column mapping system works and how to configure different sheet layouts.

## Overview

The upload system now supports flexible column layouts defined in JSON config files. Each apartment/sheet can have different columns while using the same CSV processing pipeline.

## How It Works

### 1. CSV Processing
Both `process_airbnb.py` and `process_booking.py` output standardized CSV files with these columns:
```
Actividad, Entrada, Salida, Noches, Precio, Check In/Out, Comision, VAT
```

### 2. Config Mapping
Each config file maps CSV columns to sheet columns using `column_mapping`:

```json
"column_mapping": {
  "Sheet Column Name": {
    "csv_field": "CSV_Column_Name",
    "sheet_col_offset": 0,
    "skip_next": true  // optional, for merged cells
  }
}
```

### 3. Upload Flexibility
The upload script reads `column_mapping` and `physical_columns` to:
- Clear the correct number of columns
- Place CSV data at the right sheet positions
- Handle merged cells automatically

## Configuration Examples

### Mediona Layout (8 physical columns)

**Visible Columns:** Actividad | (merged) | Entrada | Salida | Noches | Precio | Check In/Out | Comision

**Physical Sheet Layout:**
```
F: Actividad (merged with G)
G: (empty, part of F merge)
H: Entrada
I: Salida
J: Noches
K: Precio
L: Check In/Out
M: Comision
```

**Config:**
```json
{
  "columns": ["Actividad", "Entrada", "Salida", "Noches", "Precio", "Check In/Out", "Comision"],
  "column_mapping": {
    "Actividad": {"csv_field": "Actividad", "sheet_col_offset": 0, "skip_next": true},
    "Entrada": {"csv_field": "Entrada", "sheet_col_offset": 2},
    "Salida": {"csv_field": "Salida", "sheet_col_offset": 3},
    "Noches": {"csv_field": "Noches", "sheet_col_offset": 4},
    "Precio": {"csv_field": "Precio", "sheet_col_offset": 5},
    "Check In/Out": {"csv_field": "Check In/Out", "sheet_col_offset": 6},
    "Comision": {"csv_field": "Comision", "sheet_col_offset": 7}
  },
  "physical_columns": 8
}
```

### Sant Domènec Layout (5 physical columns)

**Visible Columns:** Nombre Reserva | (merged) | Entrada | Salida | Precio Total

**Physical Sheet Layout:**
```
F: Nombre Reserva (merged with G)
G: (empty, part of F merge)
H: Entrada
I: Salida
J: Precio Total
```

**Config:**
```json
{
  "columns": ["Nombre Reserva", "Entrada", "Salida", "Precio Total"],
  "column_mapping": {
    "Nombre Reserva": {"csv_field": "Actividad", "sheet_col_offset": 0, "skip_next": true},
    "Entrada": {"csv_field": "Entrada", "sheet_col_offset": 2},
    "Salida": {"csv_field": "Salida", "sheet_col_offset": 3},
    "Precio Total": {"csv_field": "Precio", "sheet_col_offset": 4}
  },
  "physical_columns": 5
}
```

## Key Concepts

### `sheet_col_offset`
The column position relative to `start_range`. If `start_range` is "F11":
- offset 0 = column F
- offset 1 = column G
- offset 2 = column H
- etc.

### `skip_next: true`
Used when a column is merged with the next one. This accounts for the physical space occupied by merged cells.

### `physical_columns`
Total number of physical columns to clear, including merged cells. This ensures proper clearing without affecting adjacent data.

## CSV to Sheet Mapping

| CSV Field | Mediona Sheet | Sant Domènec Sheet |
|-----------|---------------|--------------------|
| Actividad | Actividad | Nombre Reserva |
| Entrada | Entrada | Entrada |
| Salida | Salida | Salida |
| Noches | Noches | *(not displayed)* |
| Precio | Precio | Precio Total |
| Check In/Out | Check In/Out | *(not displayed)* |
| Comision | Comision | *(not displayed)* |
| VAT | *(removed)* | *(not displayed)* |

## Usage Examples

### Upload to Mediona (8 columns)
```bash
python main.py oneshot file1.csv file2.csv -a mediona -y 2026
```

### Upload to Sant Domènec (4 columns)
```bash
python main.py oneshot file1.csv file2.csv -a sant-domenec -y 2026
```

Both use the same CSV processing but map to different sheet layouts automatically!

## Adding New Configurations

1. Identify your sheet layout (starting cell, columns, merged cells)
2. Create config file: `config/{apartment}_{year}.json`
3. Define `column_mapping` with correct offsets
4. Set `physical_columns` (count includes merged cells)
5. Run: `python main.py oneshot ... -a {apartment} -y {year}`

## Notes

- All configs start at F11 by default
- F and G are always merged in current layouts
- Clearing affects only data cells, preserves formatting
- Month name is always written to cell B2
