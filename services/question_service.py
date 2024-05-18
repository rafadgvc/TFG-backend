from flask_jwt_extended import jwt_required

from models.question.question_schema import QuestionSchema, QuestionListSchema, QuestionReducedSchema, \
    FullQuestionSchema
from models.question.question import Question
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.question_parameter.question_parameter import QuestionParameter
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
        )

        new_question['answers'] = {'items': [], 'total': 0}

        for answer_data in answers_data.get('items'):
            new_answer = Answer.insert_answer(
                session=SESSION,
                question_id=new_question['id'],
                body=answer_data.get('body'),
                points=answer_data.get('points'),
            )
            new_question['answers']['items'].append(new_answer)
            new_question['answers']['total'] += 1

        if question_parameters_data is not []:
            new_question['question_parameters'] = {'items': [], 'total': 0}

            for question_parameter_data in question_parameters_data.get('items'):
                new_question_parameter = QuestionParameter.insert_question_parameter(
                    session=SESSION,
                    question_id=new_question['id'],
                    value=question_parameter_data.get('value'),
                    group=question_parameter_data.get('group'),
                    position=question_parameter_data.get('position')
                )
                new_question['question_parameters']['items'].append(new_question_parameter)
                new_question['question_parameters']['total'] += 1

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