import random
from datetime import datetime, timedelta
from odf.opendocument import OpenDocumentText
from odf.text import H, P, Span
from odf.style import Style, TextProperties, ParagraphProperties

from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree

from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from flask import abort
from sqlalchemy import Integer, String, ForeignKey, delete, and_, func, select, distinct, not_, DateTime, true
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column, joinedload, subqueryload
from typing import Set, List

from db.versions.db import Base
from models.exam.exam_schema import FullExamSchema, ExamListSchema
from models.question.question_schema import QuestionListSchema, QuestionSchema, QuestionExtendedListSchema
from models.question_parameter.question_parameter_schema import QuestionParameterListSchema
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
    created_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)

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
        Calculates if the exam has associated results.
        """
        return len(self.results) > 0

    @connected.expression
    def connected(cls):
        """
        SQLAlchemy expression to calculate if the exam has associated results.
        """
        from models.result.result import Result
        return select([func.count(Result.id)]).where(Result.exam_id == cls.id).label("connected") > 0

    @hybrid_property
    def difficulty(self):
        """
        Calculates the average estimated difficulty of the exam's questions.
        """
        total_difficulty = sum(question.difficulty for question in self.questions)
        return total_difficulty / len(self.questions) if self.questions else 0

    @difficulty.expression
    def difficulty(cls):
        """
        SQLAlchemy to calculate the average estimated difficulty of the exam's questions.
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
        Calculates the total estimated time of the exam's questions.
        """
        return sum(question.time for question in self.questions)

    @time.expression
    def time(cls):
        """
        SQLAlchemy expression to calculate the total estimated time of the exam's questions.
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
        Calculates the number of questions in the exam.
        """
        return len(self.questions)

    @question_number.expression
    def question_number(cls):
        """
        SQLAlchemy expression to calculate the number of questions in the exam.
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
            questions
    ) -> FullExamSchema:
        from models.question.question import Question

        # The subject is checked to belong to the current user
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

        # The exam is created and added to the database
        new_exam = Exam(
            title=title,
            subject_id=subject_id,
            created_by=user_id,
            created_on=datetime.now()
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
        # The questions are associated to the exam with their belonging section
        for question in questions:
            query = select(Question).where(Question.id == question['id'])
            res = session.execute(query).first()
            if not res:
                abort(400, f"La pregunta con el ID {question['id']} no fue encontrada.")

            # If the question is parametrized and a group has been specified, it is added as well
            group = question['group'] if question.get('group') is not None else None

            association = exam_question_association.insert().values(
                exam_id=new_exam.id,
                question_id=question['id'],
                section_id=question['section_number'],
                group=group
            )
            session.execute(association)
            session.commit()

        # The questions are added to the exam data
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
        from models.associations.associations import exam_question_association

        # The exam is checked to belong to the current user
        query = select(Exam).where(
            and_(
                Exam.id == id,
                Exam.created_by == get_current_user_id(),
            )
        )
        res = session.execute(query).first()

        if not res:
            abort(400, "El examen con el ID no ha sido encontrado.")


        exam = res[0]
        exam_data = {
            "id": exam.id,
            "connected": exam.connected,
            "title": exam.title,
            "subject_id": exam.subject_id,
            "difficulty": exam.difficulty,
            "time": exam.time,
            "year": exam.created_on.year,
            "month": exam.created_on.month,
            "questions": {
                "items": [],
                "total": 0
            }
        }

        # The questions are added to the returned data
        for question in exam.questions:
            question_data = Question.get_full_question(session, question.id)
            if question_data:
                # Get the section number for each question
                section_query = select(exam_question_association.c.section_id).where(
                    and_(
                        exam_question_association.c.exam_id == exam.id,
                        exam_question_association.c.question_id == question.id
                    )
                )
                section_result = session.execute(section_query).first()
                if section_result:
                    question_data['section_number'] = section_result[0]

                # If the question is parametrized get the selected group as well (if any)
                group_query = select(exam_question_association.c.group).where(
                    and_(
                        exam_question_association.c.exam_id == exam.id,
                        exam_question_association.c.question_id == question.id
                    )
                )
                group_result = session.execute(group_query).first()
                if group_result:
                    question_data['group'] = group_result[0]

                question_data['answers'] = Question.get_answers_for_question(session, question.id)
                exam_data['questions']['items'].append(question_data)
                exam_data['questions']['total'] += 1

        # Order the exam's questions by their section number
        exam_data['questions']['items'].sort(key=lambda x: x['section_number'])

        return exam_data

    @staticmethod
    def get_subject_exams(session, subject_id: int, limit: int = None, offset: int = 0) -> ExamListSchema:
        from models.question import Question
        # The subject is checked to belong to the current user
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

        # Each exam is mapped as an ExamSchema
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
        # The exam is checked to belong to the current user
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

        # The exam's title is changed
        exam.title = title

        # To be more general, all the old Exam-Question relations are deleted to add the new ones
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
        for question in questions:
            query = select(Question).where(Question.id == question['id'])
            res = session.execute(query).first()
            if not res:
                abort(400, f"La pregunta con el ID {question['id']} no fue encontrada.")

            group = question['group'] if question.get('group') is not None else None

            association = exam_question_association.insert().values(
                exam_id=exam.id,
                question_id=question['id'],
                section_id=question['section_number'],
                group=group
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
            parametrized: bool = None,
            exclude_ids: list[int] = None,
            limit: int = None,
            offset: int = 0
    ) -> QuestionExtendedListSchema:
        from models.question.question import Question
        from models.associations.associations import node_question_association
        from models.question_parameter.question_parameter import QuestionParameter

        # The exam is checked to belong to the current user
        current_user_id = get_current_user_id()

        # All the active questions that have, at least, one association with a given node ID
        query = select(Question).join(node_question_association).where(
            and_(
                Question.created_by == current_user_id,
                Question.active == true(),
                node_question_association.c.node_id.in_(node_ids)
            )
        ).offset(offset)

        # If there are any questions that should not be returned, they are excluded from the query
        if exclude_ids:
            query = query.where(not_(Question.id.in_(exclude_ids)))

        if limit:
            query = query.limit(limit)

        questions = session.execute(query).scalars().all()

        # A key is created for each question to establish an ordering criteria
        def get_sort_key(question):
            parametrized_priority = getattr(question, 'parametrized', False) if parametrized else None
            parametrized_value = 0 if parametrized_priority else 1
            type_match = 0 if type and question.type in type else 1
            time_diff = abs(question.time - time) if time is not None else 0
            difficulty_diff = abs(question.difficulty - difficulty) if difficulty is not None else 0
            uses = getattr(question, 'uses', 0)
            random_value = random.random()
            return (

                parametrized_value,
                type_match,
                time_diff,
                difficulty_diff,
                uses if uses is not None else float('inf'),
                random_value
            )

        # The questions are sorted using the sorting key
        questions.sort(key=get_sort_key)

        if question_number is not None:
            questions = questions[:question_number]

        total = session.query(Question).count()

        schema = QuestionSchema()
        data = []
        for question in questions:
            question_dict = schema.dump(
            {
                "id": question.id,
                "title": question.title,
                "subject_id": question.subject_id,
                "time": question.time,
                "difficulty": question.difficulty,
                "type": question.type,
                "active": question.active,
                "connected": question.connected,
                "parametrized": question.parametrized
            }
        )
            if question.parametrized:
                # If the question has parameters, they are included in the returning data
                parameters = session.query(QuestionParameter).filter_by(question_id=question.id).all()
                parameter_schema = QuestionParameterListSchema()
                parameters_data = parameter_schema.dump({"items": parameters})
                question_dict['question_parameters'] = parameters_data
            data.append(question_dict)

        return {"items": data, "total": total}

    @staticmethod
    def delete_exam(session, exam_id: int):
        from models.associations.associations import exam_question_association

        # The exam is checked to belong to the current user
        query = select(Exam).where(Exam.id == exam_id)
        res = session.execute(query).first()
        if not res:
            abort(400, "El examen no ha sido encontrado.")
        exam_data = Exam.get_exam(session, exam_id)

        # The exam is checked to not have associated results
        if exam_data['connected'] == True:
            abort(401, "El examen tiene resultados asociados.")

        # The Exam-Question associations are deleted
        query = delete(exam_question_association).where(exam_question_association.c.exam_id == exam_id)
        session.execute(query)
        session.commit()

        # The exam is deleted
        query = delete(Exam).where(Exam.id == exam_id)
        session.execute(query)
        session.commit()


    @staticmethod
    def export_exam_to_aiken(session, exam_id: int, output_file: str):

        # The exam is checked to belong to the current user
        user_id = get_current_user_id()
        exam = session.query(Exam).filter(and_(Exam.id == exam_id, Exam.created_by == user_id)).one_or_none()

        if not exam:
            abort(400, "El examen no ha sido encontrado.")

        exam_data = Exam.get_exam(session, exam_id)
        questions = exam_data['questions']['items']
        question_number = 0

        # The new file is opened
        with open(output_file, 'w', encoding='utf-8') as file:
            for question in questions:
                # Only the test questions are taken into consideration
                if question['type'] == 'test':
                    question_number += 1

                    # The questions parameters (if any) are obtained
                    raw_parameters = [{
                        'value': param['value'], 'group': param['group']
                    } for param in question.get('question_parameters', {}).get('items', [])]
                    parameters = []

                    # If there are parameters, the previously specified group is selected
                    if raw_parameters != parameters:
                        if question['group'] is not None:
                            random_group = question['group']
                        else:

                            # If no group was specified, a random group is selected
                            random_param = random.choice(raw_parameters)
                            random_group = random_param['group']
                        for param in raw_parameters:
                            if param['group'] == random_group:
                                parameters.append(param['value'])

                        # The question title is replaced with the parameters' values if needed
                        question_title = replace_parameters(question['title'], parameters)
                    else:
                        question_title = question['title']

                    file.write(f"{question_title}\n")
                    answer_letter = 'A'
                    correct_answer_letter = None

                    # Since the answers must have a question with 100% points, while the answers are written
                    # the correct one is searched
                    if 'answers' in question and question['type'] == 'test':
                        answers = question['answers']['items']
                        for answer in answers:
                            if raw_parameters != parameters:
                                # The answer content is replaced with the parameters' values if needed
                                answer_body = replace_parameters(answer['body'], parameters)
                            else:
                                answer_body = answer['body']
                            file.write(f"{answer_letter}. {answer_body}\n")
                            if answer['points'] == 100:
                                correct_answer_letter = answer_letter
                            answer_letter = chr(ord(answer_letter) + 1)

                        if not correct_answer_letter:
                            raise ValueError(f"La pregunta con ID {question.id} no tiene una respuesta correcta definida.")

                        file.write(f"ANSWER: {correct_answer_letter}\n\n")

    @staticmethod
    def export_exam_to_pdf(session, exam_id, output_file):
        from models.subject.subject import Subject
        # The exam is checked to belong to the current user
        exam_data = Exam.get_exam(session, exam_id)

        if not exam_data:
            abort(400, "El examen no ha sido encontrado.")

        subject_data = Subject.get_subject(session, exam_data['subject_id'])

        # The new file is created and opened
        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()

        # Personalized styles are created
        right_aligned_style = ParagraphStyle(
            name='RightAligned',
            parent=styles['Normal'],
            alignment=TA_RIGHT
        )

        bold_style = ParagraphStyle(
            name='Bold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold'
        )

        # The heading is established
        exam_title = exam_data['title']
        if exam_data['month'] >= 9:
            year1 = exam_data['year']
            year2 = exam_data['year'] + 1
        else:
            year1 = exam_data['year'] - 1
            year2 = exam_data['year']

        subject_name = subject_data.name
        header_text = f"{subject_name}   -   Curso {year1}-{year2}<br/>{exam_title}"
        header = Paragraph(header_text, right_aligned_style)

        name_line = Paragraph("Nombre y Apellidos: _______________________________________________________________", bold_style)

        # The actual content of the exam is established
        content = [header, Spacer(1, 50), name_line, Spacer(1, 12)]
        questions = exam_data['questions']['items']
        question_number = 0
        current_section = None
        for question in questions:
            question_number += 1

            section = question['section_number']
            # If a new section, a line saying so is added
            if section != current_section:
                current_section = section
                section_title = f"Sección {current_section}"
                content.append(Paragraph(section_title, styles['Heading2']))
                content.append(Spacer(1, 10))

            # The questions parameters (if any) are obtained
            raw_parameters = [{
                'value': param['value'], 'group': param['group']
            } for param in question.get('question_parameters', {}).get('items', [])]
            parameters = []

            # If there are parameters, the previously specified group is selected
            if raw_parameters != parameters:
                if question['group'] is not None:
                    random_group = question['group']
                else:

                    # If no group was specified, a random group is selected
                    random_param = random.choice(raw_parameters)
                    random_group = random_param['group']
                for param in raw_parameters:
                    if param['group'] == random_group:
                        parameters.append(param['value'])

                # The question title is replaced with the parameters' values if needed
                question_title = replace_parameters(question['title'], parameters)
            else:
                question_title = question['title']
            question_text = f"<b>{question_number}. {question_title}</b><br/>"
            content.append(Paragraph(question_text, styles['Normal']))

            # The answers (if any and if needed) are added
            if 'answers' in question and question['type'] == 'test':
                answers = question['answers']['items']
                answer_letter = 'A'

                for answer in answers:

                    # The answer content is replaced with the parameters' values if needed
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

        # The exam is checked to belong to the current user
        user_id = get_current_user_id()
        exam = session.query(Exam).filter(and_(Exam.id == exam_id, Exam.created_by == user_id)).one_or_none()

        if not exam:
            abort(400, "El examen no ha sido encontrado.")

        exam_data = Exam.get_exam(session, exam_id)

        questions = exam_data['questions']['items']
        question_number = 0

        # The new file is opened
        with open(output_file, 'w', encoding='utf-8') as file:
            for question in questions:
                question_number += 1

                # The questions parameters (if any) are obtained
                raw_parameters = [{
                    'value': param['value'], 'group': param['group']
                } for param in question.get('question_parameters', {}).get('items', [])]
                parameters = []

                # If there are parameters, the previously specified group is selected
                if raw_parameters != parameters:
                    if question['group'] is not None:
                        random_group = question['group']
                    else:

                        # If no group was specified, a random group is selected
                        random_param = random.choice(raw_parameters)
                        random_group = random_param['group']
                    for param in raw_parameters:
                        if param['group'] == random_group:
                            parameters.append(param['value'])

                    # The question title is replaced with the parameters' values if needed
                    question_title = replace_parameters(question['title'], parameters)
                else:
                    question_title = question['title']

                # The title is added to the file
                file.write(f"::Question {question['id']}::{question_title} {{\n")

                # The answers (if any and if needed) are added
                if 'answers' in question and question['type'] == 'test':
                    answers = question['answers']['items']
                    for answer in answers:
                        # The answer content is replaced with the parameters' values if needed
                        if raw_parameters != parameters:
                            answer_body = replace_parameters(answer['body'], parameters)
                        else:
                            answer_body = answer['body']
                        file.write(f"~%{answer['points']}%{answer_body}\n")

                file.write("}\n\n")

    @staticmethod
    def export_exam_to_moodlexml(session, exam_id: int, output_file: str):
        from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
        # The exam is checked to belong to the current user
        user_id = get_current_user_id()
        exam = session.query(Exam).filter(and_(Exam.id == exam_id, Exam.created_by == user_id)).one_or_none()

        if not exam:
            abort(400, "El examen no ha sido encontrado.")

        exam_data = Exam.get_exam(session, exam_id)
        questions = exam_data['questions']['items']

        # A new quiz element is created
        quiz = Element('quiz')

        for question in questions:

            # The questions parameters (if any) are obtained
            raw_parameters = [{
                'value': param['value'], 'group': param['group']
            } for param in question.get('question_parameters', {}).get('items', [])]
            parameters = []

            # If there are parameters, the previously specified group is selected
            if raw_parameters != parameters:
                if question['group'] is not None:
                    random_group = question['group']
                else:

                    # If no group was specified, a random group is selected
                    random_param = random.choice(raw_parameters)
                    random_group = random_param['group']
                for param in raw_parameters:
                    if param['group'] == random_group:
                        parameters.append(param['value'])

                # The question title is replaced with the parameters' values if needed
                question_title = replace_parameters(question['title'], parameters)
            else:
                question_title = question['title']

            # The type of the question is added
            if question['type'] == 'test':
                question_element = SubElement(quiz, 'question', type='multichoice')
            else:
                question_element = SubElement(quiz, 'question', type='essay')

            # The title is added to the question
            name = SubElement(question_element, 'name')
            text = SubElement(name, 'text')
            text.text = question_title

            question_text = SubElement(question_element, 'questiontext', format='html')
            text = SubElement(question_text, 'text')
            text.text = question['title']

            # The answers (if any and if needed) are added
            if 'answers' in question and question['type'] == 'test':
                for answer in question['answers']['items']:

                    # The answer content is replaced with the parameters' values if needed
                    if raw_parameters != parameters:
                        answer_body = replace_parameters(answer['body'], parameters)
                    else:
                        answer_body = answer['body']
                    answer_element = SubElement(question_element, 'answer', fraction=str(int(answer['points'] )))
                    text = SubElement(answer_element, 'text')
                    text.text = answer_body
            else:
                answer_element = SubElement(question_element, 'answer', fraction='0')
                text = SubElement(answer_element, 'text')
                text.text = ''

        tree = ElementTree(quiz)

        # A file is created and the quiz is added to it
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

    @staticmethod
    def export_exam_to_odt(session, exam_id: int, output_file: str):

        # The exam is checked to belong to the current user
        user_id = get_current_user_id()
        exam = session.query(Exam).filter(and_(Exam.id == exam_id, Exam.created_by == user_id)).one_or_none()

        if not exam:
            abort(400, "El examen no ha sido encontrado.")

        exam_data = Exam.get_exam(session, exam_id)
        subject_data = session.query(Subject).filter(Subject.id == exam_data['subject_id']).one()

        questions = exam_data['questions']['items']

        # The new file is created
        doc = OpenDocumentText()

        # Personalized styles are created
        h1_style = Style(name="Heading1", family="paragraph")
        h1_style.addElement(TextProperties(attributes={'fontsize': "24pt", 'fontweight': "bold"}))
        doc.styles.addElement(h1_style)

        h2_style = Style(name="Heading2", family="paragraph")
        h2_style.addElement(TextProperties(attributes={'fontsize': "18pt", 'fontweight': "bold"}))
        doc.styles.addElement(h2_style)

        p_style = Style(name="Paragraph", family="paragraph")
        p_style.addElement(TextProperties(attributes={'fontsize': "12pt"}))
        doc.styles.addElement(p_style)

        bold_style = Style(name="Bold", family="text")
        bold_style.addElement(TextProperties(fontweight="bold"))
        doc.styles.addElement(bold_style)

        small_right_align_style = Style(name="SmallRightAlign", family="paragraph")
        small_right_align_style.addElement(TextProperties(attributes={'fontsize': "10pt"}))
        small_right_align_style.addElement(ParagraphProperties(attributes={'textalign': "right"}))
        doc.styles.addElement(small_right_align_style)

        # The heading is established
        exam_title = exam_data['title']
        if exam_data['month'] >= 9:
            year1 = exam_data['year']
            year2 = exam_data['year'] + 1
        else:
            year1 = exam_data['year'] - 1
            year2 = exam_data['year']
        subject_name = subject_data.name
        header_text = f"{subject_name} - Curso {year1}-{year2}"
        name_line = "Nombre y Apellidos: _________________________________________________________________"
        exam_line = f"{exam_title}"

        header_p = P(stylename=small_right_align_style)
        header_p.addElement(Span(text=header_text, stylename=bold_style))
        doc.text.addElement(header_p)

        exam_p = P(stylename=small_right_align_style)
        exam_p.addElement(Span(text=exam_line, stylename=bold_style))
        doc.text.addElement(exam_p)

        doc.text.addElement(P(text=""))
        doc.text.addElement(P(text=""))

        name_p = P(stylename=small_right_align_style)
        name_p.addElement(Span(text=name_line, stylename=bold_style))
        doc.text.addElement(name_p)

        doc.text.addElement(P(text=""))

        # The actual content of the exam is established
        question_number = 0
        current_section = None

        for question in questions:
            question_number += 1

            section = question.get('section_number')

            # If a new section, a line saying so is added
            if section != current_section:
                current_section = section
                section_title = f"Sección {current_section}"
                h2 = H(outlinelevel=2, stylename=h2_style, text=section_title)
                doc.text.addElement(h2)
                doc.text.addElement(P(text=""))

            # The questions parameters (if any) are obtained
            raw_parameters = [{
                'value': param['value'], 'group': param['group']
            } for param in question.get('question_parameters', {}).get('items', [])]
            parameters = []

            # If there are parameters, the previously specified group is selected
            if raw_parameters != parameters:
                if question['group'] is not None:
                    random_group = question['group']
                else:

                    # If no group was specified, a random group is selected
                    random_param = random.choice(raw_parameters)
                    random_group = random_param['group']
                for param in raw_parameters:
                    if param['group'] == random_group:
                        parameters.append(param['value'])

                # The question title is replaced with the parameters' values if needed
                question_title = replace_parameters(question['title'], parameters)
            else:
                question_title = question['title']

            # The question title is added to the document
            question_text = f"{question_number}. {question_title}"
            p = P(stylename=p_style, text=question_text)
            doc.text.addElement(p)

            # The answers (if any and if needed) are added
            if 'answers' in question and question['type'] == 'test':
                answers = question['answers']['items']
                answer_letter = 'A'
                for answer in answers:

                    # The answer content is replaced with the parameters' values if needed
                    if raw_parameters != parameters:
                        answer_body = replace_parameters(answer['body'], parameters)
                    else:
                        answer_body = answer['body']

                    # The answer content is added to the document
                    answer_text = f"{answer_letter}. {answer_body}"
                    p = P(stylename=p_style, text=answer_text)
                    doc.text.addElement(p)
                    answer_letter = chr(ord(answer_letter) + 1)
            doc.text.addElement(P(text=""))

        # The document is saved
        doc.save(output_file)

    @staticmethod
    def get_exam_questions(session, subject_id: int, exam_ids: list[int]):
        # The selected exams are obtained
        exams_query = (
            select(Exam)
            .where(
                and_(
                    Exam.subject_id == subject_id,
                    Exam.id.in_(exam_ids)
                )
            )
        )

        exams = session.execute(exams_query).scalars().all()

        questions = []
        # Each exam's questions are added to the returned data
        for exam in exams:
            for question in exam.questions:
                question_dict = question.__dict__.copy()
                question_dict['exam_id'] = exam.id
                questions.append(question_dict)

        schema = QuestionListSchema()
        return schema.dump({"items": questions, "total": len(questions)})
