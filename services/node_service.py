from flask_jwt_extended import jwt_required
from models.node.node import Node
from models.node.node_schema import NodeSchema, NodeReducedSchema
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.question.question_schema import FullQuestionListSchema

blp = Blueprint("Node", __name__, url_prefix="/node")
Session = create_db()
SESSION = Session()


@blp.route('<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, NodeSchema)
def get_node(id):
    """ Returns node
    """
    try:

        return Node.get_node(
            SESSION,
            id=id
        )
    except Exception as e:
        abort(400, message=str(e))


@blp.route('', methods=["POST"])
@jwt_required()
@blp.arguments(NodeReducedSchema)
@blp.response(200, NodeSchema)
def add_node(node_data):
    """ Creates a node and adds it to the database
    """
    try:
        node = NodeSchema().load(node_data)
        return Node.insert_node(
            session=SESSION,
            name=node['name'],
            subject_id=node['subject_id'],
            parent_id=node.get('parent_id', None),
        )
    except Exception as e:
        abort(400, message=str(e))

@blp.route('/full/<int:id>', methods=["GET"])
@jwt_required()
@blp.response(200, FullQuestionListSchema)
def get_questions_of_node(id):
    """ Returns the list of questions that a node has
    """
    return Node.get_questions_of_node(
        session=SESSION,
        node_id=id,
        )
