import hashlib
import hmac
import re

from config import AppConfig

_pattern_username = r"^[a-zA-Z0-9_]{8,32}$"
_pattern_password = r"^[\x20-\x7E]{6,128}$"
_pattern_email = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


def is_valid_username(username: str):
    """
    Check if a username is valid.

    Parameters:
    username (str): The input username to validate.

    Returns:
    bool: True if the username is valid, False otherwise.

    Valid username requirements:
    - Must consist of alphanumeric characters (a-z, A-Z, 0-9) and underscores (_).
    - Must be between 8 and 32 characters in length.

    Example:
    is_valid_username("user_123")   # True
    is_valid_username("user@name")  # False
    """
    return re.match(_pattern_username, username) is not None


def is_valid_password(password: str):
    """
    Check if a password is valid.

    Parameters:
    password (str): The input password to validate.

    Returns:
    bool: True if the password is valid, False otherwise.

    Valid password requirements:
    - Must consist of printable ASCII characters (ASCII range 0x20 to 0x7E).
    - Must be between 6 and 128 characters in length.

    Example:
    is_valid_password("Pa$$w0rd")  # True
    is_valid_password("12345")     # False
    """
    return re.match(_pattern_password, password) is not None


def is_valid_email(email: str):
    """
    Check if an email address is valid.

    Parameters:
    email (str): The input email address to validate.

    Returns:
    bool: True if the email address is valid, False otherwise.

    Valid email address requirements:
    - Must follow a standard email format, e.g., "user@example.com".
    - User part may consist of alphanumeric characters, dots (.), underscores (_),
      percent signs (%), and plus signs (+).
    - Domain part must consist of alphanumeric characters, dots (.), and hyphens (-).
    - Must have a valid top-level domain (TLD) with at least 2 characters.

    Example:
    is_valid_email("user@example.com")  # True
    is_valid_email("invalid-email")     # False
    """
    return re.match(_pattern_email, email) is not None


def encode_password(password: str):
    return hmac.new(AppConfig.HmacSalt, password.encode(), hashlib.sha256).hexdigest()


def verify_password(password: str, encoded: str):
    new_encoded = encode_password(password)
    return new_encoded == encoded
