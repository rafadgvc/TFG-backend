from typing import Set

from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.versions.db import Base
from models.question.question_schema import QuestionSchema
from models.subject.subject import Subject


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    answer1: Mapped[str] = mapped_column(String, nullable=False)
    answer2: Mapped[str] = mapped_column(String, nullable=False)
    answer3: Mapped[str] = mapped_column(String)
    answer4: Mapped[str] = mapped_column(String)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))
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

        new_question = Question(title=title, subject_id=subject_id, answer1=answer1, answer2=answer2, answer3=answer3,
                                answer4=answer4)
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
        return res[0]

    @staticmethod
    def delete_question(
            session,
            id: int
    ) -> None:
        query = delete(Question).where(Question.id == id)
        session.execute(query)
        session.commit()

