from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set

from db.versions.db import Base
from models.node.node_schema import NodeSchema, NodeListSchema
from models.question.question_schema import QuestionListSchema, FullQuestionListSchema, FullQuestionSchema, \
    QuestionSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id


class Node(Base):
    __tablename__ = "node"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("node.id"), nullable=True)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="nodes")
    subject: Mapped["Subject"] = relationship(back_populates="nodes")
    parent: Mapped["Node"] = relationship("Node", back_populates="children", remote_side=[id])
    children: Mapped[Set["Node"]] = relationship(
        "Node",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    questions: Mapped[Set["Question"]] = relationship(
        back_populates="node",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
     return "<Node(id='%s', name='%s')>" % (self.id, self.name)

    @staticmethod
    def insert_node(
            session,
            name: str,
            subject_id: int,
            parent_id: int = None
    ) -> NodeSchema:
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

        if parent_id is not None:
            query = select(Node).where(
                and_(
                    Node.id == parent_id,
                    Node.created_by == user_id
                )
            )
            parent = session.execute(query).first()

            if not parent:
                abort(400, "El nodo superior con el ID no ha sido encontrado.")

        new_node = Node(name=name, subject_id=subject_id, created_by=user_id, parent_id=parent_id)
        session.add(new_node)
        session.commit()
        schema = NodeSchema().dump(new_node)
        return schema

    @staticmethod
    def get_node(
            session,
            id: int
    ) -> NodeSchema:
        query = select(Node).where(Node.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        return res[0]

    @staticmethod
    def get_subject_nodes(session, subject_id: int, limit: int = None, offset: int = 0) -> QuestionListSchema:
        current_user_id = get_current_user_id()
        query = select(Node).where(
            and_(
                Node.created_by == current_user_id,
                Node.subject_id == Node.subject_id
            )
        ).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Node).count()

        schema = NodeListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def get_questions_of_node(session, node_id: int, limit: int = None, offset: int = 0) -> FullQuestionListSchema:
        from models.question.question import Question
        from models.answer.answer import Answer
        current_user_id = get_current_user_id()
        query = select(Question).distinct().join(Answer).where(
            and_(
                Question.created_by == current_user_id,
                Question.node_id == node_id
            )
        ).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Node).count()

        questions_with_responses = []

        for question in items:
            answers = question.answers
            total_answers = len(answers)
            question_dict = {
                "id": question.id,
                "title": question.title,
                "subject_id": question.subject_id,
                "node_id": question.node_id,
                "time": question.time,
                "difficulty": question.difficulty,
                "type": question.type,
                "answers": {"items": answers, "total": total_answers}
            }
            questions_with_responses.append(question_dict)

        schema = FullQuestionListSchema()
        return schema.dump({"items": questions_with_responses, "total": total})
