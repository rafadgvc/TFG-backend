from flask_jwt_extended import jwt_required
from models.level.level import Level
from models.level.level_schema import LevelSchema, LevelReducedSchema
from flask_smorest import Blueprint, abort
from db.versions.db import create_db

blp = Blueprint("Level", __name__, url_prefix="/level")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, LevelSchema)
def get_level(id):
    """ Returns level
    """
    try:

        return Level.get_level(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('', methods=["POST"])
@jwt_required()
@blp.arguments(LevelReducedSchema)
@blp.response(200, LevelSchema)
def add_level(level_data):
    """ Creates a level and adds it to the database
    """
    try:
        level = LevelSchema().load(level_data)
        return Level.insert_level(
            session=SESSION,
            name=level['name'],
            subject_id=level['subject_id'],
            parent_id=level.get('parent_id', None),
        )
    except Exception as e:
        abort(400, message=str(e))
