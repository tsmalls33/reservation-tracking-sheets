import argparse
import pandas as pd
from pathlib import Path
import re
import sys

def process_airbnb_csv(input_file, output_file=None, cleaning_fee=25.0):
    """
    Process Airbnb CSV export and prepare for Google Sheets upload.
    
    Args:
        input_file: Path to raw Airbnb CSV
        output_file: Path for processed output (default: data/processed/airbnb_processed.csv)
        cleaning_fee: Default cleaning fee in euros (default: 25.0)
    
    Returns:
        DataFrame with processed data
    """
    # Read CSV
    df = pd.read_csv(input_file)
    
    # Calculate total guests (adults + children + babies)
    df['total_guests'] = (
        df['N.º de adultos'].fillna(0) + 
        df['N.º de niños'].fillna(0) + 
        df['N.º de bebés'].fillna(0)
    ).astype(int)
    
    # Format guest name with count: "Name (X)"
    df['Actividad'] = df.apply(
        lambda row: f"{row['Nombre de la persona']} ({row['total_guests']})", 
        axis=1
    )
    
    # Convert dates from DD/MM/YYYY to YYYY-MM-DD (ISO format)
    df['Entrada'] = pd.to_datetime(df['Fecha de inicio'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
    df['Salida'] = pd.to_datetime(df['Fecha de finalización'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
    
    # Get number of nights from CSV
    df['Noches'] = df['N.º de noches'].astype(int)
    
    # Clean price: remove € symbol, replace comma with dot, convert to float
    df['Precio'] = df['Ingresos'].str.replace('€', '').str.replace(',', '.').str.strip().astype(float)
    
    # Set Check In/Out (cleaning fee)
    df['Check In/Out'] = cleaning_fee
    
    # Airbnb commission is 0 (already deducted from price)
    df['Comision'] = 0.0
    
    # Leave VAT empty (let Google Sheets calculate)
    df['VAT'] = ''
    
    # Select and order columns for output
    output_columns = ['Actividad', 'Entrada', 'Salida', 'Noches', 'Precio', 'Check In/Out', 'Comision', 'VAT']
    processed_df = df[output_columns]
    
    # Sort by check-in date
    processed_df = processed_df.sort_values('Entrada')
    
    # Save to file if output path specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        processed_df.to_csv(output_path, index=False)
        print(f"✓ Processed {len(processed_df)} reservations")
        print(f"✓ Saved to: {output_path}")
    
    return processed_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Airbnb CSV export")
    parser.add_argument('input_file', help="Path to raw Airbnb CSV")
    parser.add_argument('output_file', nargs='?', default=None, help="Path for processed output")
    parser.add_argument('--cleaning-fee', type=float, default=25.0,
                        help="Cleaning fee per reservation (default: 25.0)")

    args = parser.parse_args()

    df = process_airbnb_csv(args.input_file, args.output_file, cleaning_fee=args.cleaning_fee)
    print("\nSample output:")
    print(df.head())
