import random

from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from flask import abort
from sqlalchemy import Integer, String, ForeignKey, delete, and_, func, select, distinct, not_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set, List

from db.versions.db import Base
from models.exam.exam_schema import FullExamSchema, ExamListSchema
from models.question.question_schema import QuestionListSchema
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
            questions
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
        # Asignar preguntas al examen
        for question in questions:
            query = select(Question).where(Question.id == question['id'])
            res = session.execute(query).first()
            if not res:
                abort(400, f"La pregunta con el ID {question['id']} no fue encontrada.")

            # Añadir a la asociación con la sección correspondiente
            association = exam_question_association.insert().values(
                exam_id=new_exam.id,
                question_id=question['id'],
                section_id=question['section_number']
            )
            session.execute(association)
            session.commit()

        for question in new_exam.questions:
            question_data = Question.get_full_question(session, question.id)
            if question_data:
                question_data['answers'] = Question.get_answers_for_question(session, question.id)
                exam_data['questions']['items'].append(question_data)
                exam_data['questions']['total'] += 1
        return exam_data

    @staticmethod
    def get_exam(session, id: int) -> FullExamSchema:
        from models.question.question import Question
        from models.associations.associations import exam_question_association  # Importa la asociación

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
                # Obtener el número de sección para esta pregunta
                section_query = select(exam_question_association.c.section_id).where(
                    and_(
                        exam_question_association.c.exam_id == exam.id,
                        exam_question_association.c.question_id == question.id
                    )
                )
                section_result = session.execute(section_query).first()
                if section_result:
                    question_data['section_number'] = section_result[0]

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
    def edit_exam(
            session,
            exam_id: int,
            title: str,
            questions
    ) -> FullExamSchema:
        from models.question.question import Question
        user_id = get_current_user_id()
        query = select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.created_by == user_id
            )
        )
        exam = session.execute(query).scalar_one_or_none()

        if not exam:
            abort(400, "El examen con el ID no ha sido encontrada.")

        exam.title = title
        query = delete(exam_question_association).where(exam_question_association.c.exam_id == exam_id)
        session.execute(query)
        session.commit()

        exam_data = {
            "id": exam.id,
            "title": exam.title,
            "subject_id": exam.subject_id,
            "questions": {
                "items": [],
                "total": 0
            }
        }
        # Asignar preguntas al examen
        for question in questions:
            query = select(Question).where(Question.id == question['id'])
            res = session.execute(query).first()
            if not res:
                abort(400, f"La pregunta con el ID {question['id']} no fue encontrada.")

            # Añadir a la asociación con la sección correspondiente
            association = exam_question_association.insert().values(
                exam_id=exam.id,
                question_id=question['id'],
                section_id=question['section_number']
            )
            session.execute(association)
        session.commit()

        for question in exam.questions:
            question_data = Question.get_full_question(session, question.id)
            if question_data:
                question_data['answers'] = Question.get_answers_for_question(session, question.id)
                exam_data['questions']['items'].append(question_data)
                exam_data['questions']['total'] += 1
        return exam_data


    @staticmethod
    def get_questions_to_select(
            session,
            node_ids: list[int],
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
                node_question_association.c.node_id.in_(node_ids)
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
    def delete_exam(session, exam_id: int):
        from models.associations.associations import exam_question_association
        query = select(Exam).where(Exam.id == exam_id)
        res = session.execute(query).first()
        if not res:
            abort(400, "El examen no ha sido encontrado.")
        exam_data = Exam.get_exam(session, exam_id)
        if exam_data['connected'] == True:
            abort(401, "El examen tiene resultados asociados.")


        query = delete(exam_question_association).where(exam_question_association.c.exam_id == exam_id)
        session.execute(query)
        session.commit()

        query = delete(Exam).where(Exam.id == exam_id)
        session.execute(query)
        session.commit()


    @staticmethod
    def export_exam_to_aiken(session, exam_id: int, output_file: str):
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
        from models.subject.subject import Subject
        exam_data = Exam.get_exam(session, exam_id)

        if not exam_data:
            raise ValueError("El examen no existe.")

        subject_data = Subject.get_subject(session, exam_data['subject_id'])

        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()

        # Encabezado
        exam_title = exam_data['title']
        header = Paragraph(exam_title, styles['Title'])
        subheader = Paragraph(subject_data.name, ParagraphStyle(
            name='Subheader',
            parent=styles['Heading2'],
            alignment=1
            )
        )

        # Contenido
        content = [header, Spacer(1, 0), subheader, Spacer(1, 30)]
        questions = exam_data['questions']['items']
        question_number = 0
        current_section = None
        for question in questions:
            question_number += 1

            section = question['section_number']
            if section != current_section:
                current_section = section
                section_title = f"Sección {current_section}"
                content.append(Paragraph(section_title, styles['Heading2']))
                content.append(Spacer(1, 10))

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
                answer_letter = 'A'

                for answer in answers:

                    if raw_parameters != parameters:
                        answer_body = replace_parameters(answer['body'], parameters)
                    else:
                        answer_body = answer['body']
                    answer_body = answer_letter + '. ' + answer_body
                    content.append(Paragraph(answer_body, styles['Normal']))
                    answer_letter = chr(ord(answer_letter) + 1)
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

    @staticmethod
    def export_exam_to_moodlexml(session, exam_id: int, output_file: str):
        from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
        user_id = get_current_user_id()
        exam = session.query(Exam).filter(and_(Exam.id == exam_id, Exam.created_by == user_id)).one_or_none()

        if not exam:
            raise ValueError("El examen no existe.")

        exam_data = Exam.get_exam(session, exam_id)
        questions = exam_data['questions']['items']

        quiz = Element('quiz')

        for question in questions:
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
            if question['type'] == 'test':
                question_element = SubElement(quiz, 'question', type='multichoice')
            else:
                question_element = SubElement(quiz, 'question', type='essay')
            name = SubElement(question_element, 'name')
            text = SubElement(name, 'text')
            text.text = question_title

            question_text = SubElement(question_element, 'questiontext', format='html')
            text = SubElement(question_text, 'text')
            text.text = question['title']

            if 'answers' in question and question['type'] == 'test':
                for answer in question['answers']['items']:
                    if raw_parameters != parameters:
                        answer_body = replace_parameters(answer['body'], parameters)
                    else:
                        answer_body = answer['body']
                    answer_element = SubElement(question_element, 'answer', fraction=str(int(answer['points'] * 100)))
                    text = SubElement(answer_element, 'text')
                    text.text = answer_body
            else:
                answer_element = SubElement(question_element, 'answer', fraction='0')
                text = SubElement(answer_element, 'text')
                text.text = ''

        tree = ElementTree(quiz)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
