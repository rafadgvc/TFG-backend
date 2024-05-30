from flask import request
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.result.result import Result
from models.result.result_schema import ResultReducedSchema, ResultSchema, ResultListSchema, CSVResultSchema

blp = Blueprint("Result", __name__, url_prefix="/result")
Session = create_db()
SESSION = Session()


@blp.route('/upload', methods=["POST"])
@blp.arguments(CSVResultSchema)
@jwt_required()
@blp.response(200, ResultListSchema)
def upload_results(csv_data):
    """ Uploads a CSV file and adds results """
    if 'path' not in csv_data:
        abort(400, message="Path not provided in CSV data")

    try:
        with open(csv_data['path'], 'r') as file:
            results = Result.insert_results_from_csv(session=SESSION, file=file)
            return {"items": results}, 200
    except FileNotFoundError:
        abort(400, message="File not found")
    except Exception as e:
        abort(400, message=str(e))
