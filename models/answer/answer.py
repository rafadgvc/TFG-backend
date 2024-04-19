from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, CheckConstraint, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db.versions.db import Base
from models.answer.answer_schema import AnswerSchema, AnswerListSchema
from models.question import Question
from models.question.question_schema import QuestionSchema, QuestionListSchema
from models.user.user import User
from utils.utils import get_current_user_id


class Answer(Base):
    __tablename__ = "answer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    body: Mapped[str] = mapped_column(String, nullable=False)
    points: Mapped[int] = mapped_column(Integer, CheckConstraint('points >= -1 AND points <= 1'), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"))

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="answers")

    def __repr__(self):
     return "<Answer(id='%s', body='%s')>" % (self.id, self.body)

    @staticmethod
    def insert_answer(
            session,
            body: str,
            question_id: int,
            points: int
    ) -> QuestionSchema:
        user_id = get_current_user_id()
        query = select(Question).where(
            and_(
                Question.id == question_id,
                Question.created_by == user_id
            )
        )
        question = session.execute(query).first()

        if not question:
            abort(400, "La pregunta con el ID proporcionado no ha sido encontrada.")


        new_answer = Answer(body=body, question_id=question_id, created_by=user_id, points=points)
        session.add(new_answer)
        session.commit()
        schema = AnswerSchema().dump(new_answer)
        return schema

    @staticmethod
    def get_answer(
            session,
            id: int
    ) -> AnswerSchema:
        query = select(Answer).where(Answer.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        return res[0]

    @staticmethod
    def delete_answer(
            session,
            id: int
    ) -> None:
        query = select(Answer).where(Answer.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        query = delete(Answer).where(Answer.id == id)
        session.execute(query)
        session.commit()

    @staticmethod
    def get_question_answer(session, question_id: int, limit: int = None, offset: int = 0) -> QuestionListSchema:
        query = select(Answer).where(Answer.question_id == question_id).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Answer).count()

        schema = AnswerListSchema()
        return schema.dump({"items": items, "total": total})

