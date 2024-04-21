from marshmallow import Schema, fields, EXCLUDE


class FullUserSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.Email()
    password = fields.String()
    class Meta:
        unknown = EXCLUDE


class UserRestrictedSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.Email()
    class Meta:
        unknown = EXCLUDE


class UserSignUpSchema(Schema):
    name = fields.String()
    email = fields.Email()
    password = fields.String()

    class Meta:
        unknown = EXCLUDE


class UserLoginSchema(Schema):
    email = fields.Email()
    password = fields.String()
    class Meta:
        unknown = EXCLUDE


class AccessTokenSchema(Schema):
    access_token_cookie = fields.String()
