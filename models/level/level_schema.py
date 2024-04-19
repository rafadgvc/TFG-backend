from marshmallow import Schema, fields, post_dump

class LevelSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    subject_id = fields.Integer()
    parent_id = fields.Integer()

class LevelReducedSchema(Schema):
    name = fields.String()
    subject_id = fields.Integer()
    parent_id = fields.Integer()

class LevelListSchema(Schema):
    items = fields.List(fields.Nested(LevelSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_questions(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data