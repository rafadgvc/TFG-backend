from marshmallow import Schema, fields, post_dump
from models.parameter.parameter_schema import ParameterListSchema


class QuestionParameterSchema(Schema):
    question_id = fields.String()
    parameters = fields.Nested(ParameterListSchema)

class QuestionParameterListSchema(Schema):
    items = fields.List(fields.Nested(QuestionParameterSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_parameters(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data