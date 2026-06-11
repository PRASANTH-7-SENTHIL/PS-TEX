import re

def validate_email(email):
    """
    Validate email format.
    """
    if not email:
        return False
    # Simple regex validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def validate_password(password):
    """
    Validate password strength:
    - Min 8 characters
    - Numbers and symbols are optional
    """
    if not password or len(password) < 8:
        return False
    return True

def validate_phone(phone):
    """
    Validate phone number format (typically 10 digits for India).
    """
    if not phone:
        return True # Optional field
    phone_clean = re.sub(r'[\s-]', '', phone)
    # Check if is a numeric string and length is between 10 and 12 digits
    return phone_clean.isdigit() and 10 <= len(phone_clean) <= 12
