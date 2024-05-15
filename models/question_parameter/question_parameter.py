from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, CheckConstraint, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set

from db.versions.db import Base
from models.answer.answer_schema import AnswerSchema, AnswerListSchema
from models.question import Question
from models.question.question_schema import QuestionSchema, QuestionListSchema
from models.user.user import User
from utils.utils import get_current_user_id


class QuestionParameter(Base):
    __tablename__ = "question_parameter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"))
    uses: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="question_parameters")
    question: Mapped["Question"] = relationship(back_populates="question_parameters")
    parameters: Mapped[Set["Parameter"]] = relationship(
        back_populates="question_parameter",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
     return "<Question Parameter(id='%s', question='%s')>" % (self.id, self.question_id)