from sqlalchemy import Table, Integer, ForeignKey, Column
from db.versions.db import Base

node_question_association = Table(
    'node_question_association',
    Base.metadata,
    Column('node_id', Integer, ForeignKey('node.id')),
    Column('question_id', Integer, ForeignKey('question.id'))
)

exam_question_association = Table(
    'exam_question_association',
    Base.metadata,
    Column('question_id', Integer, ForeignKey('question.id')),
    Column('exam_id', Integer, ForeignKey('exam.id'))
)
