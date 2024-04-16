from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.subject.subject import Subject
from models.subject.subject_schema import SubjectSchema

blp = Blueprint("Subject", __name__, url_prefix="/subject")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@blp.response(200, SubjectSchema)
def get_subject(id):
    """ Returns subject
    """
    # TODO: Check if a user is logged and owns the subject
    try:

        return Subject.get_subject(
            SESSION,
            id=id
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
