from flask import abort
from sqlalchemy import Integer, ForeignKey, JSON, select, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set

from db.versions.db import Base
from models.question import Question
from models.question_parameter.question_parameter import QuestionParameter
from models.user.user import User
from utils.utils import get_current_user_id


class Parameter(Base):
    __tablename__ = "parameter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    question_parameter_id: Mapped[int] = mapped_column(Integer, ForeignKey("question_parameter.id"))
    value: Mapped[str] = mapped_column(String, nullable=False)

    # Relaciones
    question_parameter: Mapped["QuestionParameter"] = relationship(back_populates="parameters")
    created: Mapped["User"] = relationship(back_populates="parameters")
