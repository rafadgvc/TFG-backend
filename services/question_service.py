from flask_jwt_extended import jwt_required

from models.question.question_schema import QuestionSchema, QuestionListSchema, QuestionReducedSchema, \
    FullQuestionSchema
from models.question.question import Question
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from utils.common_schema import PaginationSchema

blp = Blueprint("Question", __name__, url_prefix="/question")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, QuestionSchema)
def get_question(id):
    """ Returns question
    """
    # TODO: Check if a user is logged and owns the question
    try:

        return Question.get_question(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('', methods=["POST"])
@jwt_required()
@blp.arguments(QuestionReducedSchema)
@blp.response(200, QuestionSchema)
def add_question(question_data):
    """ Creates a question and adds it to the database
    """
    try:
        question = QuestionSchema().load(question_data)
        return Question.insert_question(
            session=SESSION,
            title=question.get('title'),
            subject_id=question.get('subject_id'),
            level_id=question.get('level_id'),
            time=question.get('time'),
            difficulty=question.get('difficulty'),
            type=question.get('type'),
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('<int:id>', methods=["DELETE"])
@jwt_required()
@blp.response(204)
def delete_question(id):
    """ Deletes question
    """
    # TODO: Check if a user is logged and owns the question
    try:

        Question.delete_question(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('/user-questions', methods=["GET"])
@jwt_required()
@blp.arguments(PaginationSchema, location='query')
@blp.response(200, QuestionListSchema)
def get_user_questions(pagination_params):
    """ Returns questions created by the current user
    """
    return Question.get_user_questions(
        SESSION,
        limit=pagination_params.get('limit', None),
        offset=pagination_params.get('offset', 0),
    )

@blp.route('/full-question/<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, FullQuestionSchema)
def get_full_question(id):
    """ Returns question with its answers created by the current user
    """
    return Question.get_full_question(
        session=SESSION,
        id=id,
        )