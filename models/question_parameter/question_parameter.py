import random

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

    @staticmethod
    def get_random_parameter_set(session, question_id: int) -> dict:
        query = select(QuestionParameter).where(QuestionParameter.question_id == question_id)
        parameters = session.execute(query).scalars().all()

        if not parameters:
            return {}

        groups = {}
        for param in parameters:
            if param.group not in groups:
                groups[param.group] = []
            groups[param.group].append(param)

        if not groups:
            return {}

        selected_group = random.choice(list(groups.values()))
        parameter_set = {f"##param{param.position}##": param.value for param in selected_group}
        return parameter_set

    @staticmethod
    def apply_parameters_to_question(question_text: str, answers: list, parameter_set: dict) -> (str, list):
        for placeholder, value in parameter_set.items():
            question_text = question_text.replace(placeholder, value)
            answers = [answer.replace(placeholder, value) for answer in answers]
        return question_text, answers


# Método para obtener y aplicar parámetros a una pregunta específica
def get_parametrized_question(session, question_id: int):
    question_query = select(Question).where(Question.id == question_id)
    question = session.execute(question_query).first()

    if not question:
        abort(400, "La pregunta con el ID proporcionado no ha sido encontrada.")

    question_text = question.text
    answers = [question.option_a, question.option_b, question.option_c, question.option_d]
    parameter_set = QuestionParameter.get_random_parameter_set(session, question_id)

    if parameter_set:
        question_text, answers = QuestionParameter.apply_parameters_to_question(question_text, answers, parameter_set)

    return {
        "question": question_text,
        "answers": answers,
        "correct_answer": question.correct_answer
    }