from marshmallow import Schema, fields


class SubjectSchema(Schema):
    user_id = fields.Integer()
    name = fields.String()

