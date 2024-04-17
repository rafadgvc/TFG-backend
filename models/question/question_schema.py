from marshmallow import Schema, fields


class QuestionSchema(Schema):
    id = fields.Integer()
    title = fields.String()
    answer1 = fields.String()
    answer2 = fields.String()
    answer3 = fields.String()
    answer4 = fields.String()
    subject_id = fields.Integer()

