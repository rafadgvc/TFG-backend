from flask_jwt_extended import jwt_required

from models.exam.exam import Exam
from models.exam.exam_schema import ExamSchema, FullExamSchema, ExamListSchema
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from utils.common_schema import PaginationSchema

blp = Blueprint("Exam", __name__, url_prefix="/exam")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, FullExamSchema)
def get_exam(id):
    """ Returns exam
    """
    try:

        return Exam.get_exam(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('', methods=["POST"])
@jwt_required()
@blp.arguments(ExamSchema)
@blp.response(200, FullExamSchema)
def add_exam(exam_data):
    """ Creates an exam and adds it to the database
    """
    try:

        exam = FullExamSchema().load(exam_data)
        question_ids = exam_data.pop('question_ids', [])
        new_exam = Exam.insert_exam(
            session=SESSION,
            title=exam.get('title'),
            subject_id=exam.get('subject_id'),
            question_ids=question_ids
        )

        return new_exam
    except Exception as e:
        abort(400, message=str(e))


@blp.route('/list/<int:subject_id>', methods=["GET"])
@jwt_required()
@blp.arguments(PaginationSchema, location='query')
@blp.response(200, ExamListSchema)
def get_subject_exams(pagination_params, subject_id):
    """ Returns list of exams in a subject
    """
    return Exam.get_subject_exams(
        SESSION,
        limit=pagination_params.get('limit', None),
        offset=pagination_params.get('offset', 0),
        subject_id=subject_id
    )