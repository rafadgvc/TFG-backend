from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, CheckConstraint, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db.versions.db import Base
from models.question import Question
from models.user.user import User


class QuestionParameter(Base):

    __tablename__ = "question_parameter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    question_parameter_id: Mapped[int] = mapped_column(Integer, ForeignKey("question_parameter.id"))
    value: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    group: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="question_parameters")
    question: Mapped["Question"] = relationship(back_populates="question_parameters")


    def __repr__(self):
     return "<Question Parameter(id='%s', value='%s')>" % (self.id, self.value)