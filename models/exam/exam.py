from flask import abort
from sqlalchemy import Integer, String, ForeignKey, delete, and_, CheckConstraint, Table, Column, Boolean, func, select, \
    or_, distinct
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set, List

from db.versions.db import Base
from models.exam.exam_schema import FullExamSchema, ExamListSchema
from models.node.node import Node
from models.question.question_schema import QuestionSchema, QuestionListSchema, FullQuestionSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id
from models.associations.associations import exam_question_association


class Exam(Base):
    __tablename__ = "exam"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))



    # Relaciones
    created: Mapped["User"] = relationship(back_populates="exams")
    subject: Mapped["Subject"] = relationship(back_populates="exams")
    questions = relationship("Question", secondary=exam_question_association, back_populates="exams")

    def __repr__(self):
        return "<Exam(id='%s', title='%s')>" % (self.id, self.title)

    @hybrid_property
    def connected(self):
        """
        Calcula si la pregunta tiene resultados asociados.
        """

        # TODO: Cambiar a comprobación real
        return not bool(self.id % 3 == 0)

    @connected.expression
    def connected(cls):
        """
        Expresión SQLAlchemy para calcular si el examen tiene resultados asociados.
        """
        # TODO: Cambiar a comprobación real
        return ~func.exists().where(cls.id % 3 == 0)

    @hybrid_property
    def difficulty(self):
        """
        Calcula el nivel medio de dificultad de las preguntas en el examen.
        """
        total_difficulty = sum(question.difficulty for question in self.questions)
        return total_difficulty / len(self.questions) if self.questions else 0

    @difficulty.expression
    def difficulty(cls):
        """
        Expresión SQLAlchemy para calcular el nivel medio de dificultad de las preguntas en el examen.
        """
        from models.question.question import Question
        return (
            select([func.avg(exam_question_association.c.difficulty)])
            .where(exam_question_association.c.exam_id == cls.id)
            .scalar_subquery()
        )

    @hybrid_property
    def time(self):
        """
        Calcula la suma de los tiempos estimados de todas las preguntas en el examen.
        """
        return sum(question.time for question in self.questions)

    @time.expression
    def time(cls):
        """
        Expresión SQLAlchemy para calcular la suma de los tiempos estimados de todas las preguntas en el examen.
        """
        from models.question.question import Question
        return (
            select([func.sum(Question.time)])
            .where(Exam.id == cls.id)
            .select_from(Exam)
            .join(exam_question_association)
            .join(Question)
            .scalar_subquery()
        )

    @hybrid_property
    def question_number(self):
        """
        Calcula el número total de preguntas del examen.
        """
        return len(self.questions)

    @question_number.expression
    def question_number(cls):
        """
        Expresión SQLAlchemy para calcular el número total de preguntas del examen.
        """

        from models.question.question import Question
        return (
            select([func.count(distinct(Question.id))])
            .where(Exam.id == cls.id)
            .select_from(Exam)
            .join(exam_question_association)
            .join(Question)
            .scalar_subquery().label('question_number')
        )

    @staticmethod
    def insert_exam(
            session,
            title: str,
            subject_id: int,
            question_ids: List[int],
    ) -> FullExamSchema:
        from models.question import Question
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

        new_exam = Exam(
            title=title,
            subject_id=subject_id,
            created_by=user_id
        )


        # Asignar preguntas al examen
        for question_id in question_ids:

            # TODO: Actualizar usos de preguntas
            query = select(Question).where(Question.id == question_id)
            question = session.execute(query).first()
            if not question:
                abort(400, f"El pregunta con el ID {question_id} no fue encontrada.")
            new_exam.questions.append(question[0])

        session.add(new_exam)
        session.commit()
        exam_data = {
            "id": new_exam.id,
            "title": new_exam.title,
            "subject_id": new_exam.subject_id,
            "questions": {
                "items": [],
                "total": 0
            }
        }
        for question in new_exam.questions:
            question_data = Question.get_full_question(session, question.id)
            if question_data:
                question_data['answers'] = Question.get_answers_for_question(session, question.id)
                exam_data['questions']['items'].append(question_data)
                exam_data['questions']['total'] += 1
        return exam_data
        return schema

    @staticmethod
    def get_exam(session, id: int) -> FullExamSchema:
        from models.question.question import Question
        query = select(Exam).where(Exam.id == id)
        res = session.execute(query).first()

        if not res:
            # Manejar el caso donde el examen no existe
            return None

        exam = res[0]
        exam_data = {
            "id": exam.id,
            "connected": exam.connected,
            "title": exam.title,
            "subject_id": exam.subject_id,
            "difficulty": exam.difficulty,
            "time": exam.time,
            "questions": {
                "items": [],
                "total": 0
            }
        }
        for question in exam.questions:
            question_data = Question.get_full_question(session, question.id)
            if question_data:
                question_data['answers'] = Question.get_answers_for_question(session, question.id)
                exam_data['questions']['items'].append(question_data)
                exam_data['questions']['total'] += 1
        return exam_data

    @staticmethod
    def get_subject_exams(session, subject_id: int, limit: int = None, offset: int = 0) -> ExamListSchema:
        from models.question import Question
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

        query = (session.query(
            Exam.id,
            Exam.title,
            func.avg(Question.difficulty).label('difficulty'),
            func.sum(Question.time).label('time'),
            func.count(distinct(Question.id)).label('question_number')
        )
                 .join(exam_question_association, Exam.id == exam_question_association.c.exam_id)
                 .join(Question, Question.id == exam_question_association.c.question_id)
                 .filter(Exam.subject_id == subject_id)
                 .group_by(Exam.id, Exam.title)
                 .offset(offset)
                 )

        if limit:
            query = query.limit(limit)

        res = session.execute(query)

        items = []
        total = 0
        for item in query:
            items.append(item._mapping)
            total += 1

        schema = ExamListSchema()
        return schema.dump({"items": items, "total": total})



