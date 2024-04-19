from marshmallow import Schema, fields, post_dump

from models.answer.answer_schema import AnswerListSchema


class QuestionSchema(Schema):
    id = fields.Integer()
    title = fields.String()
    subject_id = fields.Integer()
    level_id = fields.Integer()
    time = fields.Integer()
    difficulty = fields.Integer()
    type = fields.String()

class QuestionReducedSchema(Schema):
    title = fields.String()
    subject_id = fields.Integer()
    level_id = fields.Integer()
    time = fields.Integer()
    difficulty = fields.Integer()
    type = fields.String()

class QuestionListSchema(Schema):
    items = fields.List(fields.Nested(QuestionSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_questions(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data

class FullQuestionSchema(Schema):
    id = fields.Integer()
    title = fields.String()
    subject_id = fields.Integer()
    level_id = fields.Integer()
    time = fields.Integer()
    difficulty = fields.Integer()
    type = fields.String()
    answers = fields.Nested(AnswerListSchema)




