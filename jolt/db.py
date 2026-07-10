import streamlit as st
import pymongo

@st.cache_resource
def init_connection():
    """Establishes and caches the MongoDB connection."""
    try:
        return pymongo.MongoClient(st.secrets["mongo"]["uri"])
    except Exception as e:
        st.error(f"Database connection configuration error: {e}")
        st.stop()

def get_users_collection():
    """Returns the target users collection."""
    client = init_connection()
    db = client["school_portal_db"]
    return db["users"]

def find_user_by_email(email):
    """Queries a user document by email address."""
    coll = get_users_collection()
    return coll.find_one({"email": email.strip().lower()})

def register_user(user_document):
    """Inserts a new user record into the database."""
    coll = get_users_collection()
    return coll.insert_one(user_document)