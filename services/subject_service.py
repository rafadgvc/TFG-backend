from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.subject.subject import Subject
from models.subject.subject_schema import SubjectSchema, BasicSubjectSchema

blp = Blueprint("Subject", __name__, url_prefix="/subject")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, SubjectSchema)
def get_subject(id):
    """ Returns subject
    """
    return Subject.get_subject(
        SESSION,
        id=id
    )



@blp.route('', methods=["POST"])
@blp.arguments(BasicSubjectSchema)
@jwt_required()
@blp.response(200, SubjectSchema)
def add_subject(subject_data):
    """ Creates a subject
    """
    try:
        subject = SubjectSchema().load(subject_data)
        return Subject.insert_subject(
            session=SESSION,
            name=subject_data['name']

        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('<int:id>', methods=["DELETE"])
@jwt_required()
@blp.response(204)
def delete_subject(id):
    """ Deletes subject
    """
    try:
        Subject.delete_subject(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))
