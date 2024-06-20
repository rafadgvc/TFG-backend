from flask import request
from flask_jwt_extended import jwt_required

from models.question.question_schema import QuestionListSchema, QuestionReducedSchema, FullQuestionSchema, \
    ImportQuestionSchema
from models.question.question import Question
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.question_parameter.question_parameter import QuestionParameter
from models.answer.answer import Answer
from utils.common_schema import PaginationSchema

blp = Blueprint("Question", __name__, url_prefix="/question")
Session = create_db()
SESSION = Session()



@blp.route('', methods=["POST"])
@jwt_required()
@blp.arguments(QuestionReducedSchema)
@blp.response(200, FullQuestionSchema)
def add_question(question_data):
    """ Creates a question and adds it to the database
    """
    from models.answer.answer import Answer
    try:
        question = FullQuestionSchema().load(question_data)
        answers_data = question.pop('answers', [])
        question_parameters_data = question.pop('question_parameters', [])
        node_ids = question.pop('node_ids', [])
        new_question = Question.insert_question(
            session=SESSION,
            title=question.get('title'),
            subject_id=question.get('subject_id'),
            node_ids=node_ids,
            time=question.get('time'),
            difficulty=question.get('difficulty'),
            type=question.get('type'),
            active=question.get('active'),
            parametrized=question_parameters_data is not [],
            answers=answers_data.get('items', []),
            question_parameters=question_parameters_data
        )

        return new_question
    except Exception as e:
        abort(400, message=str(e))


@blp.route('<int:id>', methods=["DELETE"])
@jwt_required()
@blp.response(204)
def delete_question(id):
    """ Deletes question
    """
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


@blp.route('/subject-questions/<int:id>', methods=["GET"])
@jwt_required()
@blp.arguments(PaginationSchema, location='query')
@blp.response(200, QuestionListSchema)
def get_subject_questions(pagination_params, id):
    """ Returns questions that belong to the current user and a specific subject
    """
    return Question.get_subject_questions(
        SESSION,
        subject_id=id,
        limit=pagination_params.get('limit', None),
        offset=pagination_params.get('offset', 0),
    )


@blp.route('/full/<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, FullQuestionSchema)
def get_full_question(id):
    """ Returns question with its answers created by the current user
    """
    return Question.get_full_question(
        session=SESSION,
        id=id,
        )

@blp.route('/disable/<int:id>', methods=["PUT"])
@jwt_required()
@blp.response(200, FullQuestionSchema)
def disable_question(id):
    """ Disables question and returns it
    """
    return Question.disable_question(
        session=SESSION,
        id=id,
        )

@blp.route('/<int:question_id>', methods=["PUT"])
@jwt_required()
@blp.arguments(FullQuestionSchema)
@blp.response(200, FullQuestionSchema)
def update_question(question_data, question_id):
    """ Updates a question and returns the updated question """
    try:
        updated_question = Question.update_question(
            session=SESSION,
            question_id=question_id,
            title=question_data.get('title'),
            subject_id=question_data.get('subject_id'),
            node_ids=question_data.get('node_ids', []),
            difficulty=question_data.get('difficulty'),
            time=question_data.get('time'),
            type=question_data.get('type'),
            active=question_data.get('active'),
            question_parameters_data=question_data.get('question_parameters', {}).get('items', []),
            answers_data=question_data.get('answers', {}).get('items', [])
        )
        return updated_question
    except Exception as e:
        abort(400, message=str(e))

@blp.route('/upload', methods=["POST"])
@jwt_required()
@blp.arguments(ImportQuestionSchema, location='query')
@blp.response(200, QuestionListSchema)
def upload_questions(import_data):
    """ Uploads a CSV file and adds results """
    if 'file' not in request.files:
        abort(400, message="CSV file not provided")

    file = request.files['file']

    try:
        questions = Question.insert_questions_from_csv(
            session=SESSION,
            file=file,
            subject_id=import_data.get('subject_id'),
            difficulty=import_data.get('difficulty', 1),
            time=import_data.get('time', 1),
        )
        return {"items": questions}, 200
    except FileNotFoundError:
        abort(400, message="File not found")
    except Exception as e:
        abort(400, message=str(e))


@blp.route('/upload_aiken', methods=["POST"])
@jwt_required()
@blp.arguments(ImportQuestionSchema, location='query')
@blp.response(200, QuestionListSchema)
def upload_questions_aiken(import_data):
    """ Uploads a text file with Aiken format questions and adds results """
    if 'file' not in request.files:
        abort(400, message="Text file not provided")

    file = request.files['file']

    try:
        questions = Question.insert_questions_from_aiken(
            session=SESSION,
            file=file,
            subject_id=import_data.get('subject_id'),
            difficulty=import_data.get('difficulty', 1),
            time=import_data.get('time', 1),
        )
        return {"items": questions}, 200
    except FileNotFoundError:
        abort(400, message="File not found")
    except Exception as e:
        abort(400, message=str(e))