import pandas as pd
from pathlib import Path
import sys
import re
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

def process_booking_csv(input_file, output_file=None, cleaning_fee=25.0):
    """
    Process Booking.com CSV or XLS export and prepare for Google Sheets upload.
    Handles multiple Booking.com export formats automatically.
    
    Args:
        input_file: Path to raw Booking.com CSV or XLS file
        output_file: Path for processed output (default: data/processed/booking_processed.csv)
        cleaning_fee: Default cleaning fee in euros (default: 25.0)
    
    Returns:
        DataFrame with processed data
    """
    # Detect file format and read accordingly
    input_path = Path(input_file)
    file_extension = input_path.suffix.lower()
    
    try:
        if file_extension == '.csv':
            df = pd.read_csv(input_file)
            print(f"✓ Reading CSV file: {input_path.name}")
        elif file_extension in ['.xls', '.xlsx']:
            df = pd.read_excel(input_file, engine='xlrd' if file_extension == '.xls' else 'openpyxl')
            print(f"✓ Reading Excel file: {input_path.name}")
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Please use .csv, .xls, or .xlsx")
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        raise
    
    # Column mapping - try different possible column names (in order of preference)
    column_mappings = {
        'guest_name': ['Guest Name(s)', 'Guest name', 'Guest', 'Name', 'Booked by'],
        'persons': ['People', 'Persons', 'Guests', 'Number of guests'],
        'status': ['Status', 'Reservation status', 'Booking status'],
        'arrival': ['Check-in', 'Arrival', 'Check in', 'Checkin', 'Arrival date'],
        'departure': ['Check-out', 'Departure', 'Check out', 'Checkout', 'Departure date'],
        'room_nights': ['Duration (nights)', 'Room nights', 'Nights', 'Number of nights'],
        'final_amount': ['Price', 'Final amount', 'Total', 'Total amount', 'Amount'],
        'commission': ['Commission Amount', 'Commission amount', 'Commission', 'Booking.com commission']
    }
    
    def find_column(possible_names):
        """Find the first matching column name from a list of possibilities"""
        for name in possible_names:
            if name in df.columns:
                return name
        raise KeyError(f"Could not find column. Tried: {possible_names}. Available columns: {list(df.columns)}")
    
    def clean_currency(value):
        """Remove currency symbols and convert to float"""
        if pd.isna(value):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        # Remove currency symbols, letters, and whitespace, keep numbers and decimal point
        cleaned = re.sub(r'[^0-9.-]', '', str(value))
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    
    # Map columns dynamically
    try:
        guest_col = find_column(column_mappings['guest_name'])
        persons_col = find_column(column_mappings['persons'])
        status_col = find_column(column_mappings['status'])
        arrival_col = find_column(column_mappings['arrival'])
        departure_col = find_column(column_mappings['departure'])
        nights_col = find_column(column_mappings['room_nights'])
        amount_col = find_column(column_mappings['final_amount'])
        commission_col = find_column(column_mappings['commission'])
    except KeyError as e:
        print(f"✗ {e}")
        raise
    
    # Filter out cancelled reservations - check if "cancelled" appears anywhere in status (case-insensitive)
    df[status_col] = df[status_col].fillna('').astype(str)
    cancelled_mask = df[status_col].str.lower().str.contains('cancel', na=False)
    cancelled_count = cancelled_mask.sum()
    df = df[~cancelled_mask].copy()
    
    # Format guest name with person count: "Name (X)"
    df['Actividad'] = df.apply(
        lambda row: f"{row[guest_col]} ({int(row[persons_col])})", 
        axis=1
    )
    
    # Convert dates to YYYY-MM-DD format
    df['Entrada'] = pd.to_datetime(df[arrival_col]).dt.strftime('%Y-%m-%d')
    df['Salida'] = pd.to_datetime(df[departure_col]).dt.strftime('%Y-%m-%d')
    
    # Get number of nights
    df['Noches'] = df[nights_col].fillna(0).astype(int)
    
    # Clean and convert price (remove currency symbols)
    df['Precio'] = df[amount_col].apply(clean_currency)
    
    # Set Check In/Out (cleaning fee)
    df['Check In/Out'] = cleaning_fee
    
    # Clean and convert commission amount (remove currency symbols)
    df['Comision'] = df[commission_col].apply(clean_currency)
    
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
        print(f"✓ Processed {len(processed_df)} reservations (filtered out {cancelled_count} cancelled)")
        print(f"✓ Saved to: {output_path}")
    
    return processed_df


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("Enter path to Booking.com CSV/XLS export: ")
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    df = process_booking_csv(input_file, output_file)
    print("\nSample output:")
    print(df.head())

