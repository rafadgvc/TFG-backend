from marshmallow import Schema, fields, post_dump


class QuestionSchema(Schema):
    id = fields.Integer()
    title = fields.String()
    answer1 = fields.String()
    answer2 = fields.String()
    answer3 = fields.String()
    answer4 = fields.String()
    subject_id = fields.Integer()

class QuestionListSchema(Schema):
    items = fields.List(fields.Nested(QuestionSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_questions(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data


