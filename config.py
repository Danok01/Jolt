import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from local .env file
load_dotenv()

def get_secret(key: str, default=None):
    """Fetch secret from os.environ first, then Streamlit secrets."""
    # 1. Check OS Environment Variables (.env, Render, Railway, Heroku, Docker)
    if os.getenv(key):
        return os.getenv(key)

    # 2. Fallback to Streamlit Secrets (Streamlit Cloud / .streamlit/secrets.toml)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    return default


# App & Database Configuration
MONGO_URI = get_secret("MONGO_URI")
DB_NAME = get_secret("DB_NAME", "school_result_db")

if not MONGO_URI:
    raise ValueError(
        "MONGO_URI environment variable is missing. "
        "Please define it in your .env file or Streamlit Secrets."
    )

# App & Database Configuration
#MONGO_URI = os.getenv("MONGO_URI")
#DB_NAME = os.getenv("DB_NAME", "school_result_db")

#if not MONGO_URI:
#    raise ValueError(
#        "MONGO_URI environment variable is missing. "
#        "Please create a .env file and define MONGO_URI."
#   )

# ==============================================================================
# MONGODB ATLAS (CLOUD) CONNECTION REFERENCE
# ==============================================================================
# For local testing (Compass), place this in your .env file:
# MONGO_URI=mongodb://localhost:27017/
#
# To switch to MongoDB Atlas in production, update MONGO_URI in your .env file:
# MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority
#
# Note: Ensure `dnspython` is installed (`pip install dnspython`) when using
# `mongodb+srv://` URIs, and verify your IP is whitelisted in Atlas Network Access.