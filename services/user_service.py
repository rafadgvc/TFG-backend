from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.subject.subject import Subject
from models.subject.subject_schema import SubjectSchema
from models.user.user import User
from models.user.user_schema import UserRestrictedSchema, UserSignUpSchema, FullUserSchema

blp = Blueprint("User", __name__, url_prefix="/user")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@blp.response(200, UserRestrictedSchema)
def get_user(id):
    """ Returns user
    """
    try:

        return User.get_user(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('', methods=["POST"])
@blp.arguments(UserSignUpSchema)
@blp.response(200, FullUserSchema)
def add_user(user_data):
    """ Creates a user
    """
    try:
        return User.insert_user(
            session=SESSION,
            email=user_data['email'],
            name=user_data['name'],
            password=user_data['password']
        )
    except Exception as e:
        abort(400, message=str(e))
