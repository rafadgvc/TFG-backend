from marshmallow import Schema, fields, post_dump, EXCLUDE

from models.answer.answer_schema import AnswerListSchema, AnswerAddListSchema
from models.question_parameter.question_parameter_schema import QuestionParameterListSchema


class QuestionSchema(Schema):
    id = fields.Integer()
    title = fields.String()
    subject_id = fields.Integer()
    node_ids = fields.List(fields.Integer())
    active = fields.Boolean()
    connected = fields.Boolean()
    time = fields.Integer()
    difficulty = fields.Integer()
    type = fields.String()
    class Meta:
        unknown = EXCLUDE

class QuestionReducedSchema(Schema):
    title = fields.String()
    subject_id = fields.Integer()
    node_ids = fields.List(fields.Integer())
    active = fields.Boolean()
    time = fields.Integer()
    difficulty = fields.Integer()
    type = fields.String()
    section_number = fields.Integer()
    question_parameters = fields.Nested(QuestionParameterListSchema, nullable=True)
    answers = fields.Nested(AnswerAddListSchema)
    class Meta:
        unknown = EXCLUDE

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
    node_ids = fields.List(fields.Integer())
    active = fields.Boolean()
    connected = fields.Boolean()
    time = fields.Integer()
    difficulty = fields.Integer()
    type = fields.String()
    section_number = fields.Integer()
    answers = fields.Nested(AnswerListSchema)
    question_parameters = fields.Nested(QuestionParameterListSchema, nullable=True)
    class Meta:
        unknown = EXCLUDE

class FullQuestionListSchema(Schema):
    items = fields.List(fields.Nested(FullQuestionSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_questions(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data


class ImportQuestionSchema(Schema):
    subject_id = fields.Integer()
    time = fields.Integer()
    difficulty = fields.Integer()

