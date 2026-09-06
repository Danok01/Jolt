from datetime import datetime
from typing import Dict, List, Optional
from bson.objectid import ObjectId
from pymongo import MongoClient, ReturnDocument
from pydantic import ValidationError
from config import DB_NAME, MONGO_URI
from utils import hash_password, calculate_grade
from models import StudentModel, UserModel, SchoolModel
import re


# 1. DATABASE CONNECTION MANAGEMENT
def get_database():
    """Initializes and returns the PyMongo database instance."""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


db = get_database()


# 2. SCHOOL OPERATIONS
def create_school(school_name: str) -> str:
    """Creates a new school and returns its string ID."""
    try:
        school_doc = SchoolModel(
            name=school_name,
            created_at=datetime.utcnow(),
        )

        school_dict = school_doc.model_dump(by_alias=True, exclude={"id"})

        result = db.schools.insert_one(school_dict)
        return str(result.inserted_id)
    except ValidationError as e:
        raise ValueError(
            f"School Validation Failed: {e.errors()[0]['msg']}"
        ) from e



def get_school_by_id(school_id: str) -> Optional[Dict]:
    """Retrieves school record by ID."""
    return db.schools.find_one({"_id": ObjectId(school_id)})


# 3. USER OPERATIONS (Admins & Teachers)
def create_admin_user(
    school_id: str, full_name: str, email: str, password: str
) -> Dict:
    """Creates an initial School Admin account."""
    try:
        user_doc = UserModel(
            school_id=school_id,
            full_name=full_name,
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role="ADMIN",
            is_temporary_password=False,
            assigned_classes=[],
            created_at=datetime.utcnow(),
        )

        user_dict = user_doc.model_dump(by_alias=True, exclude={"id"})
        result = db.users.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        return user_dict
    except ValidationError as e:
        raise ValueError(
            f"User Validation Failed: {e.errors()[0]['msg']}"
        ) from e


def create_teacher_user(
    school_id: str,
    full_name: str,
    email: str,
    temp_password: str,
    assigned_classes: List[str],
) -> Dict:
    """Provisions a new Teacher account with a temporary password flag."""
    try:
        user_doc = UserModel(
            school_id=school_id,
            full_name=full_name,
            email=email.lower().strip(),
            password_hash=hash_password(temp_password),
            role="TEACHER",
            is_temporary_password=True,
            assigned_classes=assigned_classes,
            created_at=datetime.utcnow(),
        )

        user_dict = user_doc.model_dump(by_alias=True, exclude={"id"})
        result = db.users.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        return user_dict
    except ValidationError as e:
        raise ValueError(
            f"User Validation Failed: {e.errors()[0]['msg']}"
        ) from e


def get_user_by_email(email: str) -> Optional[Dict]:
    """Fetches user document by email address for authentication."""
    user = db.users.find_one({"email": email.lower().strip()})
    if user:
        user["_id"] = str(user["_id"])
    return user


def update_user_password(user_id: str, new_password: str) -> bool:
    """Updates password hash and sets temporary password status to False."""
    result = db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "password_hash": hash_password(new_password),
                "is_temporary_password": False,
            }
        },
    )
    return result.modified_count > 0


def get_teachers_by_school(school_id: str) -> List[Dict]:
    """Fetches all teacher records associated with a specific school."""
    teachers = list(
        db.users.find({"school_id": school_id, "role": "TEACHER"})
    )
    for teacher in teachers:
        teacher["_id"] = str(teacher["_id"])
    return teachers


# 4. STUDENT OPERATIONS
def create_student(
    school_id: str, admission_no: str, full_name: str, current_class: str
) -> Dict:
    """Registers a new student under a school cohort."""
    try:
        student_doc = StudentModel(
            school_id=school_id,
            admission_no=admission_no.strip(),
            full_name=full_name.strip(),
            current_class=current_class.strip(),
            created_at=datetime.utcnow(),
        )

        student_dict = student_doc.model_dump(by_alias=True, exclude={"id"})
        result = db.users.insert_one(student_dict)
        student_dict["_id"] = str(result.inserted_id)
        return student_dict
    except ValidationError as e:
        raise ValueError(
            f"User Validation Failed: {e.errors()[0]['msg']}"
        ) from e


def get_students_by_class(school_id: str, current_class: str) -> List[Dict]:
    """Retrieves all students enrolled in a specific class."""
    students = list(
        db.students.find(
            {"school_id": school_id, "current_class": current_class}
        )
    )
    for student in students:
        student["_id"] = str(student["_id"])
    return students


# 5. RESULT & GRADEBOOK OPERATIONS
def save_or_update_student_subject_score(
    school_id: str,
    student_id: str,
    class_name: str,
    academic_term: str,
    academic_session: str,
    subject_name: str,
    ca_score: float,
    exam_score: float,
    teacher_comment: Optional[str] = None,
) -> None:
    """Appends or updates a single subject score without erasing existing subjects."""
    filter_query = {
        "school_id": school_id,
        "student_id": student_id,
        "academic_term": academic_term,
        "academic_session": academic_session,
    }

    # 1. Fetch existing result document if it exists
    existing_result = db.results.find_one(filter_query)
    scores = existing_result.get("scores", []) if existing_result else []
    scores_dict = {
        s["subject_name"].lower(): s for s in scores
    }

    # 2. Process grade for current subject
    formatted_subject = subject_name.strip().title()
    ca = min(max(float(ca_score), 0.0), 30.0)
    exam = min(max(float(exam_score), 0.0), 70.0)
    total = ca + exam

    grade = calculate_grade(total)

    scores_dict[formatted_subject.lower()] = {
        "subject_name": formatted_subject,
        "ca_score": ca,
        "exam_score": exam,
        "total_score": total,
        "grade": grade,
    }

    # 3. Rebuild the list containing ALL subjects accumulated so far
    updated_scores = list(scores_dict.values())
    overall_total = sum(s["total_score"] for s in updated_scores)
    overall_average = round(overall_total / len(updated_scores), 2) if updated_scores else 0.0

    # 4. Save merged record back to MongoDB
    update_payload = {
        "$set": {
            "class_name": class_name,
            "scores": updated_scores,
            "overall_total": overall_total,
            "overall_average": overall_average,
            "updated_at": datetime.utcnow(),
        }
    }
    if teacher_comment:
        update_payload["$set"]["teacher_comment"] = teacher_comment

    db.results.update_one(filter_query, update_payload, upsert=True)


def get_class_results(
    school_id: str,
    class_name: str,
    academic_term: str,
    academic_session: str,
) -> List[Dict]:
    """Retrieves all academic result cards for a class cohort."""
    results = list(
        db.results.find(
            {
                "school_id": school_id,
                "class_name": class_name,
                "academic_term": academic_term,
                "academic_session": academic_session,
            }
        )
    )
    for res in results:
        res["_id"] = str(res["_id"])
    return results

def delete_teacher_by_email(school_id: str, teacher_email: str) -> bool:
    """Deletes a teacher account from MongoDB.

    Returns True if deleted, False if no matching record was found.
    """
    result = db.users.delete_one(
        {
            "school_id": school_id,
            "email": teacher_email.strip(),
            "role": "TEACHER",  # Safety check: prevents accidental deletion of ADMIN accounts
        }
    )
    return result.deleted_count > 0

def get_student_count_for_classes(
    school_id: str, class_names: list[str]
) -> int:
    """Counts students where 'current_class' matches any of the teacher's assigned classes."""
    cleaned_classes = [c.strip() for c in class_names if c and c.strip()]
    if not cleaned_classes:
        return 0

    # Match against 'current_class' instead of 'class_name'
    class_filters = [
        {"current_class": {"$regex": f"^{re.escape(c)}$", "$options": "i"}}
        for c in cleaned_classes
    ]

    return db.students.count_documents(
        {"school_id": str(school_id).strip(), "$or": class_filters}
    )

def update_bulk_class_ranks(rank_updates: List[Dict]) -> None:
    """Updates calculated ordinal class ranks across multiple result records."""
    for update in rank_updates:
        db.results.update_one(
            {"_id": ObjectId(update["result_id"])},
            {"$set": {"class_rank": update["class_rank"]}},
        )


# ==============================================================================
# MONGODB ATLAS (CLOUD) CONNECTION REFERENCE
# ==============================================================================
# When deploying to production with MongoDB Atlas, replace standard PyMongo client
# options with TLS/SSL options if required by your cloud configuration:
#
# client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=False)
#
# Atlas connection pooling is handled automatically by PyMongo's MongoClient.import os