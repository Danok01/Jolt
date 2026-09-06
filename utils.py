import hashlib
#import random
import secrets
import string
import streamlit as st
import re


# 1. STREAMLIT SESSION STATE INITIALIZER
def init_session_state() -> None:
    """Initializes global authentication and user state in Streamlit."""
    defaults = {
        "authenticated": False,
        "user": None,  # Holds user dict / document
        "role": None,  # "ADMIN" or "TEACHER"
        "school_id": None,
        "school_name": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validates password against security rules.

    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    return True, ""

# 2. TEMPORARY PASSWORD GENERATOR
def generate_temp_password(length: int = 10) -> str:
    """Generates a random, secure temporary password for provisioned teachers."""
    characters = string.ascii_letters + string.digits + "@#$%"
    return "".join(secrets.choice(characters) for _ in range(length))


# 3. PASSWORD HASHING & VERIFICATION (Standard Library)
def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2 with SHA-256 and a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"{salt}:{key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored salt:hash string."""
    try:
        salt, key_hex = hashed_password.split(":")
        new_key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return secrets.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False


# 4. ORDINAL RANK FORMATTER
def get_ordinal(rank: int) -> str:
    """Converts integers to ordinal rank strings (1 -> '1st', 2 -> '2nd', 3 -> '3rd')."""
    if not isinstance(rank, int) or rank <= 0:
        return str(rank)

    if 11 <= (rank % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")

    return f"{rank}{suffix}"

def calculate_grade(total_score: float) -> str:
    """Maps a total percentage score (0-100) to a letter grade."""
    if total_score >= 70.0:
        return "A"
    elif total_score >= 60.0:
        return "B"
    elif total_score >= 50.0:
        return "C"
    elif total_score >= 45.0:
        return "D"
    else:
        return "F"



# ==============================================================================
# MONGODB ATLAS (CLOUD) UTILITY NOTE
# ==============================================================================
# When running on cloud platforms (e.g., Streamlit Community Cloud) connected to
# MongoDB Atlas, manage secrets securely using Streamlit Secrets (`.streamlit/secrets.toml`):
#
# MONGO_URI = st.secrets["MONGO_URI"]
#
# Never hardcode production database URIs or password salts inside helper functions.