from flask import request
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.result.result import Result
from models.result.result_schema import ResultReducedSchema, ResultSchema, ResultListSchema, CSVResultSchema, \
    ResultDetailListSchema
from utils.common_schema import PaginationSchema

blp = Blueprint("Result", __name__, url_prefix="/result")
Session = create_db()
SESSION = Session()


@blp.route('/upload', methods=["POST"])
@jwt_required()
@blp.response(200, ResultListSchema)
def upload_results():
    """ Uploads a CSV file and adds results """
    if 'file' not in request.files:
        abort(400, message="CSV file not provided")

    file = request.files['file']

    try:
        results = Result.insert_results_from_csv(session=SESSION, file=file)
        return {"items": results}, 200
    except FileNotFoundError:
        abort(400, message="File not found")
    except Exception as e:
        abort(400, message=str(e))

@blp.route('<int:id>', methods=["DELETE"])
@jwt_required()
@blp.response(204)
def delete_results_of_exam(id):
    """ Deletes results related to an exam
    """
    try:

        Result.delete_results_of_exam(
            session=SESSION,
            exam_id=id
        )
    except Exception as e:
        abort(400, message=str(e))

@blp.route('/list/<int:subject_id>', methods=["GET"])
@jwt_required()
@blp.arguments(PaginationSchema, location='query')
@blp.response(200, ResultDetailListSchema)
def get_subject_exams(pagination_params, subject_id):
    """ Returns list of results
    """
    return Result.get_results_list(
        SESSION,
        limit=pagination_params.get('limit', None),
        offset=pagination_params.get('offset', 0),
        subject_id=subject_id
    )
