from marshmallow import Schema, fields


class FullUserSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.Email()
    password = fields.String()


class UserRestrictedSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.Email()


class UserSignUpSchema(Schema):
    name = fields.String()
    email = fields.Email()
    password = fields.String()


class UserLoginSchema(Schema):
    email = fields.Email()
    password = fields.String()


class AccessTokenSchema(Schema):
    access_token = fields.String()