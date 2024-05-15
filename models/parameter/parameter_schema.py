from marshmallow import Schema, fields, post_dump


class ParameterSchema(Schema):
    value = fields.String()

class ParameterListSchema(Schema):
    items = fields.List(fields.Nested(ParameterSchema))
    total = fields.Integer()

    @post_dump(pass_many=True)
    def add_total_parameters(self, data, many, **kwargs):
        data['total'] = len(data['items'])
        return data