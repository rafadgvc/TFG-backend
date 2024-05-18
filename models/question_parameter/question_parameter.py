import sqlalchemy
from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, CheckConstraint, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db.versions.db import Base
from models.question import Question
from models.question_parameter.question_parameter_schema import QuestionParameterSchema
from models.user.user import User
from utils.utils import get_current_user_id


class QuestionParameter(Base):

    __tablename__ = "question_parameter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"))
    value: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    group: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="question_parameters")
    question: Mapped["Question"] = relationship(back_populates="question_parameters")


    def __repr__(self):
        return "<Question Parameter(id='%s', value='%s')>" % (self.id, self.value)

    @staticmethod
    def insert_question_parameter(
            session,
            value: str,
            question_id: int,
            group: int,
            position: int,
    ) -> QuestionParameterSchema:
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

        new_question_parameter = QuestionParameter(
            value=value,
            question_id=question_id,
            created_by=user_id,
            position=position,
            group=group
        )
        session.add(new_question_parameter)
        session.commit()
        schema = QuestionParameterSchema().dump(new_question_parameter)
        return schema