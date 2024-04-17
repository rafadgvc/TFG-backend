from marshmallow import Schema, fields


class PaginationSchema(Schema):
    limit = fields.Integer()
    offset = fields.Integer()
