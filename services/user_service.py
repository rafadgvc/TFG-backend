from flask_smorest import Blueprint, abort
from db.versions.db import create_db
from models.user.user import User
from models.user.user_schema import UserRestrictedSchema, UserLoginSchema, UserSignUpSchema, FullUserSchema, AccessTokenSchema
from flask import jsonify
from flask_jwt_extended import create_access_token, jwt_required, set_access_cookies, unset_jwt_cookies
import bcrypt


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


@blp.route('/signup', methods=["POST"])
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


@blp.route('/login', methods=['POST'])
@blp.arguments(UserLoginSchema)
@blp.response(200, AccessTokenSchema)
def login(user_data):
    """ Logs in and sets an access token in the browser
    """
    email = user_data.get('email', None)
    password = user_data.get('password', None)
    if not email or not password:
        return jsonify({"msg": "Falta el email o la contraseña"}), 400

    user = User.get_user_by_email(SESSION, email)
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"msg": "Credenciales incorrectas"}), 401

    access_token = create_access_token(identity=user.id)
    response = AccessTokenSchema().dump({"access_token_cookie": access_token})

    # Establecer la cookie de acceso
    resp = jsonify(response)
    set_access_cookies(resp, access_token)
    return resp, 200

@blp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """ Logs out the current user and unsets the token
    """
    resp = jsonify({"msg": "Logout exitoso"})
    unset_jwt_cookies(resp)
    return resp, 200
