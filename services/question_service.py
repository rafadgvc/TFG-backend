from models.question.question_schema import QuestionSchema
from models.question.question import Question
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
import requests
from excepts import NoDataFound
from sqlalchemy.exc import IntegrityError

blp = Blueprint("Question", __name__, url_prefix="/question")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
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
@blp.arguments(QuestionSchema)
@blp.response(200, QuestionSchema)
def add_question(question_data):
    """ Creates a question and adds it to the database
    """
    # TODO: Check if a user is logged
    try:
        question = QuestionSchema().load(question_data)
        return Question.insert_question(
            session=SESSION,
            title=question['title'],
            subject_id=question['subject_id'],
            answer1=question['answer1'],
            answer2=question['answer2'],
            answer3=question['answer3'],
            answer4=question['answer4']
        )
    except Exception as e:
        abort(400, message=str(e))
