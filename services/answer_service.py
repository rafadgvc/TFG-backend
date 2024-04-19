from flask_jwt_extended import jwt_required

from models.answer.answer import Answer
from models.answer.answer_schema import AnswerSchema, AnswerListSchema, AnswerReducedSchema
from models.question.question_schema import QuestionSchema, QuestionListSchema
from models.question.question import Question
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from utils.common_schema import PaginationSchema

blp = Blueprint("Answer", __name__, url_prefix="/answer")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, AnswerSchema)
def get_answer(id):
    """ Returns answer
    """
    try:

        return Answer.get_answer(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('', methods=["POST"])
@jwt_required()
@blp.arguments(AnswerReducedSchema)
@blp.response(200, AnswerSchema)
def add_answer(answer_data):
    """ Creates an answer and adds it to the database
    """
    try:
        answer = AnswerSchema().load(answer_data)
        return Answer.insert_answer(
            session=SESSION,
            body=answer['body'],
            question_id=answer['question_id'],
            points=answer['points']
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('<int:id>', methods=["DELETE"])
@jwt_required()
@blp.response(204)
def delete_answer(id):
    """ Deletes answer
    """
    try:

        Answer.delete_answer(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('/question-answers', methods=["GET"])
@jwt_required()
@blp.arguments(PaginationSchema, location='query')
@blp.response(200, AnswerListSchema)
def get_question_answers(pagination_params):
    """ Returns answers from an specific question
    """
    return Answer.get_question_answer(
        SESSION,
        limit=pagination_params.get('limit', None),
        offset=pagination_params.get('offset', 0),
    )