from typing import Set

from flask import abort
from sqlalchemy import Integer, String, select, delete, ForeignKey, func, or_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.versions.db import Base
from models.subject.subject_schema import SubjectSchema, SubjectListSchema
from models.user.user import User
from utils.utils import get_current_user_id


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="subjects")
    questions: Mapped[Set["Question"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    nodes: Mapped[Set["Node"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    exams: Mapped[Set["Exam"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    #
    def __repr__(self):
     return "<Subject(id='%s', name='%s')>" % (self.id, self.name)

    @hybrid_property
    def question_number(self):
        """
        Calculates the total number of questions of a subject.
        """
        return sum(len(question_set) for question_set in [self.questions, self.nodes])

    @question_number.expression
    def question_number(cls):
        """
        SQLAlchemy to calculate the total number of questions of a subject.
        """

        from models.question import Question
        return select([func.sum(func.count(Question.id))]).where(
            or_(Question.subject_id == cls.id, Question.node_id == cls.id)).label("question_number")

    @staticmethod
    def insert_subject(
            session,
            name: str,
    ) -> SubjectSchema:
        from models.node.node import Node
        
        # The subject is created and added to the database, since it has no attributes to be checked
        new_subject = Subject(created_by=get_current_user_id(), name=name)

        # The hierarchy's root node is created with the subject name
        session.add(new_subject)
        session.commit()
        new_node = Node(
            name=name,
            subject_id=new_subject.id,
            created_by=new_subject.created_by
        )
        session.add(new_node)
        session.commit()

        schema = SubjectSchema().dump(new_subject)
        return schema

    @staticmethod
    def get_subject(
            session,
            id: int,
    ) -> SubjectSchema:
        query = select(Subject).where(Subject.id == id)
        res = session.execute(query).first()
        
        # The subject is checked to belong to the current user
        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        return res[0]

    @staticmethod
    def delete_subject(
            session,
            id: int
    ) -> None:
        from models.question.question import Question
        from models.node.node import Node
        from models.question_parameter.question_parameter import QuestionParameter
        from models.answer.answer import Answer
        from models.exam.exam import Exam
        from models.associations.associations import node_question_association, exam_question_association
        from models.result.result import Result
        query = select(Subject).where(Subject.id == id)
        res = session.execute(query).first()

        # The subject is checked to belong to the current user
        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        # The question IDs of the subject are obtained to delete the instances of the tables that contain them
        question_ids_query = select(Question.id).where(Question.subject_id == id)
        question_ids = [q[0] for q in session.execute(question_ids_query).fetchall()]

        # The entries in the Exam-Question table that regard the subject's objects are deleted
        query = delete(exam_question_association).where(exam_question_association.c.question_id.in_(question_ids))
        session.execute(query)
        session.commit()

        # The subject's results are deleted
        query = delete(Result).where(Result.question_id.in_(question_ids))
        session.execute(query)
        session.commit()

        # The subject's exams are deleted
        query = delete(Exam).where(Exam.subject_id == id)
        session.execute(query)
        session.commit()

        # The entries in the Node-Question table that regard the subject's objects are deleted
        query = delete(node_question_association).where(node_question_association.c.question_id.in_(question_ids))
        session.execute(query)
        session.commit()

        # The subject's answers are deleted
        query = delete(Answer).where(Answer.question_id.in_(question_ids))
        session.execute(query)
        session.commit()
        
        # The subject's question parameters are deleted
        query = delete(QuestionParameter).where(QuestionParameter.question_id.in_(question_ids))
        session.execute(query)
        session.commit()

        # The subject's questions are deleted
        query = delete(Question).where(Question.subject_id == id)
        session.execute(query)
        session.commit()
        
        # The subject's nodes are deleted
        query = delete(Node).where(Node.subject_id == id)
        session.execute(query)
        session.commit()

        # The subject is deleted
        query = delete(Subject).where(Subject.id == id)
        session.execute(query)
        session.commit()

    @staticmethod
    def get_user_subjects(session, limit: int = None, offset: int = 0) -> SubjectListSchema:
        from models.question.question import Question
        current_user_id = get_current_user_id()
        query = session.query(Subject).filter(Subject.created_by == current_user_id).offset(offset)

        # Subquery to obtain the total question number of each subject
        question_number_subquery = session.query(func.count(Question.id)). \
            filter(Question.subject_id == Subject.id). \
            label("question_number")

        query = query.add_columns(question_number_subquery)

        if limit:
            query = query.limit(limit)

        items = []
        total = 0
        for item, question_number in query:
            item_dict = item.__dict__
            item_dict['question_number'] = question_number or 0  
            items.append(item_dict)
            total += 1

        schema = SubjectListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def update_subject(
            session,
            name: str,
            id: int
    ) -> SubjectSchema:
        query = select(Subject).where(Subject.id == id)
        res = session.execute(query).first()

        # The subject is checked to belong to the current user
        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        # The name of the subject is changed
        res[0].name = name

        session.commit()


        schema = SubjectSchema().dump(res[0])

        return schema

