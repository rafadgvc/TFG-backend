from flask_jwt_extended import jwt_required

from models.exam.exam import Exam
from models.exam.exam_schema import ExamSchema, FullExamSchema, ExamListSchema, SectionSchema
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.question.question_schema import QuestionListSchema
from utils.common_schema import PaginationSchema
from models.question_parameter.question_parameter import QuestionParameter

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

@blp.route('/select-questions', methods=["GET"])
@jwt_required()
@blp.arguments(SectionSchema, location='query')
@blp.response(200, QuestionListSchema)
def select_node_questions(section_data):
    """ Returns questions that belong to the current user and a specific subject
    """
    return Exam.get_questions_to_select(
        SESSION,
        node_id=section_data.get('node_id'),
        time=section_data.get('time', None),
        difficulty=section_data.get('difficulty', None),
        repeat=section_data.get('repeat', None),
        type=section_data.get('type', None),
        question_number=section_data.get('question_number', None),

    )