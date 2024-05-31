from marshmallow import Schema, fields, post_dump, EXCLUDE


class CSVResultSchema(Schema):
    file = fields.Raw(type='file', required=True)

    class Meta:
        unknown = EXCLUDE


class ResultReducedSchema(Schema):
    question_id = fields.Integer()
    exam_id = fields.Integer()
    time = fields.Integer()
    taker = fields.Integer()
    points = fields.Integer()

    class Meta:
        unknown = EXCLUDE

class ResultSchema(Schema):
    id = fields.Integer()
    question_id = fields.Integer()
    exam_id = fields.Integer()
    time = fields.Integer()
    taker = fields.Integer()
    points = fields.Integer()

    class Meta:
        unknown = EXCLUDE

class ResultListSchema(Schema):
    items = fields.List(fields.Nested(ResultSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_results(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data


class ResultDetailSchema(Schema):
    id = fields.Integer()
    question_id = fields.Integer()
    exam_id = fields.Integer()
    time = fields.Integer()
    taker = fields.Integer()
    points = fields.Integer()
    question_title = fields.String()
    exam_title = fields.String()

    class Meta:
        unknown = EXCLUDE

class ResultDetailListSchema(Schema):
    items = fields.List(fields.Nested(ResultDetailSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_results(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data
