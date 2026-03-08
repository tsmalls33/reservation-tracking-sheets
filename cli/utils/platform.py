"""Platform detection utilities."""

import re
from pathlib import Path


def detect_platform(filename: str) -> str:
    """Automatically detect if a CSV is from Airbnb or Booking.com.
    
    Args:
        filename: Path to CSV file
        
    Returns:
        'airbnb' or 'booking'
        
    Raises:
        ValueError: If platform cannot be detected
    """
    fn_lower = Path(filename).name.lower()
    
    # Check filename patterns
    if any(x in fn_lower for x in ['airbnb', 'confirmación']):
        return 'airbnb'
    
    # Booking.com patterns:
    # - booking, reservation, invoice keywords
    # - Check-in YYYY-MM-DD to YYYY-MM-DD.xls pattern
    if any(x in fn_lower for x in ['booking', 'invoice']):
        return 'booking'
    
    # Match: Check-in 2025-10-01 to 2025-12-31.xls
    if re.match(r'check-in\s+\d{4}-\d{2}-\d{2}\s+to\s+\d{4}-\d{2}-\d{2}\.(xls|xlsx|csv)', fn_lower):
        return 'booking'
    
    # Quick content check if filename doesn't match
    try:
        content = Path(filename).read_text(errors='ignore')[:1000].lower()
        if any(x in content for x in ['airbnb', 'código de confirmación', 'confirmación', 'confirmation code']):
            return 'airbnb'
        if any(x in content for x in ['booking', 'reservation number', 'invoice number']):
            return 'booking'
    except OSError:
        pass
    
    raise ValueError(
        f"Cannot detect platform for: {filename}\n"
        f"Expected 'airbnb' or 'booking' in filename or content.\n"
        f"Booking files typically named: 'Check-in YYYY-MM-DD to YYYY-MM-DD.xls'"
    )
