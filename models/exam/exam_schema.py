from marshmallow import Schema, fields, post_dump, EXCLUDE

from models.answer.answer_schema import AnswerListSchema, AnswerAddListSchema
from models.question.question_schema import FullQuestionListSchema
from models.question_parameter.question_parameter_schema import QuestionParameterListSchema


class ExamSchema(Schema):
    title = fields.String()
    subject_id = fields.Integer()
    question_ids = fields.List(fields.Integer())
    class Meta:
        unknown = EXCLUDE


class FullExamSchema(Schema):
    id = fields.Integer()
    title = fields.String()
    subject_id = fields.Integer()
    connected = fields.Boolean()
    time = fields.Integer()
    difficulty = fields.Integer()
    questions = fields.Nested(FullQuestionListSchema)
    class Meta:
        unknown = EXCLUDE


class ExamSummarySchema(Schema):
    id = fields.Integer()
    title = fields.String()
    time = fields.Integer()
    difficulty = fields.Integer()
    question_number = fields.Integer()
    class Meta:
        unknown = EXCLUDE

class ExamListSchema(Schema):
    items = fields.List(fields.Nested(ExamSummarySchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_exams(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data
