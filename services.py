import io
from typing import Dict, List, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from db import get_class_results, update_bulk_class_ranks
from utils import get_ordinal, calculate_grade

# 1. SCORE & GRADING CONFIGURATION
MAX_CA_SCORE = 30.0
MAX_EXAM_SCORE = 70.0



def process_subject_scores(
    raw_scores: List[Dict],
) -> Tuple[List[Dict], float, float]:
    """Validates raw CA/Exam scores, computes totals/grades, and calculates averages.

    Returns:
        Tuple containing (processed_scores_list, overall_total, overall_average)
    """
    processed_scores = []
    total_sum = 0.0

    for score_item in raw_scores:
        ca = min(max(float(score_item.get("ca_score", 0.0)), 0.0), MAX_CA_SCORE)
        exam = min(
            max(float(score_item.get("exam_score", 0.0)), 0.0), MAX_EXAM_SCORE
        )
        total = ca + exam
        grade = calculate_grade(total)

        processed_scores.append(
            {
                "subject_name": score_item["subject_name"],
                "ca_score": ca,
                "exam_score": exam,
                "total_score": total,
                "grade": grade,
            }
        )
        total_sum += total

    subject_count = len(processed_scores)
    overall_average = (
        round(total_sum / subject_count, 2) if subject_count > 0 else 0.0
    )

    return processed_scores, total_sum, overall_average


# 2. CLASS RANKING ALGORITHM
def compute_and_update_class_ranks(
    school_id: str,
    class_name: str,
    academic_term: str,
    academic_session: str,
) -> None:
    """Fetches all results for a class cohort, sorts by overall_total descending,

    computes ordinal positions (1st, 2nd, etc.), and updates MongoDB.
    """
    class_results = get_class_results(
        school_id, class_name, academic_term, academic_session
    )

    if not class_results:
        return

    # Sort results by overall total in descending order
    sorted_results = sorted(
        class_results, key=lambda x: x.get("overall_total", 0.0), reverse=True
    )

    rank_updates = []
    for rank_idx, result_doc in enumerate(sorted_results, start=1):
        rank_updates.append(
            {"result_id": result_doc["_id"], "class_rank": rank_idx}
        )

    # Persist batch updates to database
    update_bulk_class_ranks(rank_updates)


# 3. PDF REPORT CARD GENERATION ENGINE
def generate_student_pdf(
    school_name: str, student_info: Dict, result_data: Dict
) -> bytes:
    """Generates a professional PDF report card byte stream using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    elements = []
    styles = getSampleStyleSheet()

    # Custom Paragraph Styles
    header_style = ParagraphStyle(
        "SchoolHeader",
        parent=styles["Heading1"],
        fontSize=20,
        alignment=1,  # Center
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=6,
    )
    sub_header_style = ParagraphStyle(
        "SubHeader",
        parent=styles["Normal"],
        fontSize=12,
        alignment=1,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=15,
    )
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading2"],
        fontSize=14,
        alignment=1,
        textColor=colors.HexColor("#2B6CB0"),
        spaceAfter=15,
    )

    # Header Section
    elements.append(Paragraph(school_name.upper(), header_style))
    elements.append(
        Paragraph("OFFICIAL STUDENT ACADEMIC REPORT CARD", sub_header_style)
    )
    elements.append(
        Paragraph(
            f"<b>Session:</b> {result_data.get('academic_session', 'N/A')} | <b>Term:</b> {result_data.get('academic_term', 'N/A')}",
            title_style,
        )
    )
    elements.append(Spacer(1, 10))

    # Student Details Table
    rank_value = result_data.get("class_rank")
    ordinal_rank = get_ordinal(rank_value) if rank_value else "N/A"
    total_students = len(
        get_class_results(
            result_data.get("school_id", ""),
            result_data.get("class_name", "").title(),
            result_data.get("academic_term", ""),
            result_data.get("academic_session", ""),
        )
    )

    student_meta = [
        [
            f"Student Name: {student_info.get('full_name', 'N/A').title()}",
            f"Admission No: {student_info.get('admission_no', 'N/A')}",
        ],
        [
            f"Class: {result_data.get('class_name', 'N/A').title()}",
            f"Class Position: {ordinal_rank} (out of {total_students})",
        ],
    ]
    meta_table = Table(student_meta, colWidths=[270, 270])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2D3748")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # Subject Grades Table
    table_data = [
        ["Subject Name", "CA (30)", "Exam (70)", "Total (100)", "Grade"]
    ]
    for score in result_data.get("scores", []):
        table_data.append(
            [
                score["subject_name"],
                f"{score['ca_score']:.1f}",
                f"{score['exam_score']:.1f}",
                f"{score['total_score']:.1f}",
                score["grade"],
            ]
        )

    # Summary Row
    table_data.append(
        [
            "OVERALL SUMMARY",
            "-",
            "-",
            f"Total: {result_data.get('overall_total', 0.0):.1f}",
            f"Avg: {result_data.get('overall_average', 0.0):.1f}%",
        ]
    )

    grade_table = Table(
        table_data, colWidths=[180, 90, 90, 100, 80], hAlign="CENTER"
    )
    grade_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(grade_table)
    elements.append(Spacer(1, 20))

    # Teacher Remarks Section
    comment = result_data.get("teacher_comment", "No comment provided.")
    comment_box = [
        [Paragraph("<b>Teacher's Remarks:</b>", styles["Normal"])],
        [Paragraph(comment, styles["Normal"])],
    ]
    comment_table = Table(comment_box, colWidths=[540])
    comment_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFAF0")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#DD6B20")),
                ("PADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(comment_table)

    # Build Document
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==============================================================================
# MONGODB ATLAS (CLOUD) / DEPLOYMENT NOTE
# ==============================================================================
# When deploying this application to cloud environments (such as Streamlit Community Cloud,
# Heroku, or AWS Elastic Beanstalk), reportlab works directly in-memory without requiring
# local filesystem permissions, making it ideal for serverless PDF generation.