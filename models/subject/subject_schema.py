from marshmallow import Schema, fields, post_dump


class SubjectSchema(Schema):
    id = fields.Integer()
    name = fields.String()

class BasicSubjectSchema(Schema):
    name = fields.String()

class SubjectListSchema(Schema):
    items = fields.List(fields.Nested(SubjectSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_subjects(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data

