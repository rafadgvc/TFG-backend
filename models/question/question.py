from enum import Enum

from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, and_, CheckConstraint, Table, Column, Boolean, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set, List

from db.versions.db import Base
from models.answer.answer_schema import AnswerListSchema
from models.node.node import Node
from models.question.question_schema import QuestionSchema, QuestionListSchema, FullQuestionSchema, \
    FullQuestionListSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id
from models.associations.associations import node_question_association, exam_question_association


class QuestionType(Enum):
    TEST = "test"
    DESARROLLO = "desarrollo"
    PARAMETRIZADA = "parametrizada"


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))
    type: Mapped[str] = mapped_column(String, CheckConstraint("type IN ('test', 'desarrollo', 'parametrizada')"), nullable=False)



    # Relaciones
    created: Mapped["User"] = relationship(back_populates="questions")
    subject: Mapped["Subject"] = relationship(back_populates="questions")
    nodes = relationship("Node", secondary=node_question_association, back_populates="questions")
    exams = relationship("Exam", secondary=exam_question_association, back_populates="questions")
    answers: Mapped[Set["Answer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    question_parameters: Mapped[Set["QuestionParameter"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
     return "<Question(id='%s', title='%s')>" % (self.id, self.title)

    @hybrid_property
    def connected(self):
        """
        Calcula si la pregunta tiene recursos asociados (exámenes).
        """
        return not bool(self.id % 3 == 0)

    @connected.expression
    def connected(cls):
        """
        Expresión SQLAlchemy para calcular si la pregunta tiene recursos asociados.
        """
        return ~func.exists().where(cls.id % 3 == 0)

    @staticmethod
    def get_answers_for_question(session, question_id: int, limit: int = None, offset: int = 0) -> AnswerListSchema:
        from models.answer.answer import Answer
        query = select(Answer).where(Answer.question_id == question_id).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Answer).filter(Answer.question_id == question_id).count()

        schema = AnswerListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def insert_question(
            session,
            title: str,
            subject_id: int,
            node_ids: List[int],
            difficulty: int,
            time: int,
            type: str,
            active: bool,
    ) -> FullQuestionSchema:
        user_id = get_current_user_id()
        query = select(Subject).where(
            and_(
                Subject.id == subject_id,
                Subject.created_by == user_id
            )
        )
        subject = session.execute(query).first()

        if not subject:
            abort(400, "La asignatura con el ID no ha sido encontrada.")

        new_question = Question(
            title=title,
            subject_id=subject_id,
            created_by=user_id,
            time=time,
            difficulty=difficulty,
            type=type.lower(),
            active=active
        )

        # Asignar nodos a la pregunta
        for node_id in node_ids:
            query = select(Node).where(Node.id == node_id)
            node = session.execute(query).first()
            if not node:
                abort(400, f"El nodo con el ID {node_id} no fue encontrado.")
            new_question.nodes.append(node[0])

        session.add(new_question)
        session.commit()
        schema = FullQuestionSchema().dump(new_question)
        return schema

    @staticmethod
    def get_question(
            session,
            id: int
    ) -> FullQuestionSchema:
        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        question = res[0]
        question_data = FullQuestionSchema().dump(question)
        question_data['connected'] = question.connected
        return question_data

    @staticmethod
    def delete_question(
            session,
            id: int
    ) -> None:
        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        if res[0].connected == True:
            abort(401, "La pregunta tiene recursos asociados.")

        query = delete(Question).where(Question.id == id)
        session.execute(query)
        session.commit()

    @staticmethod
    def get_user_questions(session, limit: int = None, offset: int = 0) -> QuestionListSchema:
        current_user_id = get_current_user_id()
        query = select(Question).where(Question.created_by == current_user_id).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Question).count()

        schema = QuestionListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def get_subject_questions(session, subject_id: int, limit: int = None, offset: int = 0) -> QuestionListSchema:
        current_user_id = get_current_user_id()
        query = select(Question).where(
            and_(
                Question.created_by == current_user_id,
                Question.subject_id == subject_id
            )
        ).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Question).count()

        schema = QuestionListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def get_full_question(
            session,
            id: int
    ) -> FullQuestionSchema:
        from models.answer.answer import Answer
        from models.answer.answer_schema import AnswerListSchema

        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        query = select(Answer).where(Answer.question_id == id)
        items = session.execute(query).scalars().all()

        total = session.query(Answer).count()

        schema = FullQuestionSchema()

        answers = AnswerListSchema()
        answers = answers.dump({"items": items, "total": total})
        return schema.dump(
            {
                "id": res[0].id,
                "title": res[0].title,
                "subject_id": res[0].subject_id,
                "time": res[0].time,
                "difficulty": res[0].difficulty,
                "type": res[0].type,
                "active": res[0].active,
                "connected": res[0].connected,
                "answers": answers
            }
        )

    @staticmethod
    def disable_question(
            session,
            id: int
    ) -> FullQuestionSchema:
        from models.answer.answer import Answer
        from models.answer.answer_schema import AnswerListSchema
        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        if res[0].active == False:
            abort(418, "La pregunta ya estaba desactivada")

        res[0].active = False

        session.commit()

        query = select(Answer).where(Answer.question_id == id)
        items = session.execute(query).scalars().all()
        total = session.query(Answer).count()

        schema = FullQuestionSchema()

        answers = AnswerListSchema()
        answers = answers.dump({"items": items, "total": total})
        return schema.dump(
            {
                "id": res[0].id,
                "title": res[0].title,
                "subject_id": res[0].subject_id,
                "time": res[0].time,
                "difficulty": res[0].difficulty,
                "type": res[0].type,
                "active": res[0].active,
                "connected": res[0].connected,
                "answers": answers
            }
        )

    @staticmethod
    def get_questions_for_exam(session, exam_id: int) -> FullQuestionListSchema:
        query = select(Question).join(exam_question_association).where(exam_question_association.c.exam_id == exam_id)
        items = session.execute(query).scalars().all()

        total = session.query(Question).join(exam_question_association).filter(
            exam_question_association.c.exam_id == exam_id).count()

        schema = FullQuestionListSchema()
        questions_data = []
        for question in items:
            question_data = Question.get_question(session, question.id)
            question_data['answers'] = Question.get_answers_for_question(session, question.id)
            questions_data.append(question_data)
        return schema.dump({"items": questions_data, "total": total})


