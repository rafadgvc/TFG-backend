from typing import Set
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.versions.db import Base
from models.question.question_schema import QuestionSchema


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    answer1: Mapped[str] = mapped_column(String, nullable=False)
    answer2: Mapped[str] = mapped_column(String, nullable=False)
    answer3: Mapped[str] = mapped_column(String)
    answer4: Mapped[str] = mapped_column(String)

    def __repr__(self):
     return "<Question(id='%s', title='%s')>" % (self.id, self.title)

    @staticmethod
    def insert_question(
            session,
            title: str,
            answer1: str,
            answer2: str,
            answer3: str = None,
            answer4: str = None
    ) -> QuestionSchema:
        new_question = Question(title=title, answer1=answer1, answer2=answer2, answer3=answer3, answer4=answer4)
        session.add(new_question)
        session.commit()
        schema = QuestionSchema().dump(new_question)
        return schema
