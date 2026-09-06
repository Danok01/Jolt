import streamlit as st
from db import (
    create_admin_user,
    create_school,
    create_student,
    create_teacher_user,
    get_class_results,
    get_school_by_id,
    get_students_by_class,
    get_teachers_by_school,
    get_user_by_email,
    save_or_update_student_subject_score,
    update_user_password,
    delete_teacher_by_email,
    get_student_count_for_classes
)
from services import (
    compute_and_update_class_ranks,
    generate_student_pdf,
    process_subject_scores,
)
from utils import generate_temp_password, get_ordinal, verify_password, validate_password_strength


# 1. AUTHENTICATION VIEW (LOGIN & REGISTER & TEMP PASSWORD RESET)
def render_auth_view() -> None:
    """Renders login, school setup, and mandatory temporary password reset views."""
    st.title("Jolt Result Management System")

    # Handle Temporary Password Change Enforcement
    if st.session_state.get("must_change_password"):
        st.warning(
            "🔑 You are using a temporary password. Please set a new permanent password."
        )

        with st.form("password_reset_form"):
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input(
                "Confirm New Password", type="password"
            )
            submit = st.form_submit_button("Update Password")

            if submit:
                if not new_password or new_password != confirm_password:
                    st.error("Passwords do not match or field is empty.")
                else:
                    user_id = st.session_state["user"]["_id"]
                    if submit:
                        is_valid, error_message = validate_password_strength(new_password)

                    if not is_valid:
                        st.error(f"❌ {error_message}")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match.")
                    else:
                        # Hash password and update in MongoDB
                        update_user_password(user_id, new_password)
                        st.success(
                            "✅ Password updated successfully! Please log in again."
                        )
                        st.rerun()

    # Standard Login & School Setup Tabs
    tab_login, tab_register = st.tabs(
        ["🔐 Login", "🏛️ Register School & Admin"]
    )

    with tab_login:
        st.subheader("Account Login")
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Log In")

            if login_submit:
                user = get_user_by_email(email)
                if user and verify_password(password, user["password_hash"]):
                    school = get_school_by_id(user["school_id"])
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user
                    st.session_state["role"] = user["role"]
                    st.session_state["school_id"] = user["school_id"]
                    st.session_state["school_name"] = (
                        school["name"] if school else "School"
                    )

                    if user.get("is_temporary_password", False):
                        st.session_state["must_change_password"] = True

                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with tab_register:
        st.subheader("Setup New School & Admin Account")
        with st.form("register_school_form"):
            school_name = st.text_input("School Name").lower()
            admin_name = st.text_input("Admin Full Name").lower()
            admin_email = st.text_input("Admin Email Address").lower()
            admin_password = st.text_input(
                "Admin Password", type="password"
            )
            reg_submit = st.form_submit_button("Create School Account")

            if reg_submit:
                is_valid, error_message = validate_password_strength(admin_password)

                if not is_valid:
                    st.error(f"❌ {error_message}")
                elif not all(
                    [school_name, admin_name, admin_email, admin_password]
                ):
                    st.error("All fields are required.")
                elif get_user_by_email(admin_email):
                    st.error("A user with this email already exists.")
                else:
                    school_id = create_school(school_name)
                    create_admin_user(
                        school_id, admin_name, admin_email, admin_password
                    )
                    st.success(
                        "School and Admin created! Please log in above."
                    )


# 2. ADMIN DASHBOARD VIEW
def render_admin_dashboard() -> None:
    """Renders Admin controls for provisioning teachers and registering students."""
    st.title(f"🛠️ Admin Dashboard - {st.session_state['school_name'].title()}")

    tab_teachers, tab_students, tab_list = st.tabs(
        ["👨‍🏫 Provision Teacher", "🎓 Register Student", "📋 View Records"]
    )

    school_id = st.session_state["school_id"]

    # Tab 1: Provision Teachers with Temporary Passwords
    with tab_teachers:
        st.subheader("Add New Teacher")
        with st.form("add_teacher_form"):
            teacher_name = st.text_input("Teacher Full Name").lower()
            teacher_email = st.text_input("Teacher Email").lower()
            assigned_classes_raw = st.text_input(
                "Assigned Classes (comma-separated, e.g. Grade 9A, Grade 9B)"
            ).lower()
            submit_teacher = st.form_submit_button("Create Teacher Account")

            if submit_teacher:
                if not teacher_name or not teacher_email:
                    st.error("Name and Email are required.")
                elif get_user_by_email(teacher_email):
                    st.error("A user with this email already exists.")
                else:
                    classes = [
                        c.strip()
                        for c in assigned_classes_raw.split(",")
                        if c.strip()
                    ]
                    temp_pwd = generate_temp_password()
                    create_teacher_user(
                        school_id,
                        teacher_name,
                        teacher_email,
                        temp_pwd,
                        classes,
                    )
                    st.success("Teacher account created successfully!")
                    st.info(
                        f"🔑 **Temporary Password for {teacher_name}:** `{temp_pwd}`\n\n"
                        f"*Copy this password now and share it directly with the teacher.*"
                    )

    # Tab 2: Register Students
    with tab_students:
        st.subheader("Register New Student")
        with st.form("add_student_form"):
            admission_no = st.text_input("Admission Number (e.g. ADM/2026/001)").lower()
            student_name = st.text_input("Student Full Name").lower()
            student_class = st.text_input("Current Class (e.g. Grade 9A)").lower()
            submit_student = st.form_submit_button("Register Student")

            if submit_student:
                if not all([admission_no, student_name, student_class]):
                    st.error("All student fields are required.")
                else:
                    create_student(
                        school_id, admission_no, student_name, student_class
                    )
                    st.success(f"Student {student_name} registered under {student_class}!")

    # Tab 3: Overview Lists
    with tab_list:
        st.subheader("Registered Teachers")
        teachers = get_teachers_by_school(school_id)
        if teachers:
            st.dataframe(
                [
                    {
                        "Full Name": t["full_name"],
                        "Email": t["email"],
                        "Assigned Classes": ", ".join(
                            t.get("assigned_classes", [])
                        ),
                        "Total Students": get_student_count_for_classes(
                            school_id=st.session_state.school_id,
                            class_names=t.get("assigned_classes", []),
                        ),
                    }
                    for t in teachers
                ],
                use_container_width=True,
            )
        else:
            st.info("No teachers registered yet.")

        teacher_email = st.text_input("Enter Teacher Email to Delete")

        if st.button("Delete Teacher Account", type="primary"):
            if not teacher_email:
                st.warning("Please enter an email address.")
            else:
                # Check if user exists
                existing_teacher = get_user_by_email(teacher_email)

                if not existing_teacher:
                    st.error("❌ No account found with this email address.")
                elif existing_teacher.get("role") != "TEACHER":
                    st.error("❌ This account is an Admin and cannot be deleted here.")
                else:
                    # Proceed with deletion
                    success = delete_teacher_by_email(
                        school_id=st.session_state.school_id, teacher_email=teacher_email
                    )
                    if success:
                        st.success(
                            f"✅ Account for '{existing_teacher.get('full_name')}' deleted successfully!"
                        )
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete account. Please try again.")


# 3. TEACHER DASHBOARD VIEW (GRADEBOOK & PDF GENERATION)
def render_teacher_dashboard() -> None:
    """Renders Gradebook for teachers to enter CA/Exam scores and download PDFs."""
    st.title(f"📊 Teacher Gradebook - {st.session_state['school_name'].title()}")

    user = st.session_state["user"]
    school_id = st.session_state["school_id"]
    assigned_classes = user.get("assigned_classes", [])

    if not assigned_classes:
        st.warning("You have not been assigned any classes yet. Contact your Admin.")
        return

    # Selection Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_class = st.selectbox("Select Class", assigned_classes)
    with col2:
        academic_session = st.selectbox("Academic Session", ["2025/2026", "2026/2027"])
    with col3:
        academic_term = st.selectbox(
            "Academic Term", ["First Term", "Second Term", "Third Term"]
        )

    st.markdown("---")

    tab_gradebook, tab_reports = st.tabs(
        ["📝 Input Scores", "📜 Class Leaderboard & PDF Export"]
    )

    # Tab 1: Dynamic Gradebook Input (Subject-by-Subject for all students)
    with tab_gradebook:
        st.subheader(f"Batch Gradebook Entry — {selected_class.title()}")
        students = get_students_by_class(school_id, selected_class)

        if not students:
            st.info(f"No students registered in {selected_class} yet.")
        else:
            # Select/Type Subject Name
            subject_name = st.text_input(
                "Enter Target Subject (e.g., Mathematics, English, Basic Science)",
                value="Mathematics",
            ).strip()

            st.info(
                f"📝 Entering grades for **{subject_name.title()}** across all students in **{selected_class}**"
            )

            with st.form("batch_subject_entry_form"):
                updated_scores_data = []

                for student in students:
                    st.markdown(
                        f"**{student['full_name'].title()}** (`{student['admission_no'].upper()}`)"
                    )
                    c1, c2, c3 = st.columns([2, 2, 4])
                    with c1:
                        ca = st.number_input(
                            "CA (30)",
                            min_value=0,
                            max_value=30,
                            value=0,
                            step=10,
                            key=f"ca_{student['_id']}_{subject_name}",
                        )
                    with c2:
                        exam = st.number_input(
                            "Exam (70)",
                            min_value=0,
                            max_value=70,
                            value=0,
                            step=10,
                            key=f"exam_{student['_id']}_{subject_name}",
                        )
                    with c3:
                        comment = st.text_input(
                            "Teacher Comment (Optional)",
                            value="Good effort.",
                            key=f"comm_{student['_id']}_{subject_name}",
                        )

                    updated_scores_data.append(
                        {
                            "student_id": student["_id"],
                            "ca_score": ca,
                            "exam_score": exam,
                            "comment": comment,
                        }
                    )
                    st.divider()

                submit_grades = st.form_submit_button(
                    f"💾 Save {subject_name.title()} Scores for All Students",
                    type="primary",
                )

                if submit_grades:
                    if not subject_name:
                        st.error("Please specify a subject name.")
                    else:
                        for entry in updated_scores_data:
                            save_or_update_student_subject_score(
                                school_id=school_id,
                                student_id=entry["student_id"],
                                class_name=selected_class,
                                academic_term=academic_term,
                                academic_session=academic_session,
                                subject_name=subject_name,
                                ca_score=entry["ca_score"],
                                exam_score=entry["exam_score"],
                                teacher_comment=entry["comment"],
                            )

                        # Re-calculate ordinal class ranks for the cohort
                        compute_and_update_class_ranks(
                            school_id,
                            selected_class,
                            academic_term,
                            academic_session,
                        )

                        st.success(
                            f"Successfully saved {subject_name.title()} scores! You can now select another subject."
                        )
                        st.rerun()

    # Tab 2: Leaderboard & PDF Downloads
    with tab_reports:
        st.subheader(f"Leaderboard & PDF Exports - {selected_class}")
        results = get_class_results(
            school_id, selected_class, academic_term, academic_session
        )

        if not results:
            st.info("No recorded results available for this term yet.")
        else:
            students = {
                s["_id"]: s for s in get_students_by_class(school_id, selected_class)
            }
            results_sorted = sorted(
                results, key=lambda x: x.get("class_rank") or 999
            )

            for res in results_sorted:
                stud_info = students.get(res["student_id"], {})
                rank = res.get("class_rank")
                ordinal_str = get_ordinal(rank) if rank else "N/A"

                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(
                        f"**{stud_info.get('full_name', 'Student')}** (`{stud_info.get('admission_no', '')}`)"
                    )
                with col2:
                    st.write(
                        f"Rank: **{ordinal_str}** | Total: **{res.get('overall_total', 0):.1f}**"
                    )
                with col3:
                    pdf_bytes = generate_student_pdf(
                        st.session_state["school_name"], stud_info, res
                    )
                    st.download_button(
                        label="📄 Download PDF",
                        data=pdf_bytes,
                        file_name=f"{stud_info.get('full_name', 'Student')}_Report.pdf",
                        mime="application/pdf",
                        key=f"pdf_{res['_id']}",
                    )
                st.divider()


# ==============================================================================
# MONGODB ATLAS (CLOUD) / STREAMLIT UI NOTE
# ==============================================================================
# In production cloud deployments (e.g. Streamlit Community Cloud), ensure user
# session state resets cleanly on logout by executing `st.session_state.clear()`
# and invoking `st.rerun()` to return users to the authentication view.