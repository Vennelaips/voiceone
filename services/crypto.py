import hashlib
import hmac
import re
from datetime import datetime, date
from config import Config

def sanitize_aadhaar(aadhaar_raw: str) -> str:
    """Removes spaces, dashes, and non-numeric characters from Aadhaar input."""
    if not aadhaar_raw:
        return ""
    return re.sub(r"\D", "", str(aadhaar_raw).strip())

def is_valid_aadhaar_format(aadhaar_clean: str) -> bool:
    """Verifies that the cleaned Aadhaar is exactly 12 digits."""
    return bool(re.fullmatch(r"^\d{12}$", aadhaar_clean))

def hash_aadhaar(aadhaar_number: str) -> str:
    """
    Cryptographically hashes the citizen's Aadhaar number using HMAC-SHA256 with a secure server salt.
    Guarantees that raw 12-digit Aadhaar numbers are never stored in database or logs,
    while producing a deterministic voter pseudonym to enforce one-citizen-one-vote.
    """
    clean_aadhaar = sanitize_aadhaar(aadhaar_number)
    if not is_valid_aadhaar_format(clean_aadhaar):
        raise ValueError("Invalid Aadhaar number format. Must be a 12-digit numeric identifier.")
    
    salt = Config.AADHAAR_HASH_SALT.encode("utf-8")
    message = clean_aadhaar.encode("utf-8")
    
    voter_hash = hmac.new(salt, message, hashlib.sha256).hexdigest()
    return f"citizen_v_{voter_hash[:20]}"

def calculate_age(dob_str: str) -> int:
    """
    Calculates the citizen's age in full years from a date string (YYYY-MM-DD or DD/MM/YYYY).
    """
    if not dob_str:
        return 0
        
    dob_date = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dob_date = datetime.strptime(dob_str.strip(), fmt).date()
            break
        except ValueError:
            continue
            
    if not dob_date:
        raise ValueError("Invalid Date of Birth format. Please use YYYY-MM-DD.")
        
    today = date.today()
    age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
    return age

def is_eligible_citizen(dob_str: str) -> tuple[bool, int, str]:
    """
    Checks if a citizen is 18 years of age or older.
    Returns (is_eligible, calculated_age, message).
    """
    try:
        age = calculate_age(dob_str)
        if age < 18:
            return False, age, f"Access restricted: Citizen is {age} years old. Minimum required age is 18."
        return True, age, f"Eligible voter (Age: {age})."
    except Exception as e:
        return False, 0, str(e)
