from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.subject.subject import Subject
from models.subject.subject_schema import SubjectSchema
from utils import get_current_user_id

blp = Blueprint("Subject", __name__, url_prefix="/subject")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, SubjectSchema)
def get_subject(id):
    """ Returns subject
    """
    current_user_id = get_jwt_identity()
    try:
        return Subject.get_subject(
            SESSION,
            id=id,
            user_id=current_user_id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('', methods=["POST"])
@blp.arguments(SubjectSchema)
@blp.response(200, SubjectSchema)
def add_subject(subject_data):
    """ Creates a subject
    """
    # TODO: Check if a user is logged
    try:
        subject = SubjectSchema().load(subject_data)
        return Subject.insert_subject(
            session=SESSION,
            user_id=subject_data['user_id'],
            name=subject_data['name']

        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('<int:id>', methods=["DELETE"])
@blp.response(204)
def delete_question(id):
    """ Deletes subject
    """
    # TODO: Check if a user is logged and owns the subject
    try:

        Subject.delete_subject(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))
