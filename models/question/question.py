from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set

from db.versions.db import Base
from models.question.question_schema import QuestionSchema, QuestionListSchema, FullQuestionSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="questions")
    subject: Mapped["Subject"] = relationship(back_populates="questions")
    answers: Mapped[Set["Answer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
     return "<Question(id='%s', title='%s')>" % (self.id, self.title)

    @staticmethod
    def insert_question(
            session,
            title: str,
            subject_id: int,
    ) -> QuestionSchema:
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

        new_question = Question(title=title, subject_id=subject_id, created_by=user_id)
        session.add(new_question)
        session.commit()
        schema = QuestionSchema().dump(new_question)
        return schema

    @staticmethod
    def get_question(
            session,
            id: int
    ) -> QuestionSchema:
        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        return res[0]

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

        current_user_id = get_current_user_id()
        query = select(Answer).where(Answer.question_id == id)
        items = session.execute(query).scalars().all()

        total = session.query(Answer).count()

        schema = FullQuestionSchema()

        answers = AnswerListSchema()
        answers = answers.dump({"items": items, "total": total})
        return schema.dump({"id": res[0].id, "title": res[0].title, "subject_id": res[0].subject_id, "answers": answers})

