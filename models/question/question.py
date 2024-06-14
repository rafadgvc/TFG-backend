from enum import Enum
import pandas as pd
import re

from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, and_, CheckConstraint, Boolean, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set, List

from db.versions.db import Base
from models.answer.answer_schema import AnswerListSchema
from models.node.node import Node
from models.question.question_schema import QuestionListSchema, FullQuestionSchema, \
    FullQuestionListSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id
from models.associations.associations import node_question_association, exam_question_association


class QuestionType(Enum):
    TEST = "test"
    DESARROLLO = "desarrollo"


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    parametrized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))
    type: Mapped[str] = mapped_column(String, CheckConstraint("type IN ('test', 'desarrollo')"), nullable=False)



    # Relaciones
    created: Mapped["User"] = relationship(back_populates="questions")
    subject: Mapped["Subject"] = relationship(back_populates="questions")
    nodes = relationship("Node", secondary=node_question_association, back_populates="questions")
    exams = relationship("Exam", secondary=exam_question_association, back_populates="questions")
    answers: Mapped[Set["Answer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    question_parameters: Mapped[Set["QuestionParameter"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    results: Mapped[Set["Result"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
     return "<Question(id='%s', title='%s')>" % (self.id, self.title)

    @hybrid_property
    def connected(self):
        """
        Calcula si la pregunta tiene recursos asociados (exámenes).
        """
        return len(self.exams) > 0

    @connected.expression
    def connected(cls):
        """
        Expresión SQLAlchemy para calcular si la pregunta tiene recursos asociados (exámenes).
        """
        return select([func.count(exam_question_association.c.exam_id)]).where(
            exam_question_association.c.question_id == cls.id).label("connected") > 0

    @hybrid_property
    def uses(self):
        return len(self.exams)

    @uses.expression
    def uses(cls):
        return (
            select([func.count(exam_question_association.c.exam_id)])
            .where(exam_question_association.c.question_id == cls.id)
            .label("uses")
        )


    @staticmethod
    def get_answers_for_question(session, question_id: int, limit: int = None, offset: int = 0) -> AnswerListSchema:
        from models.answer.answer import Answer
        query = select(Answer).where(Answer.question_id == question_id).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Answer).filter(Answer.question_id == question_id).count()

        schema = AnswerListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def insert_question(
            session,
            title: str,
            subject_id: int,
            node_ids: List[int],
            difficulty: int,
            time: int,
            type: str,
            active: bool,
            parametrized: bool = False
    ) -> FullQuestionSchema:
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


        new_question = Question(
            title=title,
            subject_id=subject_id,
            created_by=user_id,
            time=time,
            difficulty=difficulty,
            type=type.lower(),
            active=active,
            parametrized=parametrized,
        )

        # Asignar nodos a la pregunta
        for node_id in node_ids:
            query = select(Node).where(Node.id == node_id)
            node = session.execute(query).first()
            if not node:
                abort(400, f"El nodo con el ID {node_id} no fue encontrado.")
            new_question.nodes.append(node[0])
            parent_node = node[0]
            while parent_node.parent:
                new_question.nodes.append(parent_node.parent)
                parent_node = parent_node.parent

        session.add(new_question)
        session.commit()
        schema = FullQuestionSchema()

        return schema.dump(
            {
                "id": new_question.id,
                "title": new_question.title,
                "subject_id": new_question.subject_id,
                "time": new_question.time,
                "difficulty": new_question.difficulty,
                "type": new_question.type,
                "active": new_question.active,
                "connected": new_question.connected
            }
        )

    @staticmethod
    def get_question(
            session,
            id: int
    ) -> FullQuestionSchema:
        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        question = res[0]
        question_data = FullQuestionSchema().dump(question)
        question_data['connected'] = question.connected
        return question_data

    @staticmethod
    def delete_question(
            session,
            id: int
    ) -> None:
        from models.answer.answer import Answer
        from models.question_parameter.question_parameter import QuestionParameter
        from models.associations.associations import node_question_association
        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        if res[0].connected == True:
            abort(401, "La pregunta tiene recursos asociados.")


        query = delete(Answer).where(Answer.question_id == id)
        session.execute(query)
        session.commit()

        query = delete(node_question_association).where(node_question_association.c.question_id == id)
        session.execute(query)
        session.commit()

        query = delete(QuestionParameter).where(QuestionParameter.question_id == id)
        session.execute(query)
        session.commit()

        query = delete(Question).where(Question.id == id)
        session.execute(query)
        session.commit()

    @staticmethod
    def get_user_questions(session, limit: int = None, offset: int = 0) -> QuestionListSchema:
        current_user_id = get_current_user_id()
        query = select(Question).where(Question.created_by == current_user_id).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Question).count()

        schema = QuestionListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def get_subject_questions(session, subject_id: int, limit: int = None, offset: int = 0) -> QuestionListSchema:
        current_user_id = get_current_user_id()
        query = select(Question).where(
            and_(
                Question.created_by == current_user_id,
                Question.subject_id == subject_id
            )
        ).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Question).count()

        schema = QuestionListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def get_full_question(
            session,
            id: int
    ) -> FullQuestionSchema:
        from models.answer.answer import Answer
        from models.answer.answer_schema import AnswerListSchema
        from models.question_parameter.question_parameter import QuestionParameter
        from models.question_parameter.question_parameter_schema import QuestionParameterListSchema

        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        query = select(Answer).where(Answer.question_id == id)
        items = session.execute(query).scalars().all()

        total = session.query(Answer).count()

        answers = AnswerListSchema()
        answers = answers.dump({"items": items, "total": total})

        query = select(QuestionParameter).where(QuestionParameter.question_id == id).order_by(QuestionParameter.group, QuestionParameter.position)
        items2 = session.execute(query).scalars().all()

        total2 = session.query(QuestionParameter).count()

        query = select(Node.id).join(node_question_association).where(node_question_association.c.question_id == id)
        node_ids = session.execute(query).scalars().all()

        schema = FullQuestionSchema()

        question_parameters = QuestionParameterListSchema()
        question_parameters = question_parameters.dump({"items": items2, "total": total2})
        return schema.dump(
            {
                "id": res[0].id,
                "title": res[0].title,
                "subject_id": res[0].subject_id,
                "time": res[0].time,
                "difficulty": res[0].difficulty,
                "type": res[0].type,
                "active": res[0].active,
                "connected": res[0].connected,
                "answers": answers,
                "question_parameters": question_parameters,
                "node_ids": node_ids
            }
        )

    @staticmethod
    def disable_question(
            session,
            id: int
    ) -> FullQuestionSchema:
        from models.answer.answer import Answer
        from models.answer.answer_schema import AnswerListSchema
        query = select(Question).where(Question.id == id)
        res = session.execute(query).first()

        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        if res[0].active == False:
            abort(418, "La pregunta ya estaba desactivada")

        res[0].active = False

        session.commit()

        query = select(Answer).where(Answer.question_id == id)
        items = session.execute(query).scalars().all()
        total = session.query(Answer).count()

        schema = FullQuestionSchema()

        answers = AnswerListSchema()
        answers = answers.dump({"items": items, "total": total})
        return schema.dump(
            {
                "id": res[0].id,
                "title": res[0].title,
                "subject_id": res[0].subject_id,
                "time": res[0].time,
                "difficulty": res[0].difficulty,
                "type": res[0].type,
                "active": res[0].active,
                "connected": res[0].connected,
                "answers": answers
            }
        )

    @staticmethod
    def get_questions_for_exam(session, exam_id: int) -> FullQuestionListSchema:
        query = select(Question).join(exam_question_association).where(exam_question_association.c.exam_id == exam_id)
        items = session.execute(query).scalars().all()

        total = session.query(Question).join(exam_question_association).filter(
            exam_question_association.c.exam_id == exam_id).count()

        schema = FullQuestionListSchema()
        questions_data = []
        for question in items:
            question_data = Question.get_question(session, question.id)
            question_data['answers'] = Question.get_answers_for_question(session, question.id)
            questions_data.append(question_data)
        return schema.dump({"items": questions_data, "total": total})

    @staticmethod
    def update_question(
            session,
            question_id: int,
            title: str,
            subject_id: int,
            node_ids: List[int],
            difficulty: int,
            time: int,
            type: str,
            active: bool,
            question_parameters_data: List[dict],
            answers_data: List[dict]
    ) -> FullQuestionSchema:
        from models.answer.answer import Answer
        from models.question_parameter.question_parameter import QuestionParameter
        user_id = get_current_user_id()

        query = select(Question).where(and_(Question.id == question_id, Question.created_by == user_id))
        question = session.execute(query).scalar_one_or_none()

        if not question:
            abort(404, "Pregunta no encontrada o no tienes permisos para editarla.")

        question.title = title
        question.subject_id = subject_id
        question.difficulty = difficulty
        question.time = time
        question.type = type.lower()
        question.active = active
        question.parametrized = question_parameters_data is not []

        query = delete(node_question_association).where(node_question_association.c.question_id == question_id)
        session.execute(query)
        session.commit()

        question.nodes = []
        for node_id in node_ids:
            query = select(Node).where(Node.id == node_id)
            node = session.execute(query).first()
            if not node:
                abort(400, f"El nodo con el ID {node_id} no fue encontrado.")
            question.nodes.append(node[0])
            parent_node = node[0]
            while parent_node.parent:
                question.nodes.append(parent_node.parent)
                parent_node = parent_node.parent

        session.query(QuestionParameter).filter_by(question_id=question_id).delete()
        for param in question_parameters_data:
            new_param = QuestionParameter(
                value=param.get('value'),
                question_id=question_id,
                created_by=user_id,
                position=param.get('position'),
                group=param.get('group')
            )
            session.add(new_param)

        session.query(Answer).filter_by(question_id=question_id).delete()
        for answer in answers_data:
            new_answer = Answer(
                body=answer.get('body'),
                question_id=question_id,
                created_by=user_id,
                points=answer.get('points')
            )
            session.add(new_answer)

        session.commit()
        schema = FullQuestionSchema()

        return schema.dump(
            {
                "id": question.id,
                "title": question.title,
                "subject_id": question.subject_id,
                "time": question.time,
                "difficulty": question.difficulty,
                "type": question.type,
                "active": question.active,
                "connected": question.connected
            }
        )

    @staticmethod
    def insert_questions_from_csv(
            session,
            file,
            subject_id: int,
            time: int = 1,
            difficulty: int = 1
    ) -> FullQuestionListSchema:
        from models.answer.answer import Answer
        try:
            # Intenta leer el archivo CSV con diferentes codificaciones
            try:
                df = pd.read_csv(file, dtype='object', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file, dtype='object', encoding='latin1')

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

            questions = []

            for index, row in df.iterrows():
                title = str(row['title'])
                type = str(row['type']).lower()

                new_question = Question(
                    title=title,
                    subject_id=subject_id,
                    created_by=user_id,
                    time=time,
                    difficulty=difficulty,
                    type=type,
                    active=True
                )

                session.add(new_question)
                session.commit()

                answer_index = 1
                while f'answer{answer_index}' in row:
                    answer_text = row.get(f'answer{answer_index}')
                    points_text = row.get(f'points{answer_index}')

                    if pd.notna(answer_text) and pd.notna(points_text):
                        answer = Answer(
                            body=answer_text,
                            question_id=new_question.id,
                            created_by=user_id,
                            points=int(points_text)
                        )
                        session.add(answer)

                    answer_index += 1

                session.commit()

                question_schema = FullQuestionSchema()
                question_data = question_schema.dump(
                    {
                        "id": new_question.id,
                        "title": new_question.title,
                        "subject_id": new_question.subject_id,
                        "time": new_question.time,
                        "difficulty": new_question.difficulty,
                        "type": new_question.type,
                        "active": new_question.active,
                        "connected": new_question.connected
                    }
                )
                questions.append(question_data)

            schema = FullQuestionListSchema()
            return schema.dump({"items": questions})

        except Exception as e:
            session.rollback()
            abort(400, message=str(e))

    @staticmethod
    def insert_questions_from_aiken(session, file, subject_id: int, difficulty: int = 1,
                                    time: int = 1) -> FullQuestionListSchema:
        from models.answer.answer import Answer
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

        questions = []
        question_pattern = re.compile(r"^(.*?)\n([A-Z]\..*?)\nANSWER:\s([A-Z])", re.MULTILINE | re.DOTALL)

        try:
            content = file.read().decode('utf-8')
            matches = question_pattern.findall(content)

            for match in matches:
                title = match[0].strip()
                answers = match[1].strip().split('\n')
                correct_answer = match[2].strip()

                new_question = Question(
                    title=title,
                    subject_id=subject_id,
                    created_by=user_id,
                    time=time,
                    difficulty=difficulty,
                    type='test',
                    active=True
                )

                node = Node.get_root_node(session=session, subject_id=subject_id)
                new_question.nodes.append(node)

                session.add(new_question)
                session.commit()

                for answer in answers:
                    answer_letter = answer[0]
                    answer_text = answer[3:].strip()
                    points = 100 if answer_letter == correct_answer else 0

                    Answer.insert_answer(
                        session=session,
                        body=answer_text,
                        question_id=new_question.id,
                        points=points
                    )

                session.commit()

                questions.append(new_question)

            schema = FullQuestionListSchema()
            return schema.dump({"items": questions})
        except Exception as e:
            session.rollback()
            abort(400, message=str(e))