import pandas as pd
from pathlib import Path
import sys

def process_booking_csv(input_file, output_file=None, cleaning_fee=25.0):
    """
    Process Booking.com CSV export and prepare for Google Sheets upload.
    
    Args:
        input_file: Path to raw Booking.com CSV
        output_file: Path for processed output (default: data/processed/booking_processed.csv)
        cleaning_fee: Default cleaning fee in euros (default: 25.0)
    
    Returns:
        DataFrame with processed data
    """
    # Read CSV
    df = pd.read_csv(input_file)
    
    # Filter out cancelled reservations
    df = df[df['Status'] != 'CANCELLED'].copy()
    
    # Format guest name with person count: "Name (X)"
    df['Actividad'] = df.apply(
        lambda row: f"{row['Guest name']} ({int(row['Persons'])})", 
        axis=1
    )
    
    # Dates are already in YYYY-MM-DD format, just copy them
    df['Entrada'] = df['Arrival']
    df['Salida'] = df['Departure']
    
    # Get number of nights (already provided)
    df['Noches'] = df['Room nights'].astype(int)
    
    # Final amount is the price (already a float)
    df['Precio'] = df['Final amount'].astype(float)
    
    # Set Check In/Out (cleaning fee)
    df['Check In/Out'] = cleaning_fee
    
    # Commission amount from Booking.com
    df['Comision'] = df['Commission amount'].astype(float)
    
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
        print(f"✓ Processed {len(processed_df)} reservations (filtered out {len(df[df['Status'] == 'CANCELLED'])} cancelled)")
        print(f"✓ Saved to: {output_path}")
    
    return processed_df


if __name__ == "__main__":
    # Example usage
    input_file = sys.argv[1] if len(sys.argv) > 1 else input("Enter path to Booking.com CSV export: ")
    output_file = "data/processed/booking_processed.csv"
    
    df = process_booking_csv(input_file, output_file)
    print("\nSample output:")
    print(df.head())
