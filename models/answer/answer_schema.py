from marshmallow import Schema, fields, post_dump


class AnswerSchema(Schema):
    id = fields.Integer()
    body = fields.String()
    question_id = fields.Integer()
    points = fields.Integer()

class AnswerReducedSchema(Schema):
    body = fields.String()
    question_id = fields.Integer()
    points = fields.Integer()

class AnswerListSchema(Schema):
    items = fields.List(fields.Nested(AnswerSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_answers(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data


