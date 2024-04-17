from flask_jwt_extended import get_jwt_identity

def get_current_user_id():
    # Obtener el ID del usuario a partir token de acceso
    current_user_id = get_jwt_identity()
    return current_user_id
