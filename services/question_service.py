from models.question.question_schema import QuestionSchema
from models.question.question import Question
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
import requests
from excepts import NoDataFound
from sqlalchemy.exc import IntegrityError

blp = Blueprint("question", __name__, url_prefix="/question")
Session = create_db()
SESSION = Session()


@blp.route('', methods=["GET"])
def get_question():
    """ Returns question
    """
    return 'Any questions?'


@blp.route('', methods=["POST"])
@blp.arguments(QuestionSchema)
@blp.response(200, QuestionSchema)
def add_question(question_data):
    """ Creates a question and adds it to the database
    """
    for a in question_data:
        print(a)
    try:
        question = QuestionSchema().load(question_data)
        return Question.insert_question(
            SESSION,
            question['title'],
            question['answer1'],
            question['answer2'],
            question['answer3'],
            question['answer4']
        )
    except Exception as e:
        abort(400, message=str(e))
