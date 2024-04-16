from marshmallow import Schema, fields


class QuestionSchema(Schema):
    title = fields.String()
    answer1 = fields.String()
    answer2 = fields.String()
    answer3 = fields.String()
    answer4 = fields.String()
    subject_id = fields.Integer()

