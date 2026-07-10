import streamlit as st
import db
import utils

# --- PAGE SETUP ---
st.set_page_config(page_title="School Result Portal", page_icon="🎓", layout="centered")

# --- INITIALIZE SESSION STATE ---
# This ensures data persists across widget interactions and navigation shifts
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# --- AUTHENTICATED STATE INTERFACE ---
if st.session_state.authenticated:
    user = st.session_state.user_data
    
    # Sidebar logout controls
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Logged in as: **{user['name']}**")
    st.sidebar.write(f"Role: `{user['role']}`")
    
    if st.sidebar.button("Log Out"):
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.rerun()

    # Dynamic Dashboard Content based on persistent state roles
    st.title(f"🎓 {user['school_name']}")
    st.subheader(f"Welcome back, {user['name']}!")
    st.markdown("---")
    
    if user["role"] == "Admin":
        st.info("🏫 **Admin Control Panel Active**")
        st.write(f"📍 **Registered Location Address:** {user['address']}")
        
        logo_img = utils.convert_base64_to_image(user["logo_b64"])
        if logo_img:
            st.image(logo_img, caption="Verified School Identity System", width=140)
    else:
        st.info("📖 **Teacher Portal Active**")
        st.write("You have permission to access classes, edit test forms, and manage grades.")

    st.write("🚀 *Next architectural step: Render tables and forms for logging student exam metrics.*")

# --- UNAUTHENTICATED STATE INTERFACE ---
else:
    st.title("🎓 Student Test & Exam Portal")
    auth_mode = st.sidebar.radio("Authentication Action", ["Login", "Sign-Up"])

    if auth_mode == "Sign-Up":
        st.header("📝 Create an Account")
        role = st.selectbox("Register as:", ["Teacher", "Admin"])
        
        name = st.text_input("Full Name")
        school_name = st.text_input("School Name")
        email = st.text_input("Email Address").strip().lower()
        password = st.text_input("Create Password", type="password")
        
        school_address = ""
        logo_b64 = ""
        
        if role == "Admin":
            st.subheader("🏫 Admin Requirements")
            school_address = st.text_area("School Physical Address")
            school_logo_file = st.file_uploader("Upload School Logo", type=["png", "jpg", "jpeg"])
            if school_logo_file:
                logo_b64 = utils.convert_image_to_base64(school_logo_file)

        if st.button("Register Account"):
            if not name or not school_name or not email or not password:
                st.error("Please fill out all standard fields.")
            elif role == "Admin" and not school_address:
                st.error("Admins must provide their school address details.")
            elif db.find_user_by_email(email) is not None:
                st.error("This email identity is already registered inside our system.")
            else:
                user_document = {
                    "name": name,
                    "school_name": school_name,
                    "email": email,
                    "role": role,
                    "password": password, 
                    "address": school_address,
                    "logo_b64": logo_b64
                }
                db.register_user(user_document)
                st.success("🎉 Account deployed to cloud ecosystem! Please switch navigation to Login.")

    elif auth_mode == "Login":
        st.header("🔑 Secure Portal Login")
        login_email = st.text_input("Email Address").strip().lower()
        login_password = st.text_input("Password", type="password")
        
        if st.button("Log In"):
            user = db.find_user_by_email(login_email)
            
            if user and user["password"] == login_password:
                # Store user parameters securely inside session variables
                st.session_state.authenticated = True
                
                # Sanitize out the internal MongoDB ObjectId reference for streamlit state mapping safety
                user["_id"] = str(user["_id"]) 
                st.session_state.user_data = user
                
                # Instantly force the layout pipeline to redraw into the authenticated state view
                st.rerun()
            else:
                st.error("Verification sequence failed. Incorrect identity or credentials.")