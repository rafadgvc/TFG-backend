from typing import Set

from flask import abort
from sqlalchemy import Integer, String, select, delete, ForeignKey, func, or_, distinct, null
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.versions.db import Base
from models.subject.subject_schema import SubjectSchema, SubjectListSchema
from models.user.user import User
from utils.utils import get_current_user_id


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="subjects")
    questions: Mapped[Set["Question"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    nodes: Mapped[Set["Node"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    exams: Mapped[Set["Exam"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    #
    def __repr__(self):
     return "<Subject(id='%s', name='%s')>" % (self.id, self.name)

    @hybrid_property
    def question_number(self):
        """
        Calcula el número total de preguntas para esta asignatura.
        """
        return sum(len(question_set) for question_set in [self.questions, self.nodes])

    @question_number.expression
    def question_number(cls):
        """
        Expresión SQLAlchemy para calcular el número total de preguntas para esta asignatura.
        """

        from models.question import Question
        return select([func.sum(func.count(Question.id))]).where(
            or_(Question.subject_id == cls.id, Question.node_id == cls.id)).label("question_number")

    @staticmethod
    def insert_subject(
            session,
            name: str,
    ) -> SubjectSchema:
        from models.node.node import Node
        new_subject = Subject(created_by=get_current_user_id(), name=name)

        session.add(new_subject)
        session.commit()
        new_node = Node(
            name=name,
            subject_id=new_subject.id,
            created_by=new_subject.created_by
        )
        session.add(new_node)
        session.commit()

        schema = SubjectSchema().dump(new_subject)
        return schema

    @staticmethod
    def get_subject(
            session,
            id: int,
    ) -> SubjectSchema:
        query = select(Subject).where(Subject.id == id)
        res = session.execute(query).first()

        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        return res[0]

    @staticmethod
    def delete_subject(
            session,
            id: int
    ) -> None:
        from models.question.question import Question
        from models.node.node import Node
        query = select(Subject).where(Subject.id == id)
        res = session.execute(query).first()

        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        query = delete(Question).where(Question.subject_id == id)
        session.execute(query)
        session.commit()

        query = delete(Node).where(Node.subject_id == id)
        session.execute(query)
        session.commit()

        query = delete(Subject).where(Subject.id == id)
        session.execute(query)
        session.commit()

    @staticmethod
    def get_user_subjects(session, limit: int = None, offset: int = 0) -> SubjectListSchema:
        from models.question.question import Question
        current_user_id = get_current_user_id()
        query = session.query(Subject).filter(Subject.created_by == current_user_id).offset(offset)

        # Subconsulta para obtener el número total de preguntas por asignatura
        question_number_subquery = session.query(func.count(Question.id)). \
            filter(Question.subject_id == Subject.id). \
            label("question_number")

        # Unimos la subconsulta para obtener el número total de preguntas por asignatura
        query = query.add_columns(question_number_subquery)

        if limit:
            query = query.limit(limit)

        items = []
        total = 0
        for item, question_number in query:
            item_dict = item.__dict__
            item_dict['question_number'] = question_number or 0  # Si no hay preguntas, establece el valor en 0
            items.append(item_dict)
            total += 1

        schema = SubjectListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def update_subject(
            session,
            name: str,
            id: int
    ) -> SubjectSchema:
        query = select(Subject).where(Subject.id == id)
        res = session.execute(query).first()

        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        res[0].name = name

        session.commit()


        schema = SubjectSchema().dump(res[0])

        return schema

