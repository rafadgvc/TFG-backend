from marshmallow import Schema, fields, post_dump


class QuestionParameterFullSchema(Schema):
    question_id = fields.String()
    value = fields.String()
    position = fields.Integer()
    group = fields.Integer()

class QuestionParameterFullListSchema(Schema):
    items = fields.List(fields.Nested(QuestionParameterFullSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_parameters(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data

class QuestionParameterSchema(Schema):
    value = fields.String()
    position = fields.Integer()
    group = fields.Integer()

class QuestionParameterListSchema(Schema):
    items = fields.List(fields.Nested(QuestionParameterSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_parameters(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data