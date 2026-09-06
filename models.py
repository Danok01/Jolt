from bson import ObjectId
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class MongoBaseModel(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"


class Grade(str, Enum):
    A = "A"  # 70 - 100
    B = "B"  # 60 - 69
    C = "C"  # 50 - 59
    D = "D"  # 45 - 49
    F = "F"  # 0 - 44


# 1. SCHOOL MODEL
class SchoolModel(MongoBaseModel):
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# 2. USER MODEL (Admins & Teachers)
class UserModel(MongoBaseModel):
    school_id: str  # Multi-tenant scoping key
    full_name: str
    email: EmailStr
    password_hash: str
    role: UserRole
    is_temporary_password: bool = True  # Flag to enforce password update
    assigned_classes: List[str] = []  # e.g., ["Grade 9A", "Grade 9B"]
    created_at: datetime = Field(default_factory=datetime.utcnow)


# 3. STUDENT MODEL
class StudentModel(MongoBaseModel):
    school_id: str
    admission_no: str  # Unique identifier within the school
    full_name: str
    current_class: str  # e.g., "Grade 9A"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# 4. SUBJECT SCORE SUB-MODEL
class SubjectScore(MongoBaseModel):
    subject_name: str
    ca_score: float = Field(..., ge=0, le=30)  # Max 30 points
    exam_score: float = Field(..., ge=0, le=70)  # Max 70 points
    total_score: float = 0.0  # Calculated as ca_score + exam_score
    grade: Optional[Grade] = None  # Calculated letter grade


# 5. STUDENT RESULT MODEL
class StudentResultModel(MongoBaseModel):
    school_id: str
    student_id: str
    class_name: str  # Class cohort for ranking calculations
    academic_term: str  # e.g., "First Term"
    academic_session: str  # e.g., "2025/2026"
    scores: List[SubjectScore] = []
    overall_total: float = 0.0  # Sum of total_scores across subjects
    overall_average: float = 0.0  # Average percentage
    class_rank: Optional[int] = None  # Ordinal class position (1 = 1st, 2 = 2nd)
    teacher_comment: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# MONGODB ATLAS (CLOUD) DOCUMENTATION NOTE
# ==============================================================================
# In MongoDB Atlas, object IDs are stored as BSON ObjectId types. When retrieving
# documents using PyMongo, convert string `_id` values to ObjectId for queries:
#
# from bson.objectid import ObjectId
# document = collection.find_one({"_id": ObjectId(document_id)})