from marshmallow import Schema, fields, post_dump, EXCLUDE


class SubjectSchema(Schema):
    id = fields.Integer()
    name = fields.String()


class SubjectWithQuestionsSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    question_number = fields.Integer()

class BasicSubjectSchema(Schema):
    name = fields.String()

    class Meta:
        unknown = EXCLUDE

class SubjectListSchema(Schema):
    items = fields.List(fields.Nested(SubjectWithQuestionsSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_subjects(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data

