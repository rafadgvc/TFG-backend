from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db.versions.db import Base
from models.question.question_schema import QuestionSchema
from models.subject.subject import Subject
from models.user.user import User
from utils import get_current_user_id


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    answer1: Mapped[str] = mapped_column(String, nullable=False)
    answer2: Mapped[str] = mapped_column(String, nullable=False)
    answer3: Mapped[str] = mapped_column(String)
    answer4: Mapped[str] = mapped_column(String)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="questions")
    subject: Mapped["Subject"] = relationship(back_populates="questions")

    def __repr__(self):
     return "<Question(id='%s', title='%s')>" % (self.id, self.title)

    @staticmethod
    def insert_question(
            session,
            title: str,
            subject_id: int,
            answer1: str,
            answer2: str,
            answer3: str = None,
            answer4: str = None
    ) -> QuestionSchema:
        query = select(Subject).where(Subject.id == subject_id)
        subject = session.execute(query).first()

        if not subject:
            abort(400, "La asignatura con el ID no ha sido encontrada.")

        user_id = get_current_user_id()
        if subject.created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        new_question = Question(title=title, subject_id=subject_id, answer1=answer1, answer2=answer2, answer3=answer3,
                                answer4=answer4, created_by=user_id)
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

