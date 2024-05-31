import random

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from flask import abort
from sqlalchemy import Integer, String, ForeignKey, delete, and_, CheckConstraint, Table, Column, Boolean, func, select, \
    or_, distinct, not_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set, List

from db.versions.db import Base
from models.exam.exam_schema import FullExamSchema, ExamListSchema
from models.node.node import Node
from models.question.question_schema import QuestionSchema, QuestionListSchema, FullQuestionSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id, replace_parameters
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
    results: Mapped[Set["Result"]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        return "<Exam(id='%s', title='%s')>" % (self.id, self.title)

    @hybrid_property
    def connected(self):
        """
        Calcula si el examen tiene resultados asociados.
        """
        return len(self.results) > 0

    @connected.expression
    def connected(cls):
        """
        Expresión SQLAlchemy para calcular si el examen tiene resultados asociados.
        """
        from models.result.result import Result
        return select([func.count(Result.id)]).where(Result.exam_id == cls.id).label("connected") > 0

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
        from models.question.question import Question
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
            query = select(Question).where(Question.id == question_id)
            question = session.execute(query).first()
            if not question:
                abort(400, f"La pregunta con el ID {question_id} no fue encontrada.")
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

    @staticmethod
    def get_questions_to_select(
            session,
            node_id: int,
            question_number: int = None,
            type: list[str] = None,
            time: int = None,
            difficulty: int = None,
            repeat: bool = None,
            exclude_ids: list[int] = None,
            limit: int = None,
            offset: int = 0
    ) -> QuestionListSchema:
        from models.question.question import Question
        from models.associations.associations import node_question_association
        current_user_id = get_current_user_id()

        query = select(Question).join(node_question_association).where(
            and_(
                Question.created_by == current_user_id,
                node_question_association.c.node_id == node_id
            )
        ).offset(offset)

        if exclude_ids:
            query = query.where(not_(Question.id.in_(exclude_ids)))

        if limit:
            query = query.limit(limit)

        questions = session.execute(query).scalars().all()

        def get_sort_key(question):
            uses = getattr(question, 'uses', 0) if repeat else None
            type_match = 0 if type and question.type in type else 1
            time_diff = abs(question.time - time) if time is not None else 0
            difficulty_diff = abs(question.difficulty - difficulty) if difficulty is not None else 0
            random_value = random.random()
            return (
                uses if uses is not None else float('inf'),
                type_match,
                time_diff,
                difficulty_diff,
                question.uses if hasattr(question, 'uses') else float('inf'),
                random_value
            )

        questions.sort(key=get_sort_key)

        if question_number is not None:
            questions = questions[:question_number]

        total = session.query(Question).count()
        schema = QuestionListSchema()
        return schema.dump({"items": questions, "total": total})

    @staticmethod
    def export_exam_to_aiken(session, exam_id: int, output_file: str):
        from models.answer.answer import Answer
        user_id = get_current_user_id()
        # Obtener el examen por ID
        exam = session.query(Exam).filter(and_(Exam.id == exam_id, Exam.created_by == user_id)).one_or_none()

        if not exam:
            raise ValueError("El examen no existe.")

        exam_data = Exam.get_exam(session, exam_id)
        questions = exam_data['questions']['items']
        question_number = 0


        with open(output_file, 'w', encoding='utf-8') as file:
            for question in questions:
                question_number += 1
                raw_parameters = [{
                    'value': param['value'], 'group': param['group']
                } for param in question.get('question_parameters', {}).get('items', [])]
                parameters = []
                if raw_parameters != parameters:
                    random_group = random.choice(raw_parameters)
                    for param in raw_parameters:
                        if param['group'] == random_group['group']:
                            parameters.append(param['value'])
                    question_title = replace_parameters(question['title'], parameters)
                else:
                    question_title = question['title']

                file.write(f"{question_title}\n")
                answer_letter = 'A'
                correct_answer_letter = None

                if 'answers' in question and question['type'] == 'test':
                    answers = question['answers']['items']
                    for answer in answers:
                        if raw_parameters != parameters:
                            answer_body = replace_parameters(answer['body'], parameters)
                        else:
                            answer_body = answer['body']
                        file.write(f"{answer_letter}. {answer_body}\n")
                        if answer['points'] == 1:
                            correct_answer_letter = answer_letter
                        answer_letter = chr(ord(answer_letter) + 1)

                    if not correct_answer_letter:
                        raise ValueError(f"La pregunta con ID {question.id} no tiene una respuesta correcta definida.")

                    file.write(f"ANSWER: {correct_answer_letter}\n\n")

    @staticmethod
    def export_exam_to_pdf(session, exam_id, output_file):
        exam_data = Exam.get_exam(session, exam_id)

        if not exam_data:
            raise ValueError("El examen no existe.")

        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()

        # Encabezado
        exam_title = exam_data['title']
        header = Paragraph(exam_title, styles['Title'])

        # Contenido
        content = [header, Spacer(1, 40)]
        questions = exam_data['questions']['items']
        question_number = 0
        for question in questions:
            question_number += 1
            raw_parameters = [{
                'value': param['value'], 'group': param['group']
            } for param in question.get('question_parameters', {}).get('items', [])]
            parameters = []
            if raw_parameters != parameters:
                random_group = random.choice(raw_parameters)
                for param in raw_parameters:
                    if param['group'] == random_group['group']:
                        parameters.append(param['value'])
                question_title = replace_parameters(question['title'], parameters)
            else:
                question_title = question['title']
            question_text = f"<b>{question_number}. {question_title}</b><br/>"
            content.append(Paragraph(question_text, styles['Normal']))
            if 'answers' in question and question['type'] == 'test':
                answers = question['answers']['items']
                for answer in answers:
                    if raw_parameters != parameters:
                        answer_body = replace_parameters(answer['body'], parameters)
                    else:
                        answer_body = answer['body']
                    content.append(Paragraph(answer_body, styles['Normal']))
            content.append(Spacer(1, 12))
            content.append(Spacer(1, 12))

        doc.build(content)

    @staticmethod
    def export_exam_to_gift(session, exam_id: int, output_file: str):
        from models.answer.answer import Answer
        user_id = get_current_user_id()
        # Obtener el examen por ID
        exam = session.query(Exam).filter(and_(Exam.id == exam_id, Exam.created_by == user_id)).one_or_none()

        if not exam:
            raise ValueError("El examen no existe.")

        exam_data = Exam.get_exam(session, exam_id)

        questions = exam_data['questions']['items']
        question_number = 0

        with open(output_file, 'w', encoding='utf-8') as file:
            for question in questions:
                question_number += 1
                raw_parameters = [{
                    'value': param['value'], 'group': param['group']
                } for param in question.get('question_parameters', {}).get('items', [])]
                parameters = []
                if raw_parameters != parameters:
                    random_group = random.choice(raw_parameters)
                    for param in raw_parameters:
                        if param['group'] == random_group['group']:
                            parameters.append(param['value'])
                    question_title = replace_parameters(question['title'], parameters)
                else:
                    question_title = question['title']
                # Escribimos la pregunta
                file.write(f"::Question {question['id']}::{question_title} {{\n")

                # Obtener las respuestas
                if 'answers' in question and question['type'] == 'test':
                    answers = question['answers']['items']
                    for answer in answers:
                        if raw_parameters != parameters:
                            answer_body = replace_parameters(answer['body'], parameters)
                        else:
                            answer_body = answer['body']
                        file.write(f"~%{answer['points']*100}%{answer_body}\n")

                file.write("}\n\n")
