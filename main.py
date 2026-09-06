import streamlit as st
from utils import init_session_state
from views import render_admin_dashboard, render_auth_view, render_teacher_dashboard

# Configure Streamlit Page
st.set_page_config(
    page_title="JRMS",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize Session State
init_session_state()


def main():
    # Check authentication status
    if not st.session_state.get("authenticated", False):
        render_auth_view()
        return

    # Sidebar Navigation & User Metadata
    user = st.session_state.get("user", {})
    role = st.session_state.get("role")
    school_name = st.session_state.get("school_name", "School")

    with st.sidebar:
        st.title("🏫 Navigation")
        st.write(f"**School:** {school_name.title()}")
        st.write(f"**Logged in as:** {user.get('full_name', 'User').title()}")
        st.write(f"**Role:** `{role}`")
        st.markdown("---")

        if st.button("🚪 Log Out", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # View Routing Based on Role
    if role == "ADMIN":
        render_admin_dashboard()
    elif role == "TEACHER":
        render_teacher_dashboard()
    else:
        st.error("Unrecognized user role. Please contact system support.")


if __name__ == "__main__":
    main()

# ==============================================================================
# MONGODB ATLAS (CLOUD) / DEPLOYMENT CHECKLIST
# ==============================================================================
# To run this project locally or deploy to Streamlit Community Cloud:
#
# 1. Create a `requirements.txt` file in your root folder:
#    streamlit
#    pymongo
#    dnspython
#    pydantic
#    python-dotenv
#    reportlab
#
# 2. For local testing with MongoDB Compass, create a `.env` file:
#    MONGO_URI=mongodb://localhost:27017/
#    DB_NAME=school_result_db
#
# 3. For production on Streamlit Community Cloud using MongoDB Atlas:
#    Add your Atlas connection string to `.streamlit/secrets.toml`:
#    MONGO_URI = "mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority"
#    DB_NAME = "school_result_db"