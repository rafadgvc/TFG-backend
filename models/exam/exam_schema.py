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
