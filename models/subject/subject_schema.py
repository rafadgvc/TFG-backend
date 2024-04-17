from marshmallow import Schema, fields


class SubjectSchema(Schema):
    id = fields.Integer()
    name = fields.String()

class BasicSubjectSchema(Schema):
    name = fields.String()

