from marshmallow import Schema, fields, post_dump

class NodeSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    subject_id = fields.Integer()
    parent_id = fields.Integer()

class NodeReducedSchema(Schema):
    name = fields.String()
    subject_id = fields.Integer()
    parent_id = fields.Integer()

class NodeListSchema(Schema):
    items = fields.List(fields.Nested(NodeSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_nodes(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data