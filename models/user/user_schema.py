from marshmallow import Schema, fields


class FullUserSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.String()
    password = fields.String()


class UserRestrictedSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.String()


class UserSignUpSchema(Schema):
    name = fields.String()
    email = fields.String()
    password = fields.String()


